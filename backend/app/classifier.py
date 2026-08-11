"""CLIP zero-shot over the four appearance classes.

The four prompts never change, so their embeddings are computed once at startup and
reused for every frame — that removes the text tower from the per-frame cost entirely.
What it must not do is change the numbers: `classify` reproduces CLIP's own
logit_scale-and-softmax exactly, and a test pins it against the single-shot path.

This model answers only "what does the surface look like right now". Trend is derived
downstream from the time-derivative of the smoothed index. There is no fifth class.
"""

from __future__ import annotations

import time
from typing import Sequence

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app import config

ImageLike = Image.Image | np.ndarray


def _features(output: object) -> torch.Tensor:
    """Projected embeddings, across the transformers 4.x/5.x API change.

    4.x returned a bare tensor from get_*_features; 5.x returns a
    BaseModelOutputWithPooling whose pooler_output holds the projected vector.
    requirements.txt permits both, so handle both rather than pin by accident.
    """
    return output if isinstance(output, torch.Tensor) else output.pooler_output


class ZeroShotClassifier:
    def __init__(self, model: CLIPModel, processor: CLIPProcessor, device: str) -> None:
        self._model = model
        self._processor = processor
        self.device = device
        self.model_id = config.MODEL_ID
        self.warm = False

        # Precomputed, L2-normalised text embeddings — one row per appearance class.
        inputs = processor(text=list(config.PROMPTS), return_tensors="pt", padding=True)
        with torch.no_grad():
            embeds = _features(model.get_text_features(**{k: v.to(device) for k, v in inputs.items()}))
        self._text_embeds = embeds / embeds.norm(p=2, dim=-1, keepdim=True)
        self._logit_scale = model.logit_scale.exp().item()

    @classmethod
    def load(cls) -> "ZeroShotClassifier":
        """Load the pinned model. Never substitutes — a failure here is reported, not routed around."""
        device = config.resolve_device()
        try:
            model = CLIPModel.from_pretrained(config.MODEL_ID, cache_dir=str(config.CACHE_DIR))
            processor = CLIPProcessor.from_pretrained(config.MODEL_ID, cache_dir=str(config.CACHE_DIR))
        except Exception as exc:  # noqa: BLE001 - surfaced verbatim, never swallowed
            raise RuntimeError(
                f"Could not load pinned model {config.MODEL_ID!r} from {config.CACHE_DIR}: {exc}"
            ) from exc
        return cls(model.to(device).eval(), processor, device)

    def classify(self, images: Sequence[ImageLike]) -> list[dict[str, float]]:
        """Probability distribution per image, keys in config.CLASS_NAMES order."""
        results: list[dict[str, float]] = []
        for start in range(0, len(images), config.CLASSIFY_BATCH_SIZE):
            batch = list(images[start : start + config.CLASSIFY_BATCH_SIZE])
            inputs = self._processor(images=batch, return_tensors="pt")
            with torch.no_grad():
                embeds = _features(
                    self._model.get_image_features(**{k: v.to(self.device) for k, v in inputs.items()})
                )
                embeds = embeds / embeds.norm(p=2, dim=-1, keepdim=True)
                probs = (self._logit_scale * embeds @ self._text_embeds.T).softmax(dim=-1)
            results.extend(dict(zip(config.CLASS_NAMES, row)) for row in probs.cpu().tolist())
        return results

    def warmup(self) -> float:
        """Run throwaway frames so the first real request doesn't pay kernel init.

        Returns measured milliseconds for the final single-frame pass — the honest
        per-frame cost on this machine, reported rather than assumed.
        """
        dummy = Image.new("RGB", (config.FRAME_MAX_EDGE, config.FRAME_MAX_EDGE), (70, 70, 74))
        elapsed_ms = 0.0
        for _ in range(config.WARMUP_FRAMES):
            started = time.perf_counter()
            self.classify([dummy])
            elapsed_ms = (time.perf_counter() - started) * 1000
        self.warm = True
        return elapsed_ms


def dominant_class(probabilities: dict[str, float]) -> str:
    """Label for display only. Never let a single frame's argmax drive a decision."""
    return max(probabilities, key=lambda name: probabilities[name])

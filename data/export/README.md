---
license: cc-by-sa-4.0
task_categories:
  - image-classification
tags:
  - weather
  - road-surface
  - motorsport
size_categories:
  - n<1K
---

# Weather Whiplash — road surface conditions

247 photographs of road and track surfaces, each labelled by a human with
one of four appearance classes. Built for **Weather Whiplash**, a live track-condition
detector whose reasoning layer turns a per-frame surface classification into a stable
wetness index, a trend, and a tyre-change recommendation.

## The four classes

The classes describe **appearance at one instant**, not direction of change. There is no
"drying" class and there will not be one: drying is a property of a sequence, derived
downstream from the time-derivative of a smoothed index. A single photograph cannot show
it, so a single photograph is never labelled with it.

| class | images | share |
|---|---|---|
| `dry` | 65 | 26% |
| `damp` | 38 | 15% |
| `wet` | 87 | 35% |
| `standing_water` | 57 | 23% |

- `dry` — matte, uniform, no sheen.
- `damp` — surface darkened by moisture, but not reflecting.
- `wet` — specular; reflects light and objects.
- `standing_water` — water pooled on the surface, or visible spray.

## How it was labelled

Every image was first shown to `openai/clip-vit-base-patch32` zero-shot against four
engineered prompts, and that proposal was recorded. A human then reviewed all
400 candidates in a keyboard-driven tool and set the final label.

**The human agreed with CLIP on 46% of kept images and changed
133.** That gap is the reason the dataset exists. Zero-shot CLIP is
weak at exactly the distinction that matters most here — dry versus damp asphalt — and
the corrections concentrate there.

A further 153 candidates were rejected outright, because the surface in
them could not honestly be judged: resurfacing work mid-pour, a close-up of a tyre, a
lizard filling the frame, a vintage racing photograph. That is 38%
of everything retrieved, spread almost evenly across all four source groups — so it is
not a quirk of one search term but the ordinary cost of harvesting a specific visual
property from a general-purpose image library. They are excluded rather than forced into
whichever of the four classes fits worst.

## Provenance and licensing

All 247 source photographs come from Wikimedia Commons under licences that permit redistribution. No image was downloaded whose licence could not be read.

**`attribution.json` is keyed by the file you receive**, not by the original upload name —
one record per image, carrying its title, author, licence, and a link to the source page:

```json
{ "file": "data/wet/00278.jpg", "artist": "…", "license": "cc-by-sa-4.0",
  "source_url": "https://commons.wikimedia.org/wiki/File:…" }
```

Most of these licences require you to credit the individual photographer. Credit them
from that file — not this repository.

| licence | images |
|---|---|
| `cc-by-2.0` | 19 |
| `cc-by-2.5` | 1 |
| `cc-by-3.0` | 13 |
| `cc-by-4.0` | 11 |
| `cc-by-sa-2.0` | 40 |
| `cc-by-sa-2.5` | 1 |
| `cc-by-sa-3.0` | 23 |
| `cc-by-sa-4.0` | 111 |
| `cc0` | 20 |
| `pd` | 8 |

The set is published as **CC BY-SA 4.0**, the most restrictive licence among its
inputs, so that the whole is compatible with every part. Attribute the original
photographers via `attribution.json`, not this repository.

## Known limitations

Read these before using it for anything.

- **It is small.** 247 images is enough to fit a linear probe on frozen
  embeddings. It is not enough to fine-tune a backbone, and not enough to make strong
  claims about accuracy.
- **Single-annotator.** One person labelled every image. There is no second pass and no
  inter-annotator agreement figure, so the boundary between `damp` and `wet` reflects
  one person's judgement of a genuinely continuous variable.
- **Not motorsport footage.** These are mostly public roads photographed from a
  standing position. A trackside broadcast camera sees a different angle, different
  optics, and spray the still images here do not contain.
- **Retrieval bias.** Images come from curated Wikimedia Commons categories (`Asphalt`,
  `Wet roads`, `Puddles`, `Flooded roads`, and others), with free-text search used only
  for `damp`, which has no category — because nobody photographs a slightly wet road on
  purpose. So the set over-represents conditions dramatic enough to be worth
  photographing and captioning, and `damp` is both the smallest class here and the one
  zero-shot is worst at. That is the honest shape of the problem, not an accident.
- **Geographic and seasonal skew.** Commons road photography skews heavily towards
  Western Europe, and towards daylight. There is very little night footage, which is
  precisely the condition the parent project is designed for.

## Loading it

```python
from datasets import load_dataset

ds = load_dataset("pratyushgarg/weather-whiplash-surfaces")
```

The layout is standard `imagefolder`: `data/<label>/<id>.jpg`.

---
title: Weather Whiplash API
emoji: 🏎️
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
---

# Weather Whiplash

Track-surface intelligence for tyre decisions. Upload racing footage to classify the
surface, smooth it into a Track Wetness Index, detect whether conditions are changing,
and estimate when to pit.

![Weather Whiplash workstation](docs/screenshot.png)

## What it does

- Classifies each frame as `dry`, `damp`, `wet`, or `standing_water` with
  [`openai/clip-vit-base-patch32`](https://huggingface.co/openai/clip-vit-base-patch32).
- Derives `DRYING`, `WETTING`, or `STABLE` from the smoothed signal—not from a single
  image.
- Shows frame quality, uncertainty, weather fusion, crossover timing, and a hysteresis
  based tyre recommendation.

## Stack

FastAPI, PyTorch/Transformers, OpenCV, SQLite, and Next.js. The frontend and backend
remain separate processes connected over HTTP.

## Run locally

Requires Python 3.11+ and Node.js.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci && cd ..


# Terminal 1
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000

# Terminal 2
cd frontend && npm run dev

Open http://localhost:3000. The first backend start downloads and warms the model.

Configuration and deployment

The application uses no runtime API key. Keep optional Hugging Face write tokens in
your ignored .env file or in your shell environment; use the committed
.env.example only as a template.

Future Prospects

Weather Whiplash is intended to evolve from a zero-shot vision baseline into a
Formula 1-specific track-condition and tyre-strategy intelligence system.

Future development will focus on:

Hugging Face model integration — evaluate and integrate stronger vision models
from the Hugging Face ecosystem and move beyond the current zero-shot CLIP approach.
F1-specific dataset and fine-tuning — build a human-verified dataset from
Formula 1 racing footage and track imagery covering dry, damp, wet, and
standing_water, then fine-tune suitable Hugging Face vision models using
PyTorch and Transformers.
Track-condition intelligence — improve detection of surface wetness, standing
water, spray, drying lines, and changing grip conditions across consecutive frames.
Temporal modelling — combine frame-level predictions with temporal models and
sequence analysis to produce more reliable wetting/drying trends.
Tyre-strategy prediction — combine track condition, wetness trend, weather,
lap-time behaviour, and uncertainty to recommend when slicks, intermediates, or
full wets are likely to become optimal.
F1 telemetry integration — incorporate telemetry and race data such as lap
times, sector performance, tyre compounds, pit stops, race position, and track
conditions to improve strategic predictions.
Weather-data fusion — combine computer-vision predictions with rainfall,
temperature, humidity, wind, and forecast data to create a more complete
track-condition model.
Circuit-specific intelligence — incorporate circuit layouts, sectors, racing
lines, surface characteristics, and historical race-weather data so that the model
understands that different circuits can behave differently under the same weather
conditions.
Multimodal race analysis — combine video, telemetry, weather, historical race
data, and circuit information into a unified race-engineering report.
Real-time analysis — extend the current uploaded-clip workflow toward continuous
live analysis of racing footage.
Uncertainty-aware predictions — preserve the system's ability to refuse unreliable
predictions and explicitly report when the available evidence is insufficient.

The long-term objective is to combine:

Computer Vision + Hugging Face Models + Temporal Analysis + Weather Data +
F1 Telemetry + Circuit Intelligence + Tyre Strategy

into a single system capable of analysing racing footage and producing an
engineering-style track-condition and tyre-strategy report.

Licence

MIT. Dataset sources and attribution are documented in
docs/DATASET.md. The compiled dataset is available on Hugging Face at
mrcreoid/weather-whiplash-surfaces

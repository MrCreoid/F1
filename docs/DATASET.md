# The dataset

Four scripts, run in order, from the repo root. Each one is re-runnable and none of them
destroys work you have already done by hand.

```bash
.venv/bin/python scripts/fetch_sources.py    # 1. collect, with licences
.venv/bin/python scripts/build_dataset.py    # 2. auto-label, queue for review
open data/dataset/label_tool.html            # 3. correct, keys 1-4 and 0
.venv/bin/python scripts/push_to_hub.py      # 4. build export, read the card
HF_TOKEN=hf_... .venv/bin/python scripts/push_to_hub.py --push
```

## Why it is shaped this way

**Categories, not free-text search.** Commons search matches the wording of a file's
description page, not the picture. Measured over a 288-image search-only run, just 36% of
results had a road word in the title: `wet racetrack` returned a passenger's window
photographs from a Heathrow–LAX flight, and `standing water on road` returned four
photographs of a Norfolk water tower, matched on "Water" and "standing by". Curated
categories are maintained by people and cost the reviewer far less time.

Categories are verified before they go in `SOURCE_CATEGORIES`. Plausible-sounding names
are often empty — `Category:Wet asphalt`, `Category:Tarmac` and `Category:Dry asphalt`
all have zero files — and an empty category is indistinguishable from a typo. Check a
name returns files before adding it.

Free text survives only for `damp`, because Commons has no damp-roads category. Nobody
photographs a slightly wet road on purpose. That is also why zero-shot CLIP is worst at
damp, and why the dataset is worth building at all.

**Categories carry more than photographs.** `Category:Puddles` contains `.ogg` and `.wav`
recordings of people pronouncing the word "puddle". `is_image()` filters on extension
before anything reaches a decoder.

**The retrieval hint is never the label.** It would be easy to save two hours by treating
`Category:Wet roads` as ground truth for its members. It would also be worthless: that
category holds plenty of merely damp roads, and separating damp from wet is the whole
difficulty of this problem. The hint is recorded as `query_hint` and no downstream step
reads it.

**Attribution is flushed after every source, not at the end of the run.** An interrupted
fetch that left images on disk with no licence recorded would produce exactly the
unusable pile that made this project's original sample clips unpublishable. If it
happens anyway, `build_dataset.py` refuses to ingest an image that has no attribution
record, so an orphan cannot reach the export.

**CLIP proposes, a human disposes.** `auto_label` is written once and never overwritten,
so the card can state exactly how many frames the reviewer changed. That number is the
argument for the dataset existing at all — if a human agreed with zero-shot CLIP every
time, there would be nothing here worth publishing.

**A frame nobody reviewed is not in the dataset.** `apply_labels` drops anything with a
null label. Shipping auto-labels as ground truth would make the set a record of the
model's own opinion, and a probe trained on it would learn to imitate the mistakes it
was supposed to fix.

**Rejection is a first-class outcome.** Keyword search over Commons returns homonyms: a
dry lake bed called Racetrack Playa, a telescope "damping system", a satellite image of
a flood, 8K texture maps. Key `0` bins them. They are counted in the card and excluded
from the export, rather than being forced into whichever of the four classes fits worst.

**Licences are read, not assumed.** `ALLOWED_LICENSES` in `backend/app/config.py` is an
allowlist of slugs that permit redistribution. NC and ND are deliberately absent — a
dataset nobody may reuse is not worth publishing. An image whose licence string we
cannot parse is skipped and counted. Author, licence and source page travel with every
file from download to export.

## The labelling tool

`scripts/label_tool.html` opens off disk with no server. `build_dataset.py` writes
`manifest.js` beside it because a browser will not `fetch` a sibling JSON over `file://`,
but it will load a script tag.

- `1` dry · `2` damp · `3` wet · `4` standing water · `0` reject
- `←` `→` move · `u` undo the last decision
- Progress is written to `localStorage` on every keystroke and the tool resumes at the
  first unlabelled frame, so closing the tab two hours in costs nothing.
- `Save labels.json` downloads the result. Put it in `data/dataset/` next to the manifest.

The header shows a running "CLIP agrees N%" figure. Watch it: if it sits near 100% you
are rubber-stamping rather than reviewing, and the dataset is not adding information.

## What to do about class balance

The four classes will not come out balanced, because Commons does not contain equal
numbers of photographs of each condition. `standing_water` is over-represented relative
to real driving (people photograph floods) and ordinary `damp` is badly
under-represented (nobody photographs a slightly wet road).

Do not fix this by relabelling. Fix it by adding search terms to `SOURCE_QUERIES` in
`backend/app/config.py` and re-running the fetch — it skips what is already on disk, so
this is cheap. If it stays skewed, say so in the card and weight the probe's loss
instead.

## Adding your own footage

`build_dataset.py` takes a directory, not a fixed source. Stills and video both, and
video is sampled through the app's own extractor so a dataset frame is identical to a
runtime frame.

```bash
.venv/bin/python scripts/build_dataset.py --source path/to/your/clips
```

Own footage is strictly better than Commons for this problem: it can be shot at the
right angle, in the right light, at night, and it carries no licensing question at all.
The current source images are public roads photographed from a standing position in
daylight, which is not what a trackside camera sees.

## Secrets

`HF_TOKEN` is read from the environment by `push_to_hub.py`. It is never written to a
file, never printed, and never included in an error message. `.env` is gitignored. If
the token is missing the script says how to make one and stops, rather than falling back
to an anonymous push that would fail halfway through an upload.

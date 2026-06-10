<div class="trackflow-home-title">
  <div class="trackflow-home-logo">t</div>
  <h1>trackflow</h1>
</div>

<p class="trackflow-lead">
PsychoPy-first runtime helpers for behavior, eye tracking, EEG markers, and
deployment workflows.
</p>

## Overview

`trackflow` helps psychology researchers keep experiment scripts explicit while
reusing the runtime pieces that often become repetitive across studies:
behavior rows, trial summaries, recovery metadata, EyeLink wrappers, EEG marker
sending, and sync records.

The package is intentionally not a full experiment runner. Use ordinary
PsychoPy code for the scientific procedure, timing, stimuli, and responses. Use
`trackflow` for the parts that are shared across experiments and need to be
consistent.

The current public API is organized into four runtime areas:

- `trackflow.beh` for timeline-owned behavior helpers organized into
  timelines, stimuli, screens, trials, trial planning, and data output
- `trackflow.gaze` for EyeLink setup, tracker wrappers, and gaze monitoring
- `trackflow.eeg` for parallel-port marker senders and debug marker senders
- `trackflow.sync` for explicit EEG and EyeLink sync records

## Installation

With `uv`:

```bash
uv add "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

With `pip`:

```bash
pip install "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

## A minimal behavior screen

This example keeps PsychoPy in control of the window and uses `trackflow.beh`
only for reusable screen construction and raw data bookkeeping.

```python
from psychopy import visual

from trackflow import beh


win = visual.Window(size=(1024, 768), units="deg")
timeline = beh.timeline.setup_timeline(win=win, raw_data_file="data/S01_screen_data.jsonl")
fix = beh.stimuli.make_fixation(win, size=0.5, color="#000000")

screen = timeline.make_screen(
    stimuli=[fix],
    duration=0.5,
    response=None,
    data={"screen_name": "fixation"},
)

timeline.run(screen)
```

## Core ideas

### Timeline owns runtime context

Create a timeline first. It stores the PsychoPy window, creates screens and
trials, runs units, and owns behavior data output.

### PsychoPy owns the experiment

`trackflow` should not hide experiment design decisions. Trial phase order,
stimulus timing, response mappings, condition assignment, and data meanings
should remain visible in the experiment script or project settings.

### Simple screens are convenience helpers

`timeline.make_screen()` is useful for simple fixed-duration screens and
first-key responses. For complex trials, write a normal PsychoPy trial object
with `run(ctx)` and return `beh.timeline.TrialOutcome` so
`beh.timeline.Timeline` can still handle output and recovery bookkeeping.

### Sync records are explicit

EEG and EyeLink sends return records that experiment code explicitly stores in
the current row. This keeps marker timing and saved data visible to the
researcher.

<div class="trackflow-link-list">
  <a href="articles/psychopy-first/">PsychoPy-first runtime helpers</a>
  <a href="api/beh/">Behavior API</a>
  <a href="api/gaze/">Eye tracking API</a>
  <a href="api/eeg/">EEG API</a>
</div>

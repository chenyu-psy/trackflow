# trackflow

## What is trackflow?

`trackflow` is a small set of PsychoPy-first helpers for psychology
experiments. It helps with the repeated parts of experiment scripts while
keeping the scientific procedure visible in ordinary Python code.

Use it to:

- build reusable PsychoPy screens;
- save behavior rows and trial summaries;
- detect gaze breaks during selected screens;
- send EEG markers and EyeLink messages from explicit hooks.

Full documentation is available at <https://chenyu-psy.github.io/trackflow/>.

## When should I use it?

Use `trackflow` when you want a readable PsychoPy script but do not want to
rewrite the same runtime bookkeeping for every experiment.

`trackflow` does not replace PsychoPy, choose your trial design, assign
conditions, decide retry or exclusion rules, or hide marker timing. Your
experiment script still owns those decisions.

## Install

Install from GitHub with `pip`:

```bash
pip install "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

If your project uses `uv`, add it with:

```bash
uv add "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

## First screen

This example creates one fixation screen and saves one raw behavior row when
the screen completes. The `raw_data_file` receives one JSONL row for the
completed screen.

```python
from psychopy import visual

from trackflow import beh


win = visual.Window(size=(1024, 768), units="deg")
timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
)

fix = beh.stimuli.make_fixation(win, size=0.5, color="#000000")
screen = timeline.make_screen(
    stimuli=[fix],
    duration=0.5,
    data={"screen_name": "fixation"},
)

timeline.run(screen)
```

For planned trials, keep the plan in normal Python code and call
`timeline.run(...)` inside your loop.

## Eye tracking and EEG

Eye tracking and EEG sends are explicit. The tracker is the eye-tracking
runtime object passed to the timeline; the experiment script chooses marker
codes, message text, send timing, monitored phases, and saved data fields.

```python
from trackflow import beh, eeg, gaze


tracker = gaze.setup_tracker(
    win=win,
    cfg=gaze.GazeConfig(max_dist_deg=1.25),
    edf_name="S01.edf",
    monitor=monitor,
    debug=True,
)
sender = eeg.setup_port(
    debug=True,
    code={"sample": 21},
)

timeline = beh.timeline.setup_timeline(
    win=win,
    tracker=tracker,
    eeg=sender,
)

def mark_sample(ctx, data):
    code = ctx.code["sample"]
    ctx.send(code, message="sample")
    data["EEG"] = code
    data["ET_message"] = "sample"

sample_screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    on_load=mark_sample,
    data={"screen_name": "sample"},
)

timeline.run(sample_screen)
```

## Development checks

```bash
uv sync --only-group dev --no-install-project
PYTHONPATH=src uv run --no-sync pytest
PYTHONPATH=src uv run --no-sync ruff check src tests
PYTHONPATH=src uv run --no-sync mkdocs build --strict
```

## Documentation

The documentation site is published with GitHub Pages after changes are merged
into `main`:

<https://chenyu-psy.github.io/trackflow/>

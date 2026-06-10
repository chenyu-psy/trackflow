# trackflow

`trackflow` provides small, explicit PsychoPy runtime helpers for psychology
experiments that use behavior, eye tracking, EEG markers, and deployment-time
vendoring.

The package is designed for lab code that should remain readable to researchers.
It helps with repeated runtime bookkeeping while keeping the experiment
procedure in ordinary PsychoPy scripts.

## Current status

The current package version is `0.1.0`. It includes:

- `trackflow.beh` for behavior helpers organized into stimuli, screens,
  timelines, trials, trial planning, data output, recovery, global researcher
  keys, and preflight checks
- `trackflow.gaze` for EyeLink setup, wrappers, and gaze-break monitoring
- `trackflow.eeg` for parallel-port marker sending and debug marker senders
- `trackflow.sync` for explicit EEG and EyeLink sync records

Project packaging, vendoring commands, and experiment scaffolding are planned
for later milestones.

## Installation

Install from GitHub with `pip`:

```bash
pip install "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

If your project uses `uv`, add it with:

```bash
uv add "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

## Basic use

`trackflow` does not open windows or initialize hardware when imported.
Experiment scripts still create and own the PsychoPy window and task flow.

```python
from psychopy import visual

from trackflow import beh


win = visual.Window(size=(1024, 768), units="deg")
fix = beh.stimuli.make_fixation(win, size=0.5, color="#000000")
screen = beh.screens.make_screen(
    stimuli=[fix],
    duration=0.5,
    response=None,
    screen_name="fixation",
)

timeline = beh.timeline.setup_timeline(raw_data_file="data/S01_screen_data.jsonl")
timeline.show_screen(win, screen)
```

For complex trials, write normal PsychoPy code and return a
`beh.trials.TrialOutcome` so `trackflow` can handle common output and
recovery bookkeeping.

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

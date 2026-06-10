# Behavior Timeline

Timelines are the behavior runtime API. A timeline owns the PsychoPy window,
creates runtime-owned screens and ordered screen groups, runs them, stores
completed rows, writes optional raw JSONL and summary CSV files, manages
recovery metadata, exposes sync helpers, and handles researcher safety keys.

## Overview

Use a timeline when `trackflow` should create runtime-owned screens, group
screens into trial-like procedures, record completed screen rows, and manage
recovery and researcher safety keys. The timeline does not define the
scientific procedure; ordinary Python control flow decides when to create and
run each unit.

```python
from trackflow import beh

timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
)
screen = timeline.make_screen(stimuli=[fix], duration=0.5, data={"screen_name": "fixation"})
trial = timeline.make_trial(screens=[screen])
timeline.run(trial, trial_data={"condition": "practice"})
```

Global researcher keys and recovery metadata are timeline runtime
bookkeeping. They are configured through timeline setup and are not separate
Behavior API pages.

## Creating A Timeline

::: trackflow.beh.timeline.setup_timeline
    options:
      heading_level: 3

## Creating Screens

A screen is the smallest built-in presentation/response unit. It draws one or
more stimuli, optionally collects one key response, then returns one raw screen
row. Screens do not choose condition assignment, retry behavior, or trial
summaries.

Prefer `timeline.make_screen()` in experiment scripts. It returns a
`beh.timeline.Screen` object, but the construction path stays timeline-owned.
Use `timeline.make_text_screen(...)` and `timeline.make_image_screen(...)` for
common instruction screens. These methods create screens only; they do not run
or save data until `timeline.run(...)` is called.

```python
screen = timeline.make_screen(
    stimuli=[fix],
    duration=0.5,
    response=None,
    data={"screen_name": "fixation"},
)
```

When a timeline runs a screen, the row is built from current `trial_data`, the
screen's own `data`, response fields, and sync containers. Readable labels
such as `screen_name` are ordinary data fields.

::: trackflow.beh.timeline.Timeline.make_screen
    options:
      heading_level: 3

::: trackflow.beh.timeline.Timeline.make_text_screen
    options:
      heading_level: 3

::: trackflow.beh.timeline.Timeline.make_image_screen
    options:
      heading_level: 3

## Screen Methods

Most scripts create screens through timeline factory methods. The methods below
are useful when a script needs to update a prepared screen before a run, or for
low-level integrations.

::: trackflow.beh.timeline.Screen.update
    options:
      heading_level: 3

::: trackflow.beh.timeline.Screen.run
    options:
      heading_level: 3

Call `Screen.run()` directly only for low-level integrations that need the raw
screen row without timeline storage, global-key handling, recovery, or summary
bookkeeping. Ordinary experiment scripts should call `timeline.run(screen)`.

## Running Screen Sequences

Use `timeline.make_trial(...)` when multiple screens should run as one
trial-like procedure. The returned object is timeline-owned and intentionally
not exposed through a separate trials namespace. Use `run_if(ctx)` here when
an entire trial should be conditionally skipped.

```python
trial = timeline.make_trial(
    screens=[fixation_screen, sample_screen, response_screen],
    data_format=lambda screen_rows: {
        "plan_id": screen_rows[0]["plan_id"],
        "response": screen_rows[-1]["response"],
    },
)
```

The built-in sequence runner presents screens in order, collects their raw
screen rows, and optionally creates one trial-level summary row with
`data_format`. It does not own the PsychoPy window or output files; those
remain timeline responsibilities.

::: trackflow.beh.timeline.Timeline.make_trial
    options:
      heading_level: 3

## Running Units

Use `run()` as the only public execution entry point. A single screen is
automatically treated as a one-screen trial.

`trial_data` controls how many times a unit runs and what data every screen row
inherits:

- `trial_data=None`: run once with an empty trial-data dictionary.
- `trial_data={...}`: run once and copy that dictionary into each screen row.
- `trial_data=[{...}, {...}]`: run once per dictionary.

```python
timeline.run(screen)
timeline.run(trial, trial_data={"condition": "left"})
timeline.run(trial, trial_data=[{"condition": "left"}, {"condition": "right"}])
```

`timeline.run(...)` returns `None`. Completed data should be read through
`get_data(...)`, `get_last_data(...)`, raw JSONL output, or summary CSV output.

::: trackflow.beh.timeline.Timeline.run
    options:
      heading_level: 3

## Trial Summaries

`data_format(screen_rows)` receives only the raw screen rows from the current
trial run and returns one optional summary row. Raw screen rows and summary
rows are stored separately so screen-level timing/response data stays intact.

## Custom Trial-Like Objects

For custom PsychoPy loops, mouse responses, frame-level logic, or task-specific
branching, write an ordinary object with `run(ctx)` and return
`beh.timeline.TrialOutcome` or a compatible dictionary.

```python
class CustomTrial:
    def run(self, ctx):
        row = {"plan_id": ctx.trial_data["plan_id"]}
        # Custom PsychoPy procedure here.
        return beh.timeline.TrialOutcome(
            status="accepted",
            reason="no",
            row=row,
            screen_rows=[],
        )
```

## Runtime Context

`RunContext` is passed to trial-like objects and screen hooks so code can access
the window, timeline state, trial data, active screen, and sync helper.

- `ctx.win`: PsychoPy window configured on the timeline.
- `ctx.timeline`: timeline running the current unit.
- `ctx.trial_data`: data inherited by every screen row in this trial run.
- `ctx.params`: stable runtime settings.
- `ctx.state`: mutable runtime flags.
- `ctx.screen`: current screen while screen hooks are running.
- `ctx.sync`: configured EEG/EyeLink sync helper.

::: trackflow.beh.timeline.RunContext
    options:
      heading_level: 3

::: trackflow.beh.timeline.TrialOutcome
    options:
      heading_level: 3

## Reading Completed Data

`get_data()` returns filtered raw or summary rows. `get_last_data()` returns
the most recent screen, trial, block, or session.

::: trackflow.beh.timeline.Timeline.get_data
    options:
      heading_level: 3

::: trackflow.beh.timeline.Timeline.get_last_data
    options:
      heading_level: 3

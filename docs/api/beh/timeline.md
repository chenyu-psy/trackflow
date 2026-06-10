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

Common arguments:

- `win`: PsychoPy window used by timeline-owned screens.
- `raw_data_file` and `summary_file`: optional output files for raw screen rows
  and trial summaries.
- `meta_file` and `meta_state`: optional recovery state for completed planned
  rows.
- `params` and `state`: stable settings and mutable runtime state available
  through `RunContext`.
- `global_actions`: researcher safety keys such as pause or quit.

```python
timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
    summary_file="data/S01_trial_summary.csv",
)
```

## Creating Screens

A screen is the smallest built-in presentation/response unit. It draws one or
more stimuli, optionally collects one key response, then returns one raw screen
row. Screens do not choose condition assignment, retry behavior, or trial
summaries.

Prefer `timeline.make_screen()` in experiment scripts. It returns a
`beh.timeline.Screen` object, but the construction path stays timeline-owned.

::: trackflow.beh.timeline.Timeline.make_screen
    options:
      heading_level: 3

Important arguments:

- `stimuli`: drawable objects for the screen.
- `duration`: maximum screen duration. `None` means the screen must end through
  a response.
- `response`: response mode. The default is `"key"`; use `None` only when no
  built-in response collection should run.
- `choices`: response-option list for the selected response mode.
- `data`: screen-level fields copied into each raw row.
- `on_start`, `on_load`, `on_frame`, `on_finish`: lifecycle hooks for setup,
  first-flip work, real-time checks, and final row edits.

For `response="key"`, pass PsychoPy key names such as
`choices=["f", "j"]`. `choices=None` accepts no participant response choices,
so the screen waits for its duration. Because `response="key"` is the default,
fixed-duration screens usually do not need to set `response`.

```python
screen = timeline.make_screen(
    stimuli=[fix],
    duration=0.5,
    data={"screen_name": "fixation"},
)
```

Instruction screens are ordinary screens created through convenience helpers.
Use `timeline.make_text_screen(...)` and `timeline.make_image_screen(...)` for
common instructions. These methods create screens only; they do not run or save
data until `timeline.run(...)` is called.

### `make_text_screen(text, *, text_kwargs=None, prompt_text=None, prompt_kwargs=None, ...)`

Create a text screen without running it.

| Parameter | Meaning | Default |
| --- | --- | --- |
| `text` | Text displayed by the main PsychoPy `TextStim`. | Required |
| `text_kwargs` | Keyword arguments forwarded to the main `TextStim`. | `None` |
| `prompt_text` | Optional prompt text shown near the bottom of the screen. | `None` |
| `prompt_kwargs` | Keyword arguments forwarded to the prompt `TextStim`. | `None` |
| `...` | Shared screen behavior arguments from `make_screen(...)`. | See `make_screen(...)` |

### `make_image_screen(image, *, image_kwargs=None, prompt_text=None, prompt_kwargs=None, ...)`

Create an image screen without running it.

| Parameter | Meaning | Default |
| --- | --- | --- |
| `image` | Image path or image object forwarded to PsychoPy `ImageStim`. | Required |
| `image_kwargs` | Keyword arguments forwarded to `ImageStim`. | `None` |
| `prompt_text` | Optional prompt text shown near the bottom of the screen. | `None` |
| `prompt_kwargs` | Keyword arguments forwarded to the prompt `TextStim`. | `None` |
| `...` | Shared screen behavior arguments from `make_screen(...)`. | See `make_screen(...)` |

Shared screen behavior arguments are `duration`, `response`, `choices`,
`response_start`, `end_on_response`, `clear_events`, `data`, `on_start`,
`on_load`, `on_frame`, and `on_finish`. These behave the same as in
`make_screen(...)`.

```python
instruction = timeline.make_text_screen(
    "Ready?",
    choices=["space"],
    prompt_text="Press Space to continue",
    text_kwargs={"height": 0.8, "color": "white"},
)

image_instruction = timeline.make_image_screen(
    "instruction.png",
    duration=1.0,
    image_kwargs={"size": (10, 6)},
)
```

When a timeline runs a screen, the row is built from current `trial_data`, the
screen's own `data`, response fields, and sync containers. Readable labels
such as `screen_name` are ordinary data fields.

## Creating Trials

Use `timeline.make_trial(...)` when multiple screens should run as one
trial-like procedure. The returned object is timeline-owned and intentionally
not exposed through a separate trials namespace. Use `run_if(ctx)` here when
an entire trial should be conditionally skipped.

::: trackflow.beh.timeline.Timeline.make_trial
    options:
      heading_level: 3

Important arguments:

- `screens`: ordered screens to present for one trial run.
- `data_format`: optional function that receives the trial's raw screen rows
  and returns one summary row.
- `run_if`: optional predicate for skipping the whole trial as a completed
  no-op.

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

## Running Units

Use `run()` as the only public execution entry point. A single screen is
automatically treated as a one-screen trial.

::: trackflow.beh.timeline.Timeline.run
    options:
      heading_level: 3

`run()` executes one screen or one trial-like object. `trial_data` controls what
data every screen row inherits for that one run:

- `unit`: one screen or one trial-like object.
- `trial_data=None`: run once with an empty trial-data dictionary.
- `trial_data={...}`: run once and copy that dictionary into each screen row.
- `record=False`: run with timeline context but skip raw, summary, and recovery
  writes.
- `return_status=True`: return `True` for accepted/completed trials and `False`
  for rejected or interrupted trials.

Use an ordinary Python loop for planned trial-data rows:

```python
timeline.run(screen)
timeline.run(trial, trial_data={"condition": "left"})

for row in trial_data:
    timeline.run(trial, trial_data=row)
```

Use `record=False` for screens that should use the timeline's window and
runtime context but should not be saved, such as a local break screen:

```python
break_screen = timeline.make_text_screen(
    text="Take a break. Press space when ready.",
    response="key",
    choices=["space"],
    data={"screen_name": "break"},
)
timeline.run(break_screen, record=False)
```

`timeline.run(...)` returns `None` by default. Completed data should be read
through `get_data(...)`, `get_last_data(...)`, raw JSONL output, or summary CSV
output. Use `return_status=True` only when experiment code needs an immediate
completion signal for manual retry or replacement logic:

```python
for row in trial_data:
    complete = timeline.run(trial, trial_data=row, return_status=True)
    if not complete:
        retry_rows.append(row)
```

## Trial Summaries

`data_format(screen_rows)` receives only the raw screen rows from the current
trial run and returns one optional summary row. Raw screen rows and summary
rows are stored separately so screen-level timing/response data stays intact.

## Screen-Level Interruptions

Use `on_finish(ctx, data)` when code needs the final row after built-in response
collection. Use `on_frame(ctx, data, elapsed)` when a screen needs real-time
checks during presentation. The frame hook can call `ctx.break_trial(...)` to
stop the current screen and trial immediately. Interrupted trials are saved with
`trial_status="interrupted"` and an `interruption` reason, are not marked
complete in recovery metadata, and return `False` when
`return_status=True`.

Function:

```python
ctx.break_trial(reason="...", screen=feedback_screen, data={...})
```

Arguments:

- `reason`: short cause saved as the interruption reason.
- `screen`: optional feedback screen displayed immediately and unrecorded.
- `data`: optional fields merged into the interrupted screen row and trial
  outcome details.

```python
def check_gaze(ctx, data, elapsed):
    try:
        ctx.timeline.gaze.check()
    except gaze.GazeBreakError as err:
        ctx.break_trial(
            reason="eye_movement",
            screen=eye_feedback_screen,
            data={"eye_x": err.x, "eye_y": err.y},
        )

sample_screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    on_frame=check_gaze,
)
```

The same mechanism can mark an early press during a pre-response screen:

```python
def check_early_press(ctx, data, elapsed):
    if participant_pressed_too_early():
        ctx.break_trial(reason="early_press")
```

## Reading Completed Data

`get_data()` returns filtered raw or summary rows. `get_last_data()` returns
the most recent screen, trial, block, or session.

::: trackflow.beh.timeline.Timeline.get_data
    options:
      heading_level: 3

::: trackflow.beh.timeline.Timeline.get_last_data
    options:
      heading_level: 3

Examples:

```python
response_rows = timeline.get_data(kind="raw", screen_name="response")
latest_trial = timeline.get_last_data(kind="summary", unit="trial")
```

## Low-Level Objects

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

# Behavior Timeline API

Reference for `trackflow.beh.timeline`, the runtime namespace for timelines,
screens, screen groups, completed rows, and device-send helpers.

## Setup

### `setup_timeline(...)`

Create a `Timeline`.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window used by timeline-owned screens. |
| `raw_data_file` | Optional JSONL output path for raw screen rows. |
| `summary_file` | Optional CSV output path for rows returned by trial `data_format`. |
| `meta_file`, `meta_state` | Optional completion-state storage for planned rows. |
| `params`, `state` | Stable settings and mutable runtime state exposed through `RunContext`. |
| `eeg`, `tracker` | Optional EEG sender and eye-tracker runtime used by send helpers and hooks. |
| `enable_quit_keys`, `quit_keys` | Researcher quit shortcut configuration. |
| `global_key_requests` | Mapping from state names to researcher shortcut keys. |
| Return | `Timeline`. |

```python
timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
)
```

## Screen creation

### `make_screen(...)`

Create one screen without running it.

| Argument | Description |
| --- | --- |
| `stimuli` | Drawable objects for the screen. Each object must provide `draw()`. |
| `duration` | Maximum duration in seconds. `None` requires the screen to end through a response. |
| `response` | Response mode. Use `"key"` for keyboard responses or `None` for no built-in response collection. |
| `choices` | Allowed response choices for the response mode. Keyboard choices are PsychoPy key names. |
| `response_start` | Seconds after screen onset before built-in responses are accepted. |
| `end_on_response` | Whether the first accepted response ends the screen. |
| `clear_events` | Whether to clear keyboard events before the screen starts. |
| `data` | Static screen-level fields copied into the raw screen row. |
| `on_start`, `on_load`, `on_frame`, `on_finish` | Optional lifecycle hooks receiving `ctx`, row `data`, and for `on_frame`, `elapsed`. |
| Return | `Screen`. |

```python
screen = timeline.make_screen(
    stimuli=[fix],
    duration=0.5,
    data={"screen_name": "fixation"},
)
```

### `make_text_screen(...)`

Create a text instruction screen without running it.

| Argument | Description |
| --- | --- |
| `text` | Main text displayed by a PsychoPy `TextStim`. |
| `text_kwargs` | Optional keyword arguments forwarded to the main `TextStim`. |
| `prompt_text`, `prompt_kwargs` | Optional prompt text and prompt `TextStim` keyword arguments. |
| Shared screen arguments | `duration`, `response`, `choices`, `response_start`, `end_on_response`, `clear_events`, `data`, and lifecycle hooks. |
| Return | `Screen`. |

```python
ready = timeline.make_text_screen(
    "Ready?",
    choices=["space"],
    prompt_text="Press Space to continue",
)
```

### `make_image_screen(...)`

Create an image instruction screen without running it.

| Argument | Description |
| --- | --- |
| `image` | Image path or object forwarded to PsychoPy `ImageStim`. |
| `image_kwargs` | Optional keyword arguments forwarded to `ImageStim`. |
| `image_units`, `image_size`, `scale`, `pos` | Image display settings. `scale="auto"` fits the image to the window. |
| `prompt_text`, `prompt_kwargs` | Optional prompt text and prompt `TextStim` keyword arguments. |
| Shared screen arguments | Same shared screen behavior arguments as `make_screen(...)`. |
| Return | `Screen`. |

```python
instruction = timeline.make_image_screen(
    "instruction.png",
    scale="auto",
    choices=["space"],
)
```

## Trial creation and running

### `make_trial(...)`

Create one ordered screen group without running it.

| Argument | Description |
| --- | --- |
| `screens` | Screens or screen-like units to run in order. |
| `data_format` | Optional callable receiving this run's raw screen rows and returning one summary row. |
| `run_if` | Optional predicate receiving `RunContext`; `False` skips the trial as a completed no-op. |
| Return | Timeline-owned trial-like object for `timeline.run(...)`. |

```python
trial = timeline.make_trial(
    screens=[fixation_screen, response_screen],
    data_format=lambda rows: {"response": rows[-1]["response_value"]},
)
```

### `run(...)`

Run one screen or one trial-like object.

| Argument | Description |
| --- | --- |
| `unit` | One `Screen` or object with `run(ctx)`. Lists are not accepted; loop explicitly. |
| `trial_data` | Optional dictionary copied into every raw screen row for this run. |
| `record` | When `False`, run with timeline context but skip raw rows, summary rows, and recovery writes. |
| `return_status` | When `True`, return completion status; otherwise return `None`. |
| Return | `None`, or `bool` when `return_status=True`. |

```python
timeline.run(trial, trial_data={"condition": "left"})
complete = timeline.run(trial, trial_data=row, return_status=True)
```

## Data access

Read completed raw screen rows or summary rows.

### `get_data(...)`

Return completed raw or summary rows matching exact field filters.

| Argument | Description |
| --- | --- |
| `kind` | Data view to read, usually `"raw"` for screen rows or `"summary"` for trial summary rows. |
| `**filters` | Exact field-value filters applied to completed rows. |
| Return | `DataCollection`. |

### `get_last_data(...)`

Return the latest screen, trial, block, or session rows.

| Argument | Description |
| --- | --- |
| `kind` | Data view to read, usually `"raw"` or `"summary"`. |
| `unit` | Grouping level such as `"screen"`, `"trial"`, `"block"`, or `"session"`. |
| Return | `DataCollection`. |

```python
responses = timeline.get_data(kind="raw", screen_name="response").to_list()
latest_trial = timeline.get_last_data(kind="summary", unit="trial").to_list()
```

## Device sends

Send configured EEG markers and EyeLink messages.

### `send(...)`

Send one EEG marker, one EyeLink message, or both.

| Argument | Description |
| --- | --- |
| `code` | Optional EEG marker code. |
| `message` | Optional EyeLink message text. |
| Return | `None`. |

### `send_eeg(...)`

Send one EEG marker.

| Argument | Description |
| --- | --- |
| `code` | EEG marker code. |
| Return | `None`. |

### `send_gaze(...)`

Send one EyeLink message, one EyeLink host status line, or both.

| Argument | Description |
| --- | --- |
| `message` | Optional EyeLink message text written to the EDF file. |
| `status` | Optional status text shown on the EyeLink host display. |
| Return | `None`. |

```python
timeline.send(timeline.code["sample"], message="sample")
timeline.send_gaze(message="sample_onset")
timeline.send_gaze(status="Block 1 / Trial 12")
```

Send helpers perform hardware side effects only. Experiment code must write any
saved marker or message fields into row data explicitly.

## Runtime context

Runtime object passed to custom trial-like objects and screen hooks.

### `RunContext`

| Attribute or method | Description |
| --- | --- |
| `win`, `timeline`, `trial_data` | Current PsychoPy window, timeline, and run-level data. |
| `params`, `state` | Timeline stable settings and mutable state. |
| `tracker` | Eye-tracker facade; no-op methods are available when no tracker is configured. |
| `screen` | Current screen during screen hooks. |
| `code` | Copy of the timeline EEG code dictionary. |
| `send(...)`, `send_eeg(...)`, `send_gaze(...)` | Context versions of the timeline send helpers. |
| `break_trial(screen=None, data=None)` | Interrupt the current trial from a screen hook. |

```python
def mark_sample(ctx, data):
    code = ctx.code["sample"]
    ctx.send(code, message="sample")
    data["EEG"] = code
```

## Custom trial outcomes

Return object for custom trial-like integrations.

### `TrialOutcome`

| Field | Description |
| --- | --- |
| `status` | Completion status such as accepted, rejected, or interrupted. |
| `row` | Optional summary-like row for the custom unit. |
| `screen_rows` | Raw screen rows produced by the custom unit. |
| `details` | Optional additional outcome fields. |

```python
return beh.timeline.TrialOutcome(
    status="accepted",
    screen_rows=[row],
)
```

## Low-level screen methods

Most scripts should create screens with timeline factory methods and run them
with `timeline.run(...)`.

### `update(...)`

Mutate prepared screen settings before a run. This can change timing, response
collection, or saved row fields.

### `run(...)`

Present this screen and return one raw row without timeline storage or summary
bookkeeping.

```python
screen.update(data={"screen_name": "practice_fixation"})
row = screen.run(win, ctx=ctx)
```

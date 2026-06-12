# Use screen hook functions

Use this guide when a screen needs to run code at a specific moment: when it
starts, when the first frame appears, on every frame, or after it finishes.

Hooks are ordinary Python functions passed to `timeline.make_screen(...)`. They
are useful for marker sends, gaze checks, row edits, and other runtime work
that belongs to a specific screen.

## Choose when your code should run

Use the hook that matches when the code should run during the screen:

- `on_start`: **before the screen appears**. Use it to change stimuli before
  the participant sees them.
- `on_load`: **when the screen first appears**. Use it to start recording or
  send a screen-start marker/message.
- `on_frame`: **while the screen is visible**. Use it for repeated checks or
  updates, such as gaze, response rules, changing stimuli, or stopping the
  trial.
- `on_finish`: **after the screen ends**. Use it to score the response or
  finish editing the saved row.

Hook functions usually receive `ctx` and `data`. `ctx` gives the hook access to
the running experiment, such as trial data, marker sending, and tracker access.
`data` is the row that will be saved for this screen.

## Change stimuli before the screen appears

Use `on_start` when trial information should change what the participant sees.

```python
word_stim = beh.stimuli.make_text(
    timeline.win,
    "",
    height=0.8,
    color="#000000",
)


def prepare_word(ctx, data):
    word_stim.params.text = ctx.trial_data["word"]
    word_stim.params.color = ctx.trial_data["word_color"]
    data["planned_word"] = ctx.trial_data["word"]
    data["planned_color"] = ctx.trial_data["word_color"]


word_screen = timeline.make_screen(
    stimuli=[word_stim],
    duration=1.0,
    response=None,
    on_start=prepare_word,
    data={"screen_name": "word"},
)
```

`on_start` runs before the first visible frame, so stimulus edits happen before
the participant sees the screen.

## Send a marker when the screen appears

Use `on_load` when a marker, message, or recording action should happen when
the screen first appears.

```python
def mark_sample(ctx, data):
    ctx.send(code=1, message="sample")
    data["EEG"] = 1
    data["ET_message"] = "sample"


sample_screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    response=None,
    on_load=mark_sample,
    data={"screen_name": "sample"},
)
```

`ctx.send(...)` sends hardware events only. It does not automatically save the
marker in behavior data, so the hook also writes `EEG` and `ET_message` into
the row.

The marker code and message label are experiment decisions. Keep them explicit
in the hook or in a visible settings file.

## Check or update while the screen is visible

Use `on_frame` for repeated checks or updates while the screen is visible. The
hook receives `elapsed`, the number of seconds since the screen started.

```python
from trackflow import gaze


def check_fixation(ctx, data, elapsed):
    try:
        ctx.tracker.check_fixation()
    except gaze.GazeBreakError as err:
        data["reason"] = "eye_movement"
        ctx.break_trial(data={"eye_x": err.x, "eye_y": err.y})


sample_screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    response=None,
    on_frame=check_fixation,
    data={"screen_name": "sample"},
)
```

This example shows where a gaze check belongs. It does not decide what your
experiment should do after an eye movement. Retry, replacement, exclusion, and
feedback rules should remain visible in your experiment flow.

## Score the response after the screen ends

Use `on_finish` when the saved field depends on the final response.

```python
def score_response(ctx, data):
    correct_key = ctx.trial_data["correct_key"]
    data["correct_key"] = correct_key
    data["correct"] = data["response_value"] == correct_key


response_screen = timeline.make_screen(
    stimuli=[probe],
    duration=2.0,
    choices=["f", "j"],
    on_finish=score_response,
    data={"screen_name": "response"},
)
```

The timeline collects the response first, then calls `on_finish`, so
`response_value` and `rt` are available to the scoring function.

## Where to go next

- Read [Understand Timeline Data](timeline-data.md) to see how hook edits
  appear in raw rows and summaries.
- Read [Add EEG and Eye Tracking Later](eeg-eye-tracking.md) for hardware setup
  before using send and tracker hooks.
- Use the [RunContext API](../api/beh/timeline.md#runtime-context) for exact
  context attributes.

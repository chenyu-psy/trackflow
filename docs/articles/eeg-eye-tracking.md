# Add EEG and eye tracking later

Use this guide when the behavior task works and you are ready to connect EEG
markers or EyeLink eye tracking.

Add hardware in small steps. First run the behavior task without hardware.
Then use debug senders and debug trackers. Finally switch to real hardware on
the lab computer and check marker timing, EyeLink messages, and output files
with test data.

## Add an EEG sender

Use debug mode while developing:

```python
from trackflow import eeg


sender = eeg.setup_port(
    debug=True,
    code={
        "sample": 21,
        "response": 31,
    },
)
```

Use real mode in the lab with the correct port address:

```python
sender = eeg.setup_port(
    port_address=0xD010,
    pulse_width=0.005,
    code={
        "sample": 21,
        "response": 31,
    },
)
```

Marker codes must be explicit integers. The package sends pulses; it does not
decide marker labels or when markers should be sent.

## Add an EyeLink tracker

Use a debug tracker while developing without EyeLink hardware:

```python
from trackflow import gaze


tracker = gaze.setup_tracker(
    win=win,
    cfg=gaze.GazeConfig(tracked_eye="BOTH", max_dist_deg=1.25),
    edf_name="S01.edf",
    monitor=monitor,
    debug=True,
)
```

On the lab computer, use the same setup with `debug=False` and the correct lab
configuration.

The tracker owns EyeLink setup, EDF handling, recording, message sends, and
fixation checks. Your experiment still decides when to calibrate, when to
record, which screens should check fixation, and what to do after a gaze break.

## Pass devices to the timeline

Create the timeline with the sender and tracker:

```python
from trackflow import beh


timeline = beh.timeline.setup_timeline(
    win=win,
    eeg=sender,
    tracker=tracker,
    raw_data_file="data/S01_screen_data.jsonl",
)
```

The devices are then available in screen hooks through `ctx`.

## Send markers from a screen

Use a hook when a marker belongs to a screen event:

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

`ctx.send(...)` can send an EEG marker, an EyeLink message, or both. It does
not automatically write behavior data, so save marker fields explicitly when
you want them in the row.

## Send markers outside a screen

For block starts, pauses, or other events outside a screen hook, call the
timeline directly:

```python
timeline.send(code=1, message="block_start")
```

Use this for events that are not tied to a screen's first flip or frame loop.

## Check gaze during selected screens

Call `ctx.tracker.check_fixation()` from `on_frame` only on screens where
fixation should be checked:

```python
from trackflow import gaze


def check_sample_fixation(ctx, data, elapsed):
    try:
        ctx.tracker.check_fixation()
    except gaze.GazeBreakError as err:
        data["reason"] = "eye_movement"
        ctx.break_trial(data={"eye_x": err.x, "eye_y": err.y})


sample_screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    response=None,
    on_frame=check_sample_fixation,
    data={"screen_name": "sample"},
)
```

This stops the current trial and records the interruption fields. It does not
decide whether the trial should be retried, skipped, replaced, or excluded.
Keep that policy in the experiment flow where it can be reviewed.

## Keep hardware decisions explicit

Before collecting data, check these values in the experiment code or settings:

- EEG marker codes and labels
- EyeLink message labels
- screens that send markers
- screens that check fixation
- calibration and recording points
- retry, replacement, and exclusion rules
- saved marker and gaze fields

These are experiment design decisions. `trackflow` provides the runtime hooks,
but the experiment script should make the decisions visible.

## Where to go next

- Read [Use Screen Hook Functions](screen-hook-functions.md) for the hook
  timing model.
- Use the [EEG API](../api/eeg.md) and [Eye tracking API](../api/gaze/index.md)
  for exact setup arguments and tracker methods.

# Eye Tracking

`trackflow.gaze` creates the EyeLink tracker runtime used by behavior
timelines. Ordinary scripts should get a tracker from `gaze.setup_tracker(...)`
and pass it to `beh.timeline.setup_timeline(..., tracker=tracker)`, not create
tracker classes directly.

The tracker owns EyeLink setup, EDF handling, recording, message sends, and
realtime fixation checks. Experiment code still decides whether eye tracking is
enabled, when recording starts, which phases check fixation, and what to do
after a gaze break.

See the [Eye tracking API reference](reference.md) for tracker configuration
and method details.

## Overview

Use `gaze.GazeConfig` to define tracker settings, `gaze.setup_tracker(...)` to
open a connected or debug tracker, and `ctx.tracker` inside timeline hooks for
selected-screen fixation checks. The tracker can detect gaze breaks, but it
does not choose retry, replacement, exclusion, or trial-count policy.

## Typical Use

```python
from trackflow import beh, gaze

tracker = gaze.setup_tracker(
    win=win,
    cfg=gaze.GazeConfig(tracked_eye="BOTH", max_dist_deg=1.25),
    edf_name="S01.edf",
    monitor=monitor,
    debug=False,
)
timeline = beh.timeline.setup_timeline(win=win, tracker=tracker)

tracker.run_calibration()
tracker.start_recording()
tracker.start_tracking()

def check_gaze(ctx, data, elapsed):
    try:
        ctx.tracker.check_fixation()
    except gaze.GazeBreakError as err:
        ctx.break_trial(
            reason="eye_movement",
            data={"eye_x": err.x, "eye_y": err.y},
        )

sample_screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    on_frame=check_gaze,
    data={"screen_name": "sample"},
)
timeline.run(sample_screen)
tracker.close(save_as="S01.edf")
```

For local development or behavior-only checks, pass `debug=True`. Debug
trackers provide the same tracker-facing methods with no EyeLink connection.

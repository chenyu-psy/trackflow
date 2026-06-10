# Eye Tracking API

`trackflow.gaze` contains EyeLink setup and realtime gaze-monitoring helpers
for PsychoPy experiments. The package provides small runtime pieces; the
experiment script still decides whether eye tracking is enabled, when
recording starts, which trial phases are monitored, and what to do after a
gaze break.

## Overview

Use the gaze API when a script needs to:

1. Configure EyeLink calibration and realtime fixation checks.
2. Open a connected or debug tracker.
3. Run calibration and recording at explicit points in the experiment.
4. Check gaze during selected behavior screens.
5. Save or react to gaze-break details in experiment code.

The realtime monitor detects gaze breaks. It does not choose retry,
replacement, exclusion, or trial-count policy. Keep those decisions visible in
ordinary experiment control flow, usually around `timeline.run(...)`.

```python
from trackflow import beh, gaze

cfg = gaze.GazeConfig(tracked_eye="BOTH", max_dist_deg=1.25)
tracker = gaze.setup_tracker(
    win=win,
    cfg=cfg,
    edf_name="S01.edf",
    monitor=monitor,
    debug=False,
)

timeline = beh.timeline.setup_timeline(win=win, gaze=tracker)
gaze_monitor = tracker.make_monitor(fixation=fixation)
```

## Tracker Setup

Create a `GazeConfig` for eye-tracking settings, then pass it to
`setup_tracker(...)`. Real setup connects to EyeLink, opens the EDF file,
initializes graphics, sends stable tracker settings, and leaves calibration to
the experiment script.

```python
cfg = gaze.GazeConfig(
    tracked_eye="BOTH",
    calibration_type="HV9",
    calibration_area=(0.5, 0.5),
    max_dist_deg=1.25,
)

tracker = gaze.setup_tracker(
    win=win,
    cfg=cfg,
    edf_name="S01.edf",
    monitor=monitor,
)
tracker.run_calibration()
tracker.start_recording()
```

Use debug mode for local development, tests, or behavior-only sessions that
should not import `pylink` or connect to EyeLink:

```python
tracker = gaze.setup_tracker(
    win=win,
    cfg=gaze.GazeConfig(),
    edf_name="S01.edf",
    monitor=monitor,
    debug=True,
)
```

EDF filenames are EyeLink host filenames. They must include `.edf` and fit the
short host filename limit. Use `tracker.close(save_as=...)` near the end of the
session to stop recording, close the EDF, transfer it, and close the tracker
connection.

## Realtime Monitoring

Create a monitor from the tracker after setup. The monitor uses
`GazeConfig.max_dist_deg` as the default fixation radius.

```python
gaze_monitor = tracker.make_monitor(fixation=fixation)
gaze_monitor.start()
```

Use a screen `on_frame` hook for realtime checks during phases that should be
fixation-constrained. The hook can interrupt the current trial and save the
measured gaze position in the interrupted raw row.

```python
def check_gaze(ctx, data, elapsed):
    try:
        gaze_monitor.check()
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
```

Use `ctx.send(..., message="...")` or `ctx.send_gaze(...)` in screen hooks when
EyeLink messages should be recorded alongside behavior rows.

If a script needs gaze-specific feedback after a break, call
`gaze_monitor.show_feedback(...)` from explicit experiment code. It shows the
fixation location and measured gaze-break position. It does not choose retry,
replacement, or exclusion policy.

## API Reference

### Configuration

::: trackflow.gaze.GazeConfig
    options:
      heading_level: 4

### Tracker Setup

::: trackflow.gaze.setup_tracker
    options:
      heading_level: 4

### Realtime Monitor

::: trackflow.gaze.GazeMonitor
    options:
      heading_level: 4
      members:
        - start
        - stop
        - check
        - show_feedback

### GazeBreakError

`gaze_monitor.check()` raises `gaze.GazeBreakError` when gaze leaves the
allowed fixation radius. Use `err.x` and `err.y` for the screen-centered gaze
offset in pixels when saving gaze-break details into behavior rows.
`gaze_monitor.show_feedback(err)` can use the same error object to display the
measured break position.

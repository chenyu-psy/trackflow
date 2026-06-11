# Eye Tracking API Reference

Ordinary scripts should get trackers from `gaze.setup_tracker(...)`. The
tracker classes documented here describe the method shape returned by setup;
scripts should not instantiate those classes directly.

## Configuration

::: trackflow.gaze.GazeConfig
    options:
      heading_level: 3

## Tracker Setup

::: trackflow.gaze.setup_tracker
    options:
      heading_level: 3

## Tracker Runtime

`setup_tracker(...)` returns a tracker runtime. The connected tracker methods
below are the public method shape ordinary scripts should use; debug trackers
provide the same methods with safe no-op behavior where hardware is absent.
The methods are grouped by the part of the experiment flow they support.

### Calibration and drift correction

Use these before task trials, or when the researcher needs to recalibrate during
the session.

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 4
      members:
        - run_calibration
        - run_drift_correction

### Recording and EDF lifecycle

Use these around the parts of the experiment that should be recorded to the EDF
file, then close and transfer the file at the end of the session.

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 4
      members:
        - start_recording
        - stop_recording
        - close

### Realtime fixation checks

Use these only for phases that should be fixation-constrained; retry,
replacement, and exclusion policy remain experiment-script decisions.

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 4
      members:
        - start_tracking
        - stop_tracking
        - check_fixation
        - show_feedback

### EyeLink messages

Use this for EyeLink-only messages. In timeline hooks, `ctx.send_gaze(...)` and
`ctx.send(..., message=...)` call the configured tracker for you.

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 4
      members:
        - send_msg

## GazeBreakError

`gaze.GazeBreakError` is raised by tracker-owned fixation checks when gaze
leaves the allowed fixation radius. It carries the measured screen-centered
offset as `err.x`, `err.y`, and `err.pos`.

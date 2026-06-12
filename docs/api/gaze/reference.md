# Eye Tracking API Reference

Reference for `trackflow.gaze`. Ordinary scripts should create trackers with
`gaze.setup_tracker(...)`; the tracker classes document the returned method
shape.

## `GazeConfig`

Configuration for EyeLink setup and realtime gaze monitoring.

| Field | Description |
| --- | --- |
| `tracked_eye` | `"LEFT"`, `"RIGHT"`, or `"BOTH"`. Defaults to `"BOTH"`. |
| `calibration_type` | EyeLink calibration layout, such as `"HV9"`. |
| `calibration_area` | Width and height proportions used for calibration and validation. |
| `max_dist_deg` | Allowed realtime fixation distance in visual degrees. |
| `bg_color` | HEX background color for gaze/calibration pages. |
| `eyelink_settings` | Optional EyeLink command overrides. |

::: trackflow.gaze.GazeConfig
    options:
      heading_level: 3

```python
cfg = gaze.GazeConfig(
    tracked_eye="BOTH",
    max_dist_deg=1.25,
)
```

## `setup_tracker(...)`

Create and initialize a connected or debug tracker.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window used for tracker setup and feedback drawing. |
| `cfg` | `GazeConfig`. |
| `edf_name` | Short EDF filename opened on the EyeLink host. Must include `.edf`. |
| `monitor` | Optional PsychoPy monitor used for degree-to-pixel conversion. |
| `debug` | When `True`, return a debug tracker without importing or connecting to EyeLink. |
| Return | `ConnectedEyeLinker` or `DebugEyeLinker`. Calibration is not run automatically. |

::: trackflow.gaze.setup_tracker
    options:
      heading_level: 3

```python
tracker = gaze.setup_tracker(
    win=win,
    cfg=cfg,
    edf_name="S01.edf",
    monitor=monitor,
    debug=True,
)
```

## Calibration and drift correction

Methods used before or between task trials.

| Method | Description |
| --- | --- |
| `run_calibration(...)` | Apply optional per-call calibration settings and run calibration. |
| `run_drift_correction(position=None, setup=1)` | Run EyeLink drift correction. |

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 3
      members:
        - run_calibration
        - run_drift_correction

```python
tracker.run_calibration()
tracker.run_drift_correction()
```

## Recording and EDF lifecycle

Methods for recording and saving the EDF file.

| Method | Description |
| --- | --- |
| `start_recording()` | Start EyeLink recording. |
| `stop_recording()` | Stop EyeLink recording. |
| `close(save_as=None)` | Finalize recording, close the connection, and transfer the EDF. |

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 3
      members:
        - start_recording
        - stop_recording
        - close

```python
tracker.start_recording()
tracker.stop_recording()
tracker.close(save_as="S01.edf")
```

## Realtime fixation checks

Methods for phases where experiment code chooses to monitor fixation.

| Method | Description |
| --- | --- |
| `start_tracking()` | Start the internal realtime gaze monitor. |
| `stop_tracking()` | Stop the internal realtime gaze monitor. |
| `check_fixation()` | Return `True` when fixation is valid; raise `GazeBreakError` on a measured break. |
| `show_feedback(error=None, continue_keys=("space",))` | Show gaze-break feedback using the internal monitor. |

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 3
      members:
        - start_tracking
        - stop_tracking
        - check_fixation
        - show_feedback

```python
tracker.start_tracking()
try:
    tracker.check_fixation()
except gaze.GazeBreakError as err:
    tracker.show_feedback(err)
```

Fixation checks report breaks only. Retry, exclusion, replacement, and saved
row fields remain experiment-script decisions.

## EyeLink messages

Methods for EyeLink host commands and EDF messages.

| Method | Description |
| --- | --- |
| `send_msg(msg)` | Send a message to the EDF file. |
| `send_status(status)` | Send a researcher-facing status line to the EyeLink host display. |
| `send_command(cmd)` | Send a raw EyeLink host command. |

::: trackflow.gaze.ConnectedEyeLinker
    options:
      show_root_heading: false
      heading_level: 3
      members:
        - send_msg
        - send_status
        - send_command

```python
tracker.send_msg("sample_onset")
```

Inside timeline hooks, prefer `ctx.send_gaze(...)` or
`ctx.send(..., message=...)` when the tracker is attached to a timeline.

## `GazeBreakError`

Exception raised by realtime fixation checks when gaze leaves the allowed
radius.

| Attribute | Description |
| --- | --- |
| `x`, `y` | Screen-centered gaze offset in pixels. |
| `pos` | `(x, y)` tuple. |
| `left`, `right` | Optional raw left/right gaze samples. |

::: trackflow.gaze.GazeBreakError
    options:
      heading_level: 3

```python
except gaze.GazeBreakError as err:
    data["eye_x"] = err.x
    data["eye_y"] = err.y
```

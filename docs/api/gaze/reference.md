# Eye Tracking API

Reference for `trackflow.gaze`. Ordinary scripts should create trackers with
`gaze.setup_tracker(...)`; the tracker classes document the returned method
shape.

## Configuration

### `GazeConfig`

Configuration for EyeLink setup and realtime gaze monitoring.

| Field | Description |
| --- | --- |
| `tracked_eye` | `"LEFT"`, `"RIGHT"`, or `"BOTH"`. Defaults to `"BOTH"`. |
| `calibration_type` | EyeLink calibration layout, such as `"HV9"`. |
| `calibration_area` | Width and height proportions used for calibration and validation. |
| `max_dist_deg` | Allowed realtime fixation distance in visual degrees. |
| `bg_color` | HEX background color for gaze/calibration pages. |
| `eyelink_settings` | Optional EyeLink command overrides. |

```python
cfg = gaze.GazeConfig(
    tracked_eye="BOTH",
    max_dist_deg=1.25,
)
```

## Tracker setup

### `setup_tracker(...)`

Create and initialize a connected or debug tracker.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window used for tracker setup and feedback drawing. |
| `cfg` | `GazeConfig`. |
| `edf_name` | Short EDF filename opened on the EyeLink host. Must include `.edf`. |
| `monitor` | Optional PsychoPy monitor used for degree-to-pixel conversion. |
| `debug` | When `True`, return a debug tracker without importing or connecting to EyeLink. |
| Return | `ConnectedEyeLinker` or `DebugEyeLinker`. Calibration is not run automatically. |

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

### `run_calibration(...)`

Apply optional per-call calibration settings and run calibration.

| Argument | Description |
| --- | --- |
| `calibration_type` | Optional EyeLink calibration layout override. |
| `calibration_area` | Optional width and height proportions used for this calibration call. |
| Return | `None`. |

### `run_drift_correction(...)`

Run EyeLink drift correction.

| Argument | Description |
| --- | --- |
| `position` | Optional screen position for drift correction. |
| `setup` | EyeLink setup flag. Defaults to `1`. |
| Return | `None`. |

```python
tracker.run_calibration()
tracker.run_drift_correction()
```

## Recording lifecycle

Methods for recording and saving the EDF file.

### `start_recording(...)`

Start EyeLink recording.

| Return | Description |
| --- | --- |
| `None` | Recording starts on the configured tracker. |

### `stop_recording(...)`

Stop EyeLink recording.

| Return | Description |
| --- | --- |
| `None` | Recording stops on the configured tracker. |

### `close(...)`

Finalize recording, close the connection, and transfer the EDF.

| Argument | Description |
| --- | --- |
| `save_as` | Optional EDF filename for transfer. |
| Return | `None`. |

```python
tracker.start_recording()
tracker.stop_recording()
tracker.close(save_as="S01.edf")
```

## Realtime fixation checks

Methods for phases where experiment code chooses to monitor fixation.

### `start_tracking(...)`

Start the internal realtime gaze monitor.

| Return | Description |
| --- | --- |
| `None` | The realtime monitor begins sampling gaze. |

### `stop_tracking(...)`

Stop the internal realtime gaze monitor.

| Return | Description |
| --- | --- |
| `None` | The realtime monitor stops sampling gaze. |

### `check_fixation(...)`

Return `True` when fixation is valid; raise `GazeBreakError` on a measured
break.

| Return | Description |
| --- | --- |
| `bool` | `True` when fixation is valid. |

### `show_feedback(...)`

Show gaze-break feedback using the internal monitor.

| Argument | Description |
| --- | --- |
| `error` | Optional `GazeBreakError` used to draw feedback. |
| `continue_keys` | Keys that allow the researcher or participant to continue. Defaults to `("space",)`. |
| Return | `None`. |

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

### `send_msg(...)`

Send a message to the EDF file.

| Argument | Description |
| --- | --- |
| `msg` | Message text written to the EDF file. |
| Return | `None`. |

### `send_status(...)`

Send a researcher-facing status line to the EyeLink host display.

| Argument | Description |
| --- | --- |
| `status` | Status text shown on the EyeLink host display. |
| Return | `None`. |

### `send_command(...)`

Send a raw EyeLink host command.

| Argument | Description |
| --- | --- |
| `cmd` | Raw EyeLink command text. |
| Return | `None`. |

```python
tracker.send_msg("sample_onset")
```

Inside timeline hooks, prefer `ctx.send_gaze(...)` or
`ctx.send(..., message=...)` when the tracker is attached to a timeline.

## Gaze errors

### `GazeBreakError`

Exception raised by realtime fixation checks when gaze leaves the allowed
radius.

| Attribute | Description |
| --- | --- |
| `x`, `y` | Screen-centered gaze offset in pixels. |
| `pos` | `(x, y)` tuple. |
| `left`, `right` | Optional raw left/right gaze samples. |

```python
except gaze.GazeBreakError as err:
    data["eye_x"] = err.x
    data["eye_y"] = err.y
```

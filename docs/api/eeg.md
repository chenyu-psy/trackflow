# EEG API

Reference for `trackflow.eeg`, which creates EEG marker senders for real
parallel-port hardware or debug runs.

## Configuration

### `EEGConfig`

Configuration object for real parallel-port EEG marker setup.

| Field | Description |
| --- | --- |
| `port_address` | Integer parallel-port address for real hardware. Required when using `EEGConfig`. |
| `pulse_width` | Seconds to hold the marker code before resetting the port to zero. Defaults to `0.005`. |
| `code` | Optional named marker-code dictionary for experiment scripts. Values must be marker integers `1..255`. |

```python
from trackflow import eeg

cfg = eeg.EEGConfig(
    port_address=0xD010,
    code={"sample": 21},
)
```

## Port setup

### `setup_port(...)`

Create a marker sender.

| Argument | Description |
| --- | --- |
| `cfg` | Optional `EEGConfig`. |
| `port_address` | Hardware address used when `cfg` is omitted. Required for real hardware unless `port` is supplied. |
| `pulse_width` | Optional pulse-width override. |
| `code` | Optional named marker-code dictionary. |
| `debug` | When `True`, return a debug sender and do not import PsychoPy hardware modules. |
| `port`, `core` | Optional already-open objects, mainly for tests or custom hardware setup. |
| Return | `ParallelPortMarkerSender` or `DebugMarkerSender`, both with `send(code)`. |

```python
sender = eeg.setup_port(
    debug=True,
    code={"sample": 21},
)
sender.send(sender.code["sample"])
```

## Marker sending

Both sender types expose the same user-facing marker method.

### `send(...)`

Send one EEG marker through a real or debug marker sender.

| Sender | Effect |
| --- | --- |
| `ParallelPortMarkerSender` | Write `code`, wait `pulse_width`, then reset the port to `0`. |
| `DebugMarkerSender` | Validate and append `code` to `sent_codes`. |

| Argument | Description |
| --- | --- |
| `code` | Marker code in the 8-bit parallel-port range `1..255`. |
| Return | `None`. |

```python
sender.send(21)
```

`send(...)` only performs the marker side effect. It does not create behavior
data rows or save marker fields.

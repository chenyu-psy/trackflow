# EEG API

`trackflow.eeg` configures EEG trigger sending for PsychoPy experiments. It
keeps PsychoPy imports lazy, requires an explicit real port address, and
provides a debug mode for development without EEG hardware.

## Overview

Use the EEG API when a script needs to:

1. Configure an EEG trigger sender.
2. Send one marker pulse and reset the port to zero.
3. Store a named code dictionary for readable experiment hooks.
4. Combine EEG markers with EyeLink messages through `ctx.send(...)`.

The sender only sends pulses. It does not decide marker labels, marker timing,
or send timing. Those choices belong in the experiment script and screen
lifecycle hooks.

## Setup

Use debug mode while developing or testing without a parallel port:

```python
from trackflow import eeg

sender = eeg.setup_port(
    debug=True,
    code={"sample": 21, "response": 31},
)

sender.send(sender.code["sample"])
```

Use real mode in the lab with an explicit port address:

```python
from trackflow import eeg

sender = eeg.setup_port(
    port_address=0xD010,
    pulse_width=0.005,
    code={"sample": 21, "response": 31},
)
```

Marker codes must be integers in the non-zero 8-bit trigger range, `1..255`.
The sender writes the code, waits for `pulse_width` seconds, then resets the
port to zero.

`setup_port(...)` returns a sender object. In debug mode, the sender validates
codes and records them for testing. In real mode, it sends pulses through the
configured parallel port. User scripts normally do not need to know the sender
class names.

## Sending Markers In Behavior Hooks

Pass the configured sender to the behavior timeline so hooks can use
`ctx.send(...)`. `ctx.code` exposes the sender's named code dictionary, but
`ctx.send(...)` requires a numeric code so marker lookup stays explicit.

```python
from trackflow import beh, eeg

sender = eeg.setup_port(
    debug=True,
    code={"sample": 21, "response": 31},
)
timeline = beh.timeline.setup_timeline(win=win, eeg=sender)

def mark_sample(ctx, data):
    code = ctx.code["sample"]
    ctx.send(code, message="sample")
    data["EEG"] = code
    data["ET_message"] = "sample"

sample_screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    on_load=mark_sample,
    data={"screen_name": "sample"},
)
```

`ctx.send(...)` sends hardware events only. It does not write behavior data.
Use hook code such as `data["EEG"] = code` when the marker should be saved in
the current row. Use `ctx.send_eeg(...)` or `ctx.send_gaze(...)` for
single-device sends.

## Direct Sends

For simple scripts that do not use a behavior timeline, call the sender
directly:

```python
sender.send(21)
```

Use `ctx.send(...)` inside behavior hooks when a script needs one call to send
an EEG marker and an optional EyeLink message.

For trial-outside sends such as block starts, call the timeline directly:

```python
timeline.send(timeline.code["block_start"], message="block_start")
```

## API Reference

### Configuration

::: trackflow.eeg.EEGConfig
    options:
      heading_level: 4

### Setup

::: trackflow.eeg.setup_port
    options:
      heading_level: 4

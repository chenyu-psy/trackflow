# Behavior API

`trackflow.beh` is organized by runtime responsibility. Import the behavior
package once, then use the submodule namespace that matches the part of the
experiment script you are writing.

```python
from trackflow import beh

fix = beh.stimuli.make_fixation(win, size=0.5)
screen = beh.screens.make_screen(stimuli=[fix], duration=0.5)
timeline = beh.timeline.setup_timeline()
```

This structure keeps stimulus timing, screen presentation, trial scheduling,
data output, and recovery helpers visible instead of flattening them into one
large behavior namespace.

## Sections

- [Stimuli](beh/stimuli.md): timed drawable wrappers and fixation helpers.
- [Screens](beh/screens.md): simple fixed-duration and first-key screen units.
- [Timeline](beh/timeline.md): behavior runtime state and output bookkeeping.
- [Trials](beh/trials.md): trial runners, outcomes, and hook context.
- [Trial planning](beh/design.md): explicit condition expansion and planned rows.
- [Data output](beh/data.md): row views and summary conversion.
- [Recovery](beh/recovery.md): meta-JSON state for continue-mode scheduling.
- [Preflight](beh/preflight.md): opt-in runtime checks.
- [Global keys](beh/keys.md): researcher pause/quit key action definitions.

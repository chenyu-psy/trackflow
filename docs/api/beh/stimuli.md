# Behavior Stimuli

Stimulus helpers wrap PsychoPy-native drawables with screen-relative timing.
They are part of `trackflow.beh` because their timing contract is consumed by
behavior screens.

```python
from trackflow import beh

fix = beh.stimuli.make_fixation(win, size=0.5, color="#000000")
screen = beh.screens.make_screen(stimuli=[fix], duration=0.5)
```

::: trackflow.beh.stimuli
    options:
      members:
        - Timing
        - Stimulus
        - FixationParams
        - FixationStim
        - wrap_stimulus
        - make_fixation

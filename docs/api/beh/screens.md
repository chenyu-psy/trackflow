# Behavior Screens

Screens are the smallest built-in presentation unit. Use them for simple
fixed-duration displays and first-key responses; write ordinary PsychoPy code
for complex trial logic.

## Overview

A screen owns one short presentation step: draw one or more stimuli, optionally
collect one key response, then return one raw screen row. Screens do not choose
condition assignment, retry behavior, or trial summaries.

```python
from trackflow import beh

screen = beh.screens.make_screen(
    stimuli=[fix],
    duration=0.5,
    response=None,
    screen_name="fixation",
)
```

## Creating Screens

Prefer `make_screen()` in experiment scripts. It returns a `Screen` object and
keeps screen construction visually separate from stimulus construction.

::: trackflow.beh.screens.make_screen
    options:
      heading_level: 3

## Screen Methods

Most scripts create screens through `make_screen()`. The methods below are
useful when a script needs to update a prepared screen before a run, or when a
timeline executes the screen.

::: trackflow.beh.screens.Screen.update
    options:
      heading_level: 3

Use `update()` before the screen is run when a script needs to reuse a prepared
screen object with new presentation settings.

```python
screen.update(
    stimuli=[new_fix],
    duration=0.75,
    screen_name="long_fixation",
)
```

::: trackflow.beh.screens.Screen.run
    options:
      heading_level: 3

Most experiment scripts should let a timeline run screens so data recording
and runtime bookkeeping stay in one place.

```python
timeline.show_screen(win, screen)
```

Call `run()` directly only for low-level integrations that need the raw screen
row without timeline storage.

```python
row = screen.run(win, screen_index=0, row={"trial_id": 1})
```

# Behavior API

`trackflow.beh` is organized around `beh.timeline`. A timeline owns the
runtime context, creates screens and ordered screen groups, runs them, and
stores completed data. Stimuli remain ordinary timed drawables; screen and
trial concepts are documented inside the timeline API because they are created
and run by a timeline.

```python
from trackflow import beh

timeline = beh.timeline.setup_timeline(win=win)
fix = beh.stimuli.make_fixation(win, size=0.5)
screen = timeline.make_screen(stimuli=[fix], duration=0.5)
trial = timeline.make_trial(screens=[screen])
timeline.run(trial, trial_data={"condition": "practice"})
```

The usual learning path is:

1. Create a timeline with the PsychoPy window and output settings.
2. Learn the timeline factory and run methods.
3. Create stimuli with `beh.stimuli`.
4. Create screens through timeline factory methods.
5. Combine screens into trials through `timeline.make_trial(...)`.
6. Run one screen or one trial at a time with
   `timeline.run(..., trial_data=...)`.
7. Query completed raw screen rows or summary rows through timeline data
   helpers.

Use normal Python loops for multiple planned rows. Rejected or interrupted
trials are recorded for auditability, but retry policy stays in experiment
code.

This structure keeps trial flow, stimulus timing, screen presentation,
timeline bookkeeping, and data output visible instead of flattening them into
one large runner.

## Sections

- [Timeline](beh/timeline.md): runtime context, factories, execution, and data.
- [Stimuli](beh/stimuli.md): timed drawable wrappers and fixation helpers.
- [Trial planning](beh/design.md): explicit condition expansion into trial data.
- [Data output](beh/data.md): row views and summary conversion.

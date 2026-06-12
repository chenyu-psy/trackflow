# Behavior API

Reference for `trackflow.beh`, the behavior runtime namespace.

| Page | API area |
| --- | --- |
| [Timeline](beh/timeline.md) | Create timelines, screens, trials, run units, send device events, and read completed rows. |
| [Stimuli](beh/stimuli.md) | Create timed PsychoPy drawables for timeline screens. |
| [Trial planning](beh/design.md) | Build explicit trial-data rows and balance checks. |
| [Data output](beh/data.md) | Filter and convert completed raw or summary rows. |

```python
from trackflow import beh

timeline = beh.timeline.setup_timeline(win=win)
fix = beh.stimuli.make_fixation(win)
screen = timeline.make_screen(stimuli=[fix], duration=0.5)
timeline.run(screen)
```

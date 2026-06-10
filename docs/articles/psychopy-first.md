# PsychoPy-first runtime helpers

`trackflow` is designed to support PsychoPy experiments, not replace their
procedure code. This matters because experiment scripts often encode design
decisions that affect participant behavior, EEG markers, eye-tracking records,
or saved data meanings.

## Use simple screens when they fit

Use `timeline.make_screen()` for screens with a small, explicit contract:

- draw one or more stimuli
- optionally collect one keyboard response
- stop after a fixed duration or the first accepted response
- save one raw screen row

```python
timeline = beh.timeline.setup_timeline(win=win)
screen = timeline.make_screen(
    stimuli=[fixation],
    duration=0.5,
    response=None,
    data={"screen_name": "fixation"},
)
timeline.run(screen)
```

This is a convenience path for common screens. It should not force complex
trials into a generic screen abstraction.

## Write normal PsychoPy for complex trials

When a trial needs custom frame logic, mouse responses, multiple response
streams, custom clocks, `win.callOnFlip(...)`, or task-specific branching,
write the PsychoPy loop directly.

Return a `beh.timeline.TrialOutcome` so `trackflow` can still write raw rows,
summaries, and recovery metadata.

```python
from trackflow import beh


class SearchTrial:
    def run(self, ctx):
        screen_rows = []

        # Ordinary PsychoPy drawing, flipping, response collection, and sync
        # logic live here so the procedure remains inspectable.

        return beh.timeline.TrialOutcome(
            status="accepted",
            reason="no",
            row={"plan_id": ctx.trial_data["plan_id"]},
            screen_rows=screen_rows,
        )
```

## Keep sync explicit

Lifecycle hooks can send EEG markers and EyeLink messages, but the returned
records should be written into the current data row by the experiment code.

```python
def mark_sample(ctx, data):
    result = ctx.sync.send(21, gaze_message="sample")
    data["markers"].extend(result.markers)
    data["messages"].extend(result.messages)
```

This makes marker labels, marker codes, and saved records visible in the
experiment source.

## Avoid hidden design decisions

Do not use package helpers to hide:

- phase order
- stimulus duration
- response windows
- response keys
- marker meanings
- condition assignment
- saved data semantics

Those choices should stay in the experiment script, settings, or design files
where a researcher can inspect them before running participants.

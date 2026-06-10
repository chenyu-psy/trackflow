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
    data={"screen_name": "fixation"},
)
timeline.run(screen)
```

This is a convenience path for common screens. It should not force complex
trials into a generic screen abstraction.

For real-time monitoring during a screen, use `on_frame(ctx, data, elapsed)`.
If a participant blinks, moves gaze outside the allowed region, or presses too
early, the hook can call `ctx.break_trial(...)`. The interrupted trial is
recorded, and experiment code can choose whether to retry, skip, or continue.

## Write normal PsychoPy for complex trials

When a trial needs custom frame logic, mouse responses, multiple response
streams, custom clocks, `win.callOnFlip(...)`, or task-specific branching,
write the PsychoPy loop directly.

Return a `beh.timeline.TrialOutcome` so `trackflow` can still write raw rows,
summaries, and completion state.

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

## Keep Sends Visible

Lifecycle hooks can send EEG markers and EyeLink messages through the runtime
context. The hook chooses marker codes, message text, timing, and any saved
data fields.

```python
def mark_sample(ctx, data):
    ctx.send(21, message="sample")
    data["EEG"] = 21
    data["ET_message"] = "sample"
```

This keeps marker labels, marker codes, send timing, and saved fields visible in the
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

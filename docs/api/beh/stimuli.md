# Behavior Stimuli

Stimuli are drawables passed into `timeline.make_screen(...)`. `trackflow`
keeps the stimulus and screen layers separate: stimuli define what should be
drawn and when each drawable is visible within a screen, while screens decide
screen duration, response collection, and raw screen-row output.

```python
from trackflow import beh

timeline = beh.timeline.setup_timeline(win=win)
fix = beh.stimuli.make_fixation(
    win,
    size=0.5,
    color="#000000",
    start=0.0,
    end=0.5,
    label="fixation",
)

screen = timeline.make_screen(
    stimuli=[fix],
    duration=0.5,
    response=None,
)
```

Stimuli do not create screens, run trials, collect responses, send markers, or
write data. They are ordinary PsychoPy-compatible drawables, optionally wrapped
with screen-relative visibility timing.

## Common Parameters

These parameters describe the shared contract for built-in visual stimuli.
Not every stimulus type uses every field, but built-ins should follow the same
meanings when the field is present.

| Parameter | Meaning | Default |
| --- | --- | --- |
| `start` | Seconds after screen onset when the stimulus starts drawing. | Screen start |
| `end` | Seconds after screen onset when the stimulus stops drawing. | Screen end |
| `label` | Researcher-facing label for debugging and future data records. | Built-in type label |
| `pos` | Center position for built-in stimuli with a location. | `(0.0, 0.0)` |
| `units` | PsychoPy units for built-in stimuli with geometric size or position. | `"deg"` |

`start` and `end` are screen-relative. They do not create a new PsychoPy
clock, change the screen duration, or decide when participant responses are
accepted. Response timing belongs to the screen.

## Built-in Stimuli

### fixation

`make_fixation()` creates the current built-in fixation stimulus. It returns a
timed wrapper that can be passed directly to `timeline.make_screen(...)`.

| Parameter | Meaning | Default |
| --- | --- | --- |
| `win` | PsychoPy window used to build the fixation drawing objects. | Required |
| `size` | Full outer diameter of the fixation stimulus. | `0.5` |
| `pos` | Fixation center position. | `(0.0, 0.0)` |
| `color` | Visible fixation color. HEX values and PsychoPy-supported names are allowed. | `"#000000"` |
| `units` | PsychoPy units for fixation geometry. | `"deg"` |
| `start` | Seconds after screen onset when the fixation starts drawing. | Screen start |
| `end` | Seconds after screen onset when the fixation stops drawing. | Screen end |
| `label` | Researcher-facing label. | `"fixation"` |

The fixation helper preserves the migrated `trackNeuAct` fixation proportions.
Its transparent cross gap is not drawn as a background-colored mask, so it
remains transparent on non-matching backgrounds.

::: trackflow.beh.stimuli.make_fixation
    options:
      heading_level: 4

## Custom Stimuli

Use `wrap_stimulus()` when you already have a PsychoPy stimulus or another
object with a `draw()` method and only need `trackflow` to manage
screen-relative visibility.

```python
from psychopy import visual
from trackflow import beh

text_stim = visual.TextStim(win, text="Ready?")
ready_text = beh.stimuli.wrap_stimulus(
    text_stim,
    start=0.0,
    end=1.0,
    label="ready_text",
)
```

Custom stimuli follow the same `start`, `end`, and `label` timing contract as
built-in stimuli. The wrapped object remains a normal PsychoPy object; users
can keep editing it directly before or during their ordinary PsychoPy trial
code when the experiment design requires that flexibility.

::: trackflow.beh.stimuli.wrap_stimulus
    options:
      heading_level: 3

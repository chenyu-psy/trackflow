# Behavior Stimuli

Stimuli are timed drawables passed to `beh.screens.make_screen(...)`.
`trackflow` keeps the screen and stimulus layers separate: screens decide when
a presentation unit starts and ends, while stimuli define what should be drawn
inside that screen and when each drawable is visible.

```python
from trackflow import beh

fix = beh.stimuli.make_fixation(
    win,
    size=0.5,
    color="#000000",
    start=0.0,
    end=0.5,
    label="fixation",
)

screen = beh.screens.make_screen(
    stimuli=[fix],
    duration=0.5,
    response=None,
)
```

## Common Parameters

These parameters describe the long-term contract for built-in visual stimuli.
Not every stimulus type uses every field, but future built-ins should follow
the same meanings when the field is present.

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

## Available Stimuli

### fixation

`make_fixation()` creates the current built-in fixation stimulus. It returns a
timed wrapper that can be passed directly to `beh.screens.make_screen(...)`.

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

## Planned Stimulus Types

The `beh.stimuli` namespace is intended to grow into a small set of built-in
visual stimulus helpers. Planned types include:

- `square`
- `circle`
- `text`
- `image`

These types are not implemented yet. When added, each type should document its
specific parameters below the common parameter contract rather than expanding
the top-level behavior API.

## Function Reference

Use `wrap_stimulus()` when you already have a PsychoPy stimulus or another
object with a `draw()` method and only need `trackflow` to manage
screen-relative visibility. The reference below intentionally lists only the
current public helper functions; implementation classes are not expanded here.

::: trackflow.beh.stimuli
    options:
      members:
        - make_fixation
        - wrap_stimulus

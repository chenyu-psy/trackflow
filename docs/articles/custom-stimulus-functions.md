# Create custom stimulus functions

Use this guide when your experiment has task-specific stimuli that you want to
reuse across screens or trials.

The usual place for these functions is the generated `stimuli.py` file. Keep
these functions focused on visual construction. Put timing, response rules,
marker sends, and saved data fields in the screen or trial code where they are
easy to inspect.

## Build one reusable stimulus

A custom stimulus function can create a normal PsychoPy stimulus and wrap it
for use in `timeline.make_screen(...)`.

```python
# src/exp1/stimuli.py
from trackflow import beh


def make_word_stimulus(win, word, color="#000000"):
    """Create one centered word stimulus for a trial screen."""
    return beh.stimuli.make_text(
        win,
        text=word,
        height=0.8,
        color=color,
        units="deg",
        label="word",
    )
```

Use it from your trial code:

```python
from stimuli import make_word_stimulus


word = make_word_stimulus(timeline.win, row["word"], color=row["color"])
screen = timeline.make_screen(
    stimuli=[word],
    duration=1.0,
    response=None,
    data={"screen_name": "word"},
)
timeline.run(screen, trial_data=row)
```

This keeps the visual recipe reusable while the timing and saved fields remain
visible where the screen is created.

## Build one stimulus from several components

Some task stimuli are made from several PsychoPy objects that should be treated
as one visual item. For example, a colored box may contain one letter.
`fill_color` and `letter_color` can change from trial to trial, but the display
should still be passed to `timeline.make_screen(...)` as one stimulus.

```python
# src/exp1/stimuli.py
from psychopy import visual


class LetterBoxStim:
    """Draw one letter inside a colored rectangle."""

    def __init__(
        self,
        win,
        letter,
        fill_color="#FFFFFF",
        letter_color="#000000",
        pos=(0, 0),
    ):
        self.params = {
            "fill_color": fill_color,
            "letter_color": letter_color,
        }
        self.box = visual.Rect(
            win,
            width=2.0,
            height=2.0,
            pos=pos,
            fillColor=fill_color,
            lineColor="#000000",
            colorSpace="hex",
            units="deg",
        )
        self.letter = visual.TextStim(
            win,
            text=letter,
            pos=pos,
            height=1.0,
            color=letter_color,
            colorSpace="hex",
            units="deg",
        )

    def draw(self):
        """Draw the box first, then draw the letter on top."""
        self.box.fillColor = self.params["fill_color"]
        self.letter.color = self.params["letter_color"]
        self.box.draw()
        self.letter.draw()


def make_letter_box(
    win,
    letter,
    fill_color="#FFFFFF",
    letter_color="#000000",
    pos=(0, 0),
):
    """Create one stimulus made from a box and a letter."""
    return LetterBoxStim(
        win,
        letter=letter,
        fill_color=fill_color,
        letter_color=letter_color,
        pos=pos,
    )
```

Use it like any other stimulus:

```python
letter_box = make_letter_box(
    timeline.win,
    letter=row["letter"],
    fill_color=row["fill_color"],
    letter_color=row["letter_color"],
)

sample_screen = timeline.make_screen(
    stimuli=[letter_box],
    duration=0.5,
    response=None,
    data={"screen_name": "sample"},
)
```

If you need to change colors before running the screen, update the stimulus
params:

```python
letter_box.params["fill_color"] = row["new_fill_color"]
letter_box.params["letter_color"] = row["new_letter_color"]
```

The important part is that the stimulus has a `draw()` method. Keeping editable
values in `params` makes the object feel similar to built-in `trackflow`
stimuli. The custom stimulus still owns only the drawing recipe. The screen
owns duration, response collection, marker hooks, and saved row fields.

## Use built-in helpers inside your own functions

You do not have to call PsychoPy directly. A helper can combine built-in
`trackflow` stimuli:

```python
# src/exp1/stimuli.py
from trackflow import beh


def make_fixation_with_label(win, label_text):
    """Create a fixation display with a small condition label."""
    fixation = beh.stimuli.make_fixation(
        win,
        size=0.5,
        color="#000000",
        label="fixation",
    )
    label = beh.stimuli.make_text(
        win,
        label_text,
        pos=(0, -2.5),
        height=0.3,
        color="#000000",
        label="condition_label",
    )
    return [fixation, label]
```

This is useful when you want all screens to share the same layout.

## Keep timing decisions visible

Avoid hiding important experiment behavior inside a stimulus builder. This is
usually easier to review:

```python
sample = make_word_stimulus(timeline.win, row["word"])
screen = timeline.make_screen(
    stimuli=[sample],
    duration=0.5,
    response=None,
    data={"screen_name": "sample"},
)
```

This is harder to audit because a reader must inspect the helper to learn the
screen duration:

```python
screen = make_word_screen(timeline, row)
```

A screen-building helper can still be useful for common instruction screens or
very repetitive task screens. When you use one, name it clearly and keep
response keys, durations, marker labels, and saved fields obvious to the
researcher reviewing the experiment.

## Where to go next

- Read [Understand the Timeline](understand-timeline.md) for screen timing and
  trial grouping.
- Use the [Stimuli API](../api/beh/stimuli.md) for exact built-in stimulus
  helper details.

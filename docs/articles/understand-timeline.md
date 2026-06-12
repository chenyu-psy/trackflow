# Understand the timeline

Use this guide when you want to show screens, group screens into trials, and
run them from ordinary Python code.

A `trackflow` timeline does not own your scientific procedure. Your script
still decides the trial order, timing, responses, markers, and saved fields.
The timeline gives you a consistent way to run screens, write behavior rows,
and share runtime context with hooks.

## Create a timeline

Start with a PsychoPy window, then pass it to `setup_timeline`:

```python
from psychopy import visual
from trackflow import beh


win = visual.Window(size=(1024, 768), units="deg")
timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
)
```

When `raw_data_file` is set, the timeline saves one raw row for each completed
screen while the experiment runs. Add `summary_file` later only if your trial
uses `data_format` to create a separate trial-summary CSV.

See the [timeline API](../api/beh/timeline.md) for all setup arguments.

## Make stimuli

Stimuli are drawable objects that a screen can show. `trackflow.beh.stimuli`
has small helpers for common PsychoPy visuals:

```python
fixation = beh.stimuli.make_fixation(
    win,
    size=0.5,
    color="#000000",
)

sample = beh.stimuli.make_text(
    win,
    "BLUE",
    height=0.8,
    color="#0000FF",
)
```

You can also make images and simple shapes:

```python
cue = beh.stimuli.make_image(win, "assets/images/cue.png", size=(4, 4))
box = beh.stimuli.make_rect(win, width=3.0, height=2.0, color="#FFFFFF")
```

Stimuli decide what can be drawn. Screens decide how long the display lasts,
whether responses are collected, and what row fields are saved.

## Make a fixed-duration screen

A screen shows one or more stimuli and produces one raw behavior row when it
finishes.

```python
fixation_screen = timeline.make_screen(
    stimuli=[fixation],
    duration=0.5,
    response=None,
    data={"screen_name": "fixation"},
)
```

This screen shows the fixation for 0.5 seconds and does not collect a
participant response. The saved row includes `screen_name="fixation"` plus the
timeline-managed response fields.

## Make a response screen

For a keyboard response, give the allowed PsychoPy key names:

```python
response_screen = timeline.make_screen(
    stimuli=[sample],
    duration=2.0,
    choices=["f", "j"],
    response_start=0.2,
    data={"screen_name": "response"},
)
```

This screen accepts `f` or `j` starting 0.2 seconds after screen onset. The
screen ends after the first accepted response because `end_on_response=True`
by default. If no accepted key is pressed, the screen ends at 2.0 seconds and
the response value is `None`.

## Show more than one stimulus

Pass several stimuli to the same screen when they should be drawn together:

```python
prompt = beh.stimuli.make_text(
    win,
    "F = old     J = new",
    pos=(0, -3),
    height=0.35,
    color="#000000",
)

response_screen = timeline.make_screen(
    stimuli=[sample, prompt],
    duration=2.0,
    choices=["f", "j"],
    data={"screen_name": "response"},
)
```

Both stimuli are drawn on each frame while the screen runs.

## Time stimuli within a screen

Use `start` and `end` when a stimulus should appear only during part of a
screen. These times are relative to the screen onset.

```python
sample = beh.stimuli.make_text(
    win,
    "BLUE",
    start=0.0,
    end=0.5,
    height=0.8,
)

mask = beh.stimuli.make_text(
    win,
    "####",
    start=0.5,
    end=1.0,
    height=0.8,
)

screen = timeline.make_screen(
    stimuli=[sample, mask],
    duration=1.0,
    response=None,
    data={"screen_name": "sample_then_mask"},
)
```

`start` and `end` do not create new trial phases. They only control whether a
stimulus is drawn during the current screen. The screen duration and response
window still come from `timeline.make_screen(...)`.

## Group screens into a trial

Use `make_trial` when several screens should run as one trial-like unit:

```python
trial = timeline.make_trial(
    screens=[fixation_screen, response_screen],
)
```

The trial runs its screens in order. Each completed screen still produces one
raw row.

## Run screens or trials

Run one screen or one trial at a time:

```python
timeline.run(fixation_screen)
timeline.run(trial, trial_data={"condition": "practice", "target": "BLUE"})
```

`trial_data` is copied into every raw screen row from that run. This is a good
place for condition labels, planned stimulus names, block numbers, and other
fields shared by the screens in one trial.

Use an ordinary Python loop for planned trial rows:

```python
for row in planned_trials:
    timeline.run(trial, trial_data=row)
```

The loop stays in your experiment script so condition order, trial counts, and
retry rules remain visible.

## Where to go next

- Read [Create Custom Stimulus Functions](custom-stimulus-functions.md) when
  your visual code starts repeating.
- Read [Use Screen Hook Functions](screen-hook-functions.md) when you need to
  send markers or run code during a screen.
- Read [Understand Timeline Data](timeline-data.md) when you want to format
  trial summaries.

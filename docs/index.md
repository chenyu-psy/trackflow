<div class="trackflow-home-title">
  <div class="trackflow-home-logo">t</div>
  <h1>trackflow</h1>
</div>

<p class="trackflow-lead">
PsychoPy-first helpers for running screens, saving behavior rows, sending EEG
markers, checking eye tracking, and preparing lab copies.
</p>

## What trackflow helps with

When you write a PsychoPy experiment, you usually want the trial flow to stay
visible in your own Python code. At the same time, you may not want to rewrite
the same screen-running, data-saving, marker-sending, and eye-tracking
bookkeeping for every study.

`trackflow` gives you a `Timeline` for that repeated runtime work. You keep the
experiment design in your script; the timeline handles the parts that should be
consistent across screens and trials.

## Start with a timeline

If you already have a PsychoPy window, pass it to `trackflow` and create a
timeline:

```python
from psychopy import visual

from trackflow import beh


win = visual.Window(size=(1024, 768), units="deg")
timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
)
```

The timeline keeps the window, output files, runtime state, and hook context in
one place. Your experiment code still decides what happens next.

## Build screens and trials

Start with stimuli. Stimuli are drawable objects that screens can show:

```python
fixation = beh.stimuli.make_fixation(win, size=0.5, color="#000000")
continue_text = beh.stimuli.make_text(
    win,
    "Press Space to continue",
    pos=(0, -3),
    height=0.35,
    color="#000000",
)
```

Then make screens from those stimuli. A screen decides what is shown, how long
it can run, and which fields should be saved in that screen's behavior row:

```python
fixation_screen = timeline.make_screen(
    stimuli=[fixation],
    duration=0.5,
    data={"screen_name": "fixation"},
)

continue_screen = timeline.make_screen(
    stimuli=[continue_text],
    choices=["space"],
    data={"screen_name": "continue"},
)
```

If several screens belong together, group them into a trial and run the trial:

```python
trial = timeline.make_trial(
    screens=[fixation_screen, continue_screen],
)

timeline.run(trial, trial_data={"trial_type": "practice"})
```

`timeline.run(...)` runs one screen or one trial at a time. Each completed
screen still saves one flat behavior row.

## Add EEG and eye tracking when needed

Create a tracker and sender first, then pass them to the timeline. Later sends
will use the devices configured on that timeline.

```python
from trackflow import beh, eeg, gaze


tracker = gaze.setup_tracker(
    win=win,
    cfg=gaze.GazeConfig(),
    edf_name="S01.edf",
    monitor=monitor,
    debug=True,
)
sender = eeg.setup_port(debug=True, code={"sample": 12})

timeline = beh.timeline.setup_timeline(
    win=win,
    tracker=tracker,
    eeg=sender,
)
```

Once the devices are set up, use the timeline during the study whenever you
want to send a marker to EEG, a message to the eye tracker, or both:

```python
timeline.send(code=12)
timeline.send(message="trial 1")
timeline.send(code=12, message="trial 1")
```

`code` sends an EEG marker when an EEG sender is configured. `message` sends an
EyeLink message when a tracker is configured. Passing both sends them from the
same timeline call.

Use the runtime guides when you need to send markers at exact screen events or
check gaze during a screen.

## Keep the experiment design visible

Use `trackflow` for runtime support, not for hiding design choices. Keep these
decisions in your experiment code, settings, or design files where you can
inspect them before running participants:

- phase order
- stimulus and delay durations
- response keys and response windows
- marker codes, marker labels, and EyeLink messages
- condition assignment, balancing, and trial counts
- retry, rejection, pause, and exclusion rules
- saved behavior fields and their meanings

## Install, setup, and deploy

Use `uv` as the main project workflow:

```bash
uv add "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

`pip` also works when you are managing the Python environment another way:

```bash
pip install "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

When you want `trackflow` to create a standard project layout or a generated
experiment scaffold, use:

```bash
uv run trackflow init
uv run trackflow add-experiment exp1
```

When a PsychoPy lab computer should run the project without installing
`trackflow`, package the project:

```bash
uv run trackflow package
```

Packaging copies git-visible project files, vendors the current `trackflow`
source, applies deployment overrides only to the copied settings files, and
writes Windows launchers.

## Next steps

Use articles for practical guides, and use the API reference when you need to
look up a function, class, or method.

<div class="trackflow-link-list">
  <a href="articles/start-project-lab-copy/">Start a project and make a lab copy</a>
  <a href="articles/understand-timeline/">Understand the timeline</a>
  <a href="articles/screen-hook-functions/">Use screen hook functions</a>
  <a href="articles/timeline-data/">Understand timeline data</a>
  <a href="api/beh/timeline/">Behavior timeline API</a>
  <a href="api/gaze/">Eye tracking API</a>
  <a href="api/eeg/">EEG API</a>
</div>

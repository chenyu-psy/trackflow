# Start a project and make a lab copy

Use this guide when you are starting a new PsychoPy experiment project and
want a folder that can later be copied to a lab computer.

The workflow is:

1. Install `trackflow` in your project environment.
2. Create the shared project folders.
3. Add an experiment scaffold.
4. Run the scaffold locally.
5. Package a copy for the lab computer.

## Install trackflow

Use `uv` in the project folder:

```bash
uv add "trackflow @ git+https://github.com/chenyu-psy/trackflow.git"
```

After that, run `trackflow` commands through `uv run`:

```bash
uv run trackflow --help
```

If you activate an environment where `trackflow` is already installed, you can
run the same commands without `uv run`.

## Create the project folders

From the project root, run:

```bash
uv run trackflow init
```

This creates the standard folders used by generated experiments:

- `assets/images/` for image files
- `assets/instructions/` for instruction materials
- `data/` for local participant output
- `src/` for experiment code
- `src/utils/` for shared helper code

It also updates `.gitignore` and creates a `README.md` when the project does
not already have one.

This command only prepares the folder layout. It does not choose trial timing,
response keys, marker labels, condition assignment, or saved data fields.

## Create the experiment scaffold

For a named experiment, run:

```bash
uv run trackflow add-experiment exp1
```

This creates `src/exp1/` with plain Python files:

- `main.py` runs the session.
- `runtime.py` creates the PsychoPy window and the `trackflow` timeline.
- `settings.py` stores visible runtime settings.
- `screens.py` contains common welcome, break, pause, and end screens.
- `stimuli.py` is where you can add task-specific stimulus builders.
- `trial.py` contains a small example trial.
- `__init__.py` marks the named experiment folder as a Python package.

Use a named experiment when one project may contain several experiments, such
as `exp1`, `exp2`, and `practice`.

For a single flat experiment, omit the name:

```bash
uv run trackflow add-experiment
```

That creates the experiment files directly under `src/`.

Use either named experiments or one flat experiment. `trackflow` prevents
mixing both layouts because mixed layouts make imports and lab launchers harder
to check.

## Run the scaffold

Run a named experiment with:

```bash
uv run python src/exp1/main.py
```

The scaffold is intentionally small. Edit the generated files so the study is
easy to inspect before data collection:

- Put monitor and runtime settings in `settings.py`.
- Put reusable participant screens in `screens.py`.
- Put visual builders in `stimuli.py`.
- Put the trial flow in `trial.py`.
- Keep the session order in `main.py`.

When you add your real task, keep design choices visible in these files:
screen order, stimulus durations, response keys, marker labels, retry rules,
and saved data meanings should not be hidden in generic helpers.

## Check the packaging config

When the first experiment is added, `trackflow` creates a project-level
`packaging_config.py` if one does not already exist.

For a named experiment, it looks like this:

```python
PROJECT_NAME = "my_project"
DESTINATION = "../packaged/my_project"

SETTINGS_OVERRIDES = {}

LAUNCHERS = {
    "run_exp1.bat": {
        "settings": "src/exp1/settings.py",
        "entry_script": "src/exp1/main.py",
        "python": None,
        "settings_overrides": {},
    },
}
```

Set `DESTINATION` to the folder where the packaged project should be copied.
On a Windows lab computer, that might be a local folder or a USB drive path.

Use `SETTINGS_OVERRIDES` when the lab copy needs different runtime settings
than your development copy, such as full-screen mode or real hardware flags:

```python
SETTINGS_OVERRIDES = {
    "MONITOR.fullscr": True,
    "MONITOR.resolution": [1920, 1080],
}

LAUNCHERS = {
    "run_exp1.bat": {
        "settings": "src/exp1/settings.py",
        "entry_script": "src/exp1/main.py",
        "python": None,
        "settings_overrides": {
            "RUNTIME.realtime_tracker": True,
            "RUNTIME.realtime_eeg": True,
        },
    },
}
```

Project-level overrides are applied first. Launcher-specific overrides are
applied second, so a launcher can change one value for one lab script.

Overrides change only the copied settings file. They do not rewrite your source
experiment files. Settings files must use literal top-level dictionaries for
overridden values, such as `RUNTIME = {...}` or `MONITOR = {...}`. If a target
block or key is missing, packaging fails with an explicit error instead of
guessing.

## Package the lab copy

When the project is ready to copy, run:

```bash
uv run trackflow package
```

Packaging copies git-visible project files, vendors the current `trackflow`
source into the copied project, applies configured settings overrides to the
copy, writes `trackflow_vendored.json`, and creates Windows `.bat` launchers.
Use `.gitignore` to keep local data, generated files, and other non-deployment
files out of the lab copy.

Use a temporary destination when you want to test packaging without touching
the usual lab folder:

```bash
uv run trackflow package --destination ../packaged/test_copy
```

Use a different config file when needed:

```bash
uv run trackflow package --config packaging_config.py
```

Before running participants, open the packaged copy on the lab computer and run
the generated launcher. Check monitor settings, response keys, EEG markers,
EyeLink messages, and output files with test data before collecting real data.

## Where to go next

- Read [Understand the Timeline](understand-timeline.md) when you are ready to
  build real screens and trials.
- Use the [Behavior timeline API](../api/beh/timeline.md) when you need exact
  method arguments.

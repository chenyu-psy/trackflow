# Deployment packaging

Use `trackflow package` when a lab computer should run a project without
installing `trackflow`.

Packaging is configured at the project root in `packaging_config.py`. Experiment
settings stay focused on runtime values, while deployment choices live in one
project-level file.

## Project config

```python
PROJECT_NAME = "catload"
DESTINATION = r"D:\trackflow_lab_copies\catload"

PATHS = [
    "assets",
    "src/common",
    "src/exp1b",
]

SETTINGS_OVERRIDES = {
    "RUNTIME.run_warmup": True,
    "MONITOR.fullscr": True,
    "MONITOR.resolution": [1920, 1080],
}

LAUNCHERS = {
    "run_exp1b.bat": {
        "settings": "src/exp1b/settings.py",
        "entry_script": "src/exp1b/main.py",
        "python": None,
        "settings_overrides": {
            "RUNTIME.realtime_tracker": True,
            "RUNTIME.realtime_eeg": True,
        },
    },
}
```

Package the configured project:

```bash
trackflow package
```

Use a different config path or temporary destination when needed:

```bash
trackflow package --config packaging_config.py
trackflow package --destination D:\temporary_lab_copy
```

The config can also be run as a Python script:

```python
if __name__ == "__main__":
    from pathlib import Path
    from trackflow.packaging import package_project

    package_project(config_path=Path(__file__))
```

## Copy scope

The command copies the configured project `PATHS`, every settings file and
entry script referenced by `LAUNCHERS`, and `packaging_config.py`.

Copied files are selected from git-visible files, so `.gitignore` still controls
generated files, local data, and other files that should not be deployed.

The command also vendors the current `trackflow` source into the copied project,
writes `trackflow_vendored.json`, and creates every configured Windows `.bat`
launcher.

## Deployment overrides

Deployment overrides modify only the copied settings file. Source experiment
settings are never rewritten.

Settings files must use literal top-level dictionaries for values that should be
overridable:

```python
RUNTIME = {
    "run_warmup": False,
    "realtime_tracker": False,
    "realtime_eeg": False,
}

MONITOR = {
    "resolution": [1024, 768],
    "fullscr": False,
    "distance": 60,
    "width": 53,
}
```

Override keys use dotted paths:

```python
SETTINGS_OVERRIDES = {
    "MONITOR.fullscr": True,
}

LAUNCHERS = {
    "run_exp1b.bat": {
        "settings_overrides": {
            "RUNTIME.realtime_tracker": True,
        },
    },
}
```

Project-level overrides are applied first. Launcher-specific overrides are
applied second and take precedence for the same dotted key.

`trackflow` does not do broad keyword replacement. If a target block or key is
missing, or if the settings block is not a literal dictionary, packaging fails
with an explicit error instead of guessing.

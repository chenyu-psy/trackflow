# Deployment packaging

Use `trackflow package` when a lab computer should run one experiment without
installing `trackflow`.

Packaging is configured at the project root in `packaging_config.py`. Experiment
settings stay focused on runtime values, while deployment choices live in one
project-level file.

## Project config

```python
DESTINATION_ROOT = r"D:\trackflow_lab_copies"

SHARED_PATHS = [
    "assets",
    "src/common",
]

GLOBAL_SETTINGS_OVERRIDES = {
    "RUNTIME.run_warmup": True,
    "MONITOR.fullscr": True,
    "MONITOR.resolution": [1920, 1080],
}

EXPERIMENTS = {
    "exp1b": {
        "settings": "src/exp1b/settings.py",
        "entry_script": "src/exp1b/main.py",
        "launcher_name": "run_exp1b.bat",
        "python": None,
        "paths": ["src/exp1b"],
        "settings_overrides": {
            "RUNTIME.realtime_tracker": True,
            "RUNTIME.realtime_eeg": True,
        },
    },
}
```

Run one configured experiment by name:

```bash
trackflow package exp1b
```

Use a different config path or temporary destination when needed:

```bash
trackflow package exp1b --config packaging_config.py
trackflow package exp1b --destination D:\temporary_lab_copy
```

## Copy scope

The command copies only the selected experiment's configured `paths`, the
project-level `SHARED_PATHS`, the selected settings file, the selected entry
script, and `packaging_config.py`.

Copied files are selected from git-visible files, so `.gitignore` still controls
generated files, local data, and other files that should not be deployed.

The command also vendors the current `trackflow` source into the copied project,
writes `trackflow_vendored.json`, and creates the configured Windows `.bat`
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
GLOBAL_SETTINGS_OVERRIDES = {
    "MONITOR.fullscr": True,
}

EXPERIMENTS = {
    "exp1b": {
        "settings_overrides": {
            "RUNTIME.realtime_tracker": True,
        },
    },
}
```

Global overrides are applied first. Experiment-specific overrides are applied
second and take precedence for the same dotted key.

`trackflow` does not do broad keyword replacement. If a target block or key is
missing, or if the settings block is not a literal dictionary, packaging fails
with an explicit error instead of guessing.

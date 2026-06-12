# Changelog

Release notes are required before merging a release pull request into `main`.
The release workflow reads the section matching `project.version` in
`pyproject.toml`.

## 0.3.0

- Added `trackflow init` to create project folders, starter README content, and
  standard `.gitignore` entries for experiment projects.
- Added `trackflow add-experiment` for flat or named experiment scaffolds with
  overwrite protection and mixed-layout guards.
- Generated minimal runnable experiment files: `main.py`, `runtime.py`,
  `settings.py`, `screens.py`, `stimuli.py`, and `trial.py`.
- Created the first project-level `packaging_config.py` automatically when
  adding an experiment.
- Tightened package support to Python `>=3.10,<3.11` and added direct SciPy and
  wxPython constraints for cleaner editable installs.
- Refreshed the documentation homepage, learning articles, navigation, and
  compact API reference pages for the 0.3.0 scaffold workflow.

## 0.2.0

- Added project-level deployment packaging with `packaging_config.py`.
- Changed `trackflow package` and `package_project(...)` to package one
  configured project without an experiment argument.
- Copied git-visible project files while respecting `.gitignore`.
- Vendored the current `trackflow` source into packaged projects and generated
  configured Windows launchers for offline PsychoPy lab computers.
- Added opt-in deployment settings overrides for literal settings blocks such
  as `RUNTIME` and `MONITOR`, applied only to copied settings files.
- Removed the design-stage per-settings `PACKAGE` block workflow.

## 0.1.0

- Initial reusable runtime helpers for behavior, gaze, EEG, and sync support.

# Changelog

Release notes are required before merging a release pull request into `main`.
The release workflow reads the section matching `project.version` in
`pyproject.toml`.

## 0.3.2

- Added EyeLink host status support through
  `timeline.send_gaze(status=...)`.
- Kept EDF messages on `timeline.send_gaze(message=...)` and preserved
  `timeline.send(..., message=...)` behavior.
- Simplified `run_calibration(...)` by removing built-in instruction and
  transition pages; experiment scripts now own any calibration-related
  instruction screens.
- Updated the Behavior Timeline and Gaze API reference documentation.

## 0.3.1

- Reworked API reference pages into compact, hand-authored sections with
  cleaner task-based headings and right-side tables of contents.
- Removed duplicated generated API headings and parameter tables from the
  rendered documentation.
- Simplified API overview pages into ordinary linked text lines.
- Made Eye tracking match EEG's single-page API navigation style.
- Removed unused mkdocstrings documentation tooling from the project
  configuration.

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
- Added release-branch sync checks so `main` changes are surfaced back to
  `develop` before the next release PR.

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

## 0.1.1

- Clarified timeline data storage around one flat raw row per completed screen,
  matching the jsPsych-like `trial` to `Screen` model.
- Simplified default behavior rows to stable runtime fields:
  `screen_index`, `response_type`, `response_value`, and `rt`.
- Removed historical default rejection, interruption, marker, and message
  containers from saved rows; experiment-specific fields now stay explicit in
  user data or hooks.
- Updated behavior, gaze, EEG, and onboarding documentation for the current
  runtime APIs.
- Expanded tests for timeline row shape, response fields, interruption data,
  and summary formatting behavior.

## 0.1.0

- Initial reusable runtime helpers for behavior, gaze, EEG, and sync support.

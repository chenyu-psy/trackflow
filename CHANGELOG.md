# Changelog

Release notes are required before merging a release pull request into `main`.
The release workflow reads the section matching `project.version` in
`pyproject.toml`.

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

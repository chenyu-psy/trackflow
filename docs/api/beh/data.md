# Behavior Data Output

Behavior data helpers provide lightweight collection views for completed raw
screen rows and user-formatted summary rows.

## Overview

Timelines store one flat row per completed `Screen`, matching the jsPsych
model where each trial contributes one data row. In `trackflow`, a `Screen` is
the data-producing unit; a `Trial` only groups screens into an ordered
procedure.

Raw screen rows are the primary timeline data source and can be written to
JSONL. Summary rows are optional user-formatted rows produced by `data_format`
from the current run's screen rows, and can be written to CSV.
`DataCollection` is a small view object for filtering and converting completed
rows.

`trial_data` is input to `timeline.run(...)`; it is copied into raw screen rows
when a screen runs. `screen.data` is then merged into the row,
timeline-managed fields `screen_index`, `response_type`, `response_value`,
and `rt` are added, and lifecycle hooks can edit the row before it is stored.

```python
raw_rows = timeline.get_data(kind="raw", condition="left").to_list()
summary = timeline.get_data(kind="summary").to_pandas()
latest_trial = timeline.get_last_data(unit="trial").to_list()
```

## Row Views

::: trackflow.beh.data.DataCollection
    options:
      heading_level: 3

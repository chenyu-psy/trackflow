# Behavior Data Output

Behavior data helpers provide lightweight row views for completed raw screen
rows and trial summary rows.

## Overview

Timelines store completed rows in memory and can write raw JSONL or summary
CSV files. `DataRows` is a small view object for filtering and converting
completed rows.

`trial_data` is input to `timeline.run(...)`; it is copied into raw screen rows
when a trial runs. Raw screen rows are completed screen-level records. Summary
rows are optional trial-level records returned by `data_format`.

```python
raw_rows = timeline.get_data(kind="raw", condition="left").to_list()
summary = timeline.get_data(kind="summary").to_pandas()
latest_trial = timeline.get_last_data(unit="trial").to_list()
```

## Row Views

::: trackflow.beh.data.DataRows
    options:
      heading_level: 3

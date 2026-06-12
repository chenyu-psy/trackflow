# Behavior Data API

Reference for `trackflow.beh.data`, the lightweight view over completed
timeline rows.

## `DataCollection`

Small query object returned by `timeline.get_data(...)` and
`timeline.get_last_data(...)`.

| Method | Description |
| --- | --- |
| `filter(**fields)` | Return a new `DataCollection` containing rows where every named field matches exactly. |
| `to_list()` | Return copied rows as `list[dict]`. |
| `to_pandas()` | Convert copied rows to a pandas `DataFrame`. |

::: trackflow.beh.data.DataCollection
    options:
      heading_level: 3

```python
rows = timeline.get_data(kind="raw", screen_name="response")
response_data = rows.to_list()
response_table = rows.to_pandas()
```

`DataCollection` is a view over completed rows. It does not define the row
schema; experiment code supplies fields through `trial_data`, screen `data`,
and hook edits.

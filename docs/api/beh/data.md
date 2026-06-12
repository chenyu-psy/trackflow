# Behavior Data API

Reference for `trackflow.beh.data`, the lightweight view over completed
timeline rows.

## Completed data views

### `DataCollection`

Small query object returned by `timeline.get_data(...)` and
`timeline.get_last_data(...)`.

| Item | Description |
| --- | --- |
| Input | Iterable of row dictionaries. Each row is copied into the view. |
| Role | Lightweight query view over completed raw or summary rows. |
| Alias | `DataRows` is an alias of `DataCollection`. |

`DataCollection` does not define the row schema. Experiment code supplies
fields through `trial_data`, screen `data`, and hook edits.

## Query methods

### `filter(...)`

Return rows whose fields match all requested values exactly.

| Argument | Description |
| --- | --- |
| `**fields` | Field names and exact values to match. |
| Return | New `DataCollection` containing only matching rows. |

## Conversion methods

### `to_list(...)`

Return copied rows as a plain list of dictionaries.

| Return | Description |
| --- | --- |
| `list[dict]` | Copied rows in their current order. |

### `to_pandas(...)`

Convert rows to a pandas `DataFrame`.

| Return | Description |
| --- | --- |
| `pandas.DataFrame` | Tabular view of the copied rows. |

```python
rows = timeline.get_data(kind="raw", screen_name="response")
response_data = rows.to_list()
response_table = rows.to_pandas()
```

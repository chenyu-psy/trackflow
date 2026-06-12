# Trial Planning API

Reference for `trackflow.beh.design`, which builds explicit dictionaries for
`timeline.run(..., trial_data=row)`.

## Condition expansion

### `factor_conditions(...)`

Expand explicit factor levels into condition dictionaries.

| Item | Description |
| --- | --- |
| Input | `factors`, a dictionary mapping factor names to single values or lists/tuples of values. |
| Return | `list[dict]`, one dictionary per factor-level combination. |
| Constraint | This function expands values only; it does not choose condition levels or trial counts. |

```python
conditions = beh.design.factor_conditions({
    "condition": ["left", "right"],
    "set_size": [2, 4],
})
```

## Trial row generation

### `build_trial_rows(...)`

Repeat and label condition dictionaries as runtime trial-data rows.

| Argument | Description |
| --- | --- |
| `conditions` | Explicit condition dictionaries. |
| `repeats` | Number of repetitions per condition row. |
| `session_by`, `session_size` | Optional session grouping by field values or fixed row count. |
| `block_size` | Optional rows per block within each session. |
| `random_order`, `seed` | Optional reproducible shuffle within each session. |
| `plan_prefix` | Prefix for generated `plan_id` values. |
| Return | `list[dict]` with condition fields plus `plan_id`, `session_id`, `block_id`, `trial_id`, and `session_trial_id`. |

```python
trial_rows = beh.design.build_trial_rows(
    conditions,
    repeats=2,
    block_size=8,
    random_order=True,
    seed=1,
)
```

## Balance checks

### `check_balance(...)`

Count rows by selected fields.

| Item | Description |
| --- | --- |
| Input | `rows`, a sequence of dictionaries, and `fields`, the fields defining balance cells. |
| Return | Dictionary mapping field-value tuples to counts. |
| Use | Inspect planned or condition rows before running a task. |

```python
counts = beh.design.check_balance(trial_rows, fields=["condition", "set_size"])
```

## Retry queue

### `requeue_trials(...)`

Insert one retry row into an existing mutable trial queue.

| Argument | Description |
| --- | --- |
| `trial_queue` | Mutable list of remaining trial-data rows. Mutated in place. |
| `retry_trial` | Trial-data row to retry. Copied before insertion. |
| `placement` | `"next"`, `"random"`, or `"end"`. |
| `min_delay` | Minimum delay before a random retry placement. |
| `rng` | Optional `random.Random` instance for reproducible random insertion. |
| Return | `None`. |

```python
beh.design.requeue_trials(queue, failed_row, placement="end")
```

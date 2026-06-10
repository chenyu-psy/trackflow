# Trial Planning

Planning helpers operate on explicit dictionaries and return plain trial-data
dictionaries that can be passed to `timeline.run(..., trial_data=...)`. They do
not choose condition levels, response mappings, trial counts, or experiment
design decisions.

## Overview

Use planning helpers only after the experiment design has already been chosen.
They expand explicit conditions, repeat them, assign stable IDs, and check
balance counts.

```python
conditions = beh.design.factor_conditions({"condition": ["left", "right"]})
trial_data = beh.design.build_trial_rows(conditions, repeats=2, random_order=True, seed=1)

for row in trial_data:
    timeline.run(trial, trial_data=row)
```

The function name `build_trial_rows(...)` is retained for now, but the returned
`list[dict]` is runtime trial data, not completed raw screen rows or summary
rows.

## Conditions

::: trackflow.beh.design.factor_conditions
    options:
      heading_level: 3

## Trial Data

::: trackflow.beh.design.build_trial_rows
    options:
      heading_level: 3

## Balance Checks

::: trackflow.beh.design.check_balance
    options:
      heading_level: 3

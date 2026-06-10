# Trial Planning

Planning helpers operate on explicit dictionaries and return plain planned
rows. They do not choose condition levels, response mappings, trial counts, or
experiment design decisions.

## Overview

Use planning helpers only after the experiment design has already been chosen.
They expand explicit conditions, repeat rows, assign stable IDs, and check
balance counts.

## Conditions

::: trackflow.beh.design.factor_conditions
    options:
      heading_level: 3

## Planned Rows

::: trackflow.beh.design.build_trial_rows
    options:
      heading_level: 3

## Balance Checks

::: trackflow.beh.design.check_balance
    options:
      heading_level: 3

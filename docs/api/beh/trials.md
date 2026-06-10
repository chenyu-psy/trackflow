# Behavior Trials

Trial helpers keep trial-level procedure code explicit while letting the
timeline handle common output and recovery bookkeeping.

## Overview

A `Trial` runs a list of screens for one planned row. For more complex
procedures, write an ordinary trial-like object with `run(timeline, win, row)`
and return a `TrialOutcome`.

## Trial Object

::: trackflow.beh.trials.Trial
    options:
      heading_level: 3

## Trial Outcome

`TrialOutcome` tells the timeline whether the trial was accepted or rejected,
and carries raw screen rows plus an optional trial summary row.

::: trackflow.beh.trials.TrialOutcome
    options:
      heading_level: 3

## Hook Context

`RunContext` is passed to trial and screen hooks so hooks can access the
window, timeline state, planned row, active screen, and sync helper.

::: trackflow.beh.trials.RunContext
    options:
      heading_level: 3

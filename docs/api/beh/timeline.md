# Behavior Timeline

Timelines run screens and trials while owning behavior output bookkeeping.
They store in-memory rows, optional raw JSONL output, optional trial summary
CSV output, recovery metadata, sync helpers, and researcher safety keys.

## Overview

Use a timeline when `trackflow` should record completed screens or trials. The
timeline does not define the scientific procedure; it runs explicit `Screen`
or trial objects that the experiment script provides.

```python
from trackflow import beh

timeline = beh.timeline.setup_timeline(
    raw_data_file="data/S01_screen_data.jsonl",
)
timeline.show_screen(win, screen)
```

Global researcher keys and recovery metadata are timeline runtime
bookkeeping. They are configured through timeline setup and are not separate
Behavior API pages.

## Creating A Timeline

::: trackflow.beh.timeline.setup_timeline
    options:
      heading_level: 3

## Running Screens And Trials

Use `show_screen()` for one prepared screen. Use `run()` when the unit may be
a screen, a `Trial`, or a trial-like object that returns a `TrialOutcome`.

::: trackflow.beh.timeline.Timeline.show_screen
    options:
      heading_level: 3

::: trackflow.beh.timeline.Timeline.run
    options:
      heading_level: 3

## Reading Completed Data

`get_data()` returns filtered raw or summary rows. `get_last_data()` returns
the most recent screen, trial, block, or session.

::: trackflow.beh.timeline.Timeline.get_data
    options:
      heading_level: 3

::: trackflow.beh.timeline.Timeline.get_last_data
    options:
      heading_level: 3

# Understand timeline data

Use this guide when you want to understand what the timeline records and how to
create a trial summary.

The timeline saves data automatically when output files are configured. You do
not need to manually save after each screen. Your main job is to decide which
fields should be included in the rows.

## Know the two outputs

The timeline can write two kinds of data:

- Raw screen rows: one row for each completed screen.
- Summary rows: optional user-formatted rows created from the screens in one
  trial run.

Raw rows are the source data. Summary rows are derived from raw rows only when
you provide a `data_format` function.

For ordinary raw data saving, configure `raw_data_file` when you create the
timeline:

```python
timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
)
```

## Add fields shared by a trial

Pass `trial_data` to `timeline.run(...)` when fields should appear on every
screen row from that run.

```python
row = {
    "participant": "S01",
    "block": 1,
    "condition": "valid",
    "target_word": "BLUE",
}

timeline.run(trial, trial_data=row)
```

Each screen row from that trial inherits these fields.

## Add fields for one screen

Pass `data` when fields belong to a specific screen:

```python
fixation_screen = timeline.make_screen(
    stimuli=[fixation],
    duration=0.5,
    response=None,
    data={"screen_name": "fixation"},
)

response_screen = timeline.make_screen(
    stimuli=[probe],
    duration=2.0,
    choices=["f", "j"],
    data={"screen_name": "response"},
)
```

The raw fixation row gets `screen_name="fixation"`. The raw response row gets
`screen_name="response"`.

The timeline also adds managed fields such as `screen_index`, `response_type`,
`response_value`, and `rt`.

## Edit rows from hooks

Use hooks when a saved field depends on runtime behavior:

```python
def score_response(ctx, data):
    data["correct_key"] = ctx.trial_data["correct_key"]
    data["correct"] = data["response_value"] == data["correct_key"]


response_screen = timeline.make_screen(
    stimuli=[probe],
    duration=2.0,
    choices=["f", "j"],
    on_finish=score_response,
    data={"screen_name": "response"},
)
```

Because `on_finish` runs after response collection, the hook can use
`response_value` and `rt`.

## Skip recording for helper screens

Use `record=False` when a screen should run through the timeline but should not
be saved, such as a welcome screen or break screen:

```python
break_screen = timeline.make_text_screen(
    "Take a break.",
    choices=["space"],
    prompt_text="Press Space to continue",
    data={"screen_name": "break"},
)

timeline.run(break_screen, record=False)
```

The screen can still use the timeline window, keys, and runtime context.

## Create a trial summary

Use `data_format` when you want one summary row for a trial. The function
receives the raw screen rows from that trial run and returns a dictionary.
Set `summary_file` on the timeline when you want those summary rows written to
CSV.

```python
timeline = beh.timeline.setup_timeline(
    win=win,
    raw_data_file="data/S01_screen_data.jsonl",
    summary_file="data/S01_trial_summary.csv",
)


def summarize_trial(screen_rows):
    response_row = next(
        row for row in screen_rows
        if row["screen_name"] == "response"
    )
    return {
        "participant": response_row["participant"],
        "block": response_row["block"],
        "condition": response_row["condition"],
        "target_word": response_row["target_word"],
        "response": response_row["response_value"],
        "rt": response_row["rt"],
        "correct": response_row["correct"],
    }


trial = timeline.make_trial(
    screens=[fixation_screen, response_screen],
    data_format=summarize_trial,
)
```

`data_format` does not replace raw data saving. It creates a separate summary
row from the raw screen rows that were already produced.

## Read completed rows during a session

Use `get_data(...)` to inspect saved rows while the session is running:

```python
response_rows = timeline.get_data(
    kind="raw",
    screen_name="response",
).to_list()

summary_rows = timeline.get_data(kind="summary").to_list()
```

This is useful for debugging or for simple runtime checks. For analysis, use
the raw JSONL and summary CSV files written by the timeline.

## Where to go next

- Read [Use Screen Hook Functions](screen-hook-functions.md) for examples of
  editing rows at screen events.
- Use the [Behavior data API](../api/beh/data.md) for exact data collection
  methods.

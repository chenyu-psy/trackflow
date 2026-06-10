"""Tests for behavior screen, trial, and timeline helpers."""

import csv
import json
import tempfile
import unittest
from unittest import mock

from trackflow import beh
from trackflow.beh import keys as beh_keys
from trackflow.beh import preflight as beh_preflight
from trackflow.beh import recovery as beh_recovery
from trackflow.beh import screens as beh_screens
from trackflow.beh import timeline as beh_timeline


class FakeStim:
    """Drawable stimulus that records draw times."""

    def __init__(self, visible=True):
        """Store visibility behavior and initialize draw count."""
        self.visible = visible
        self.draw_calls = 0
        self.draw_elapsed = []

    def draw(self):
        """Record one draw call."""
        self.draw_calls += 1

    def is_visible(self, elapsed):
        """Return whether the stimulus should be visible."""
        self.draw_elapsed.append(float(elapsed))
        if callable(self.visible):
            return bool(self.visible(elapsed))
        return bool(self.visible)


class FakeWindow:
    """Minimal PsychoPy window stand-in."""

    def __init__(self):
        """Initialize flip count."""
        self.flip_calls = 0

    def flip(self):
        """Record one screen flip."""
        self.flip_calls += 1


class FakeCore:
    """PsychoPy core stand-in with deterministic time."""

    def __init__(self, times):
        """Store time values returned by ``getTime``."""
        self.times = list(times)
        self.last = 0.0

    def getTime(self):
        """Return the next scripted time value."""
        if self.times:
            self.last = float(self.times.pop(0))
        return self.last


class FakeEvent:
    """PsychoPy event stand-in for key-response tests."""

    def __init__(self, key_batches=None, mouse=None):
        """Store scripted key batches and mouse object."""
        self.key_batches = list(key_batches or [])
        self.mouse = mouse
        self.clear_calls = 0
        self.globalKeys = FakeGlobalKeys()

    def clearEvents(self, eventType=None):
        """Record event clearing."""
        self.clear_calls += 1
        self.clear_event_type = eventType

    def getKeys(self, keyList=None):
        """Return the next scripted key batch, filtered by ``keyList``."""
        if not self.key_batches:
            return []
        keys = list(self.key_batches[0])
        if not keys:
            self.key_batches.pop(0)
            return []
        if keyList is None:
            self.key_batches.pop(0)
            return keys
        allowed = set(keyList)
        matching = [key for key in keys if key in allowed]
        remaining = [key for key in keys if key not in allowed]
        if matching:
            if remaining:
                self.key_batches[0] = remaining
            else:
                self.key_batches.pop(0)
        return matching


class FakeGlobalKeys:
    """Minimal PsychoPy globalKeys stand-in."""

    def __init__(self):
        """Initialize registered shortcut records."""
        self.added = []
        self.removed = []

    def add(self, key=None, modifiers=None, func=None, name=None):
        """Store one registered global shortcut."""
        self.added.append({"key": key, "modifiers": list(modifiers or []), "func": func, "name": name})

    def remove(self, key, modifiers=None):
        """Record one removal request."""
        self.removed.append({"key": key, "modifiers": list(modifiers or [])})

class FakeShape:
    """Drawable shape used in screen tests."""

    def __init__(self, *args, **kwargs):
        """Store constructor values."""
        self.args = args
        self.kwargs = kwargs
        self.draw_calls = 0

    def draw(self):
        """Record one draw call."""
        self.draw_calls += 1


class FakeEegSender:
    """EEG sender stand-in that records sent codes."""

    def __init__(self, fail=False):
        """Store failure mode and initialize send log."""
        self.fail = fail
        self.sent = []

    def send(self, code):
        """Record a code or raise a scripted failure."""
        if self.fail:
            raise RuntimeError("port disconnected")
        self.sent.append(int(code))


class FakeGazeSender:
    """EyeLink stand-in that records message text."""

    def __init__(self):
        """Initialize message log."""
        self.messages = []

    def send_msg(self, text):
        """Record one EyeLink message."""
        self.messages.append(str(text))


class BehaviorScreenTests(unittest.TestCase):
    """Check screen runtime behavior without opening PsychoPy."""

    def test_import_exposes_screen_helpers(self):
        """The behavior package should expose screen and timeline namespaces."""
        self.assertTrue(hasattr(beh, "screens"))
        self.assertTrue(hasattr(beh, "timeline"))
        self.assertTrue(hasattr(beh.screens, "make_screen"))
        self.assertTrue(hasattr(beh.timeline, "setup_timeline"))
        self.assertTrue(hasattr(beh.screens, "Screen"))
        self.assertTrue(hasattr(beh.timeline, "Timeline"))
        self.assertFalse(hasattr(beh, "make_screen"))

    def test_make_screen_requires_an_end_condition(self):
        """Screens should not be allowed to run forever by accident."""
        with self.assertRaises(ValueError):
            beh.screens.make_screen(stimuli=[FakeStim()])

    def test_key_response_records_response_and_rt(self):
        """Key screens should append response and RT to timeline records."""
        stim = FakeStim()
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.1])
        event = FakeEvent(key_batches=[["space"]])
        screen = beh.screens.make_screen(
            stimuli=[stim],
            duration=1.0,
            response="key",
            keys=["space"],
        )
        timeline = beh.timeline.setup_timeline()

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                result = timeline.show_screen(win, screen)

        self.assertIsNone(result)
        self.assertEqual(
            timeline.records,
            [{"screen_index": 0, "response": "space", "rt": 0.1, "markers": [], "messages": []}],
        )
        self.assertEqual(event.clear_calls, 1)
        self.assertEqual(event.clear_event_type, "keyboard")
        self.assertEqual(win.flip_calls, 1)
        self.assertEqual(stim.draw_calls, 1)

    def test_end_on_response_false_waits_until_duration(self):
        """Fixed-duration screens should record only the first response."""
        stim = FakeStim()
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.2, 0.4, 0.6])
        event = FakeEvent(key_batches=[["space"], ["other"], []])
        screen = beh.screens.make_screen(
            stimuli=[stim],
            duration=0.5,
            response="key",
            keys=["space", "other"],
            end_on_response=False,
        )
        timeline = beh.timeline.setup_timeline()

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(win, screen)

        self.assertEqual(
            timeline.records,
            [{"screen_index": 0, "response": "space", "rt": 0.2, "markers": [], "messages": []}],
        )
        self.assertGreater(win.flip_calls, 1)

    def test_stimulus_timing_controls_draws(self):
        """Stimuli should draw only inside their timing windows."""
        always = beh.stimuli.wrap_stimulus(FakeStim())
        delayed = beh.stimuli.wrap_stimulus(FakeStim(), start=0.3, end=0.6)
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.2, 0.4, 0.7])
        event = FakeEvent(key_batches=[[], [], []])
        screen = beh.screens.make_screen(stimuli=[always, delayed], duration=0.5, response=None)
        timeline = beh.timeline.setup_timeline()

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(win, screen)

        self.assertEqual(always.drawable.draw_calls, 3)
        self.assertEqual(delayed.drawable.draw_calls, 1)
        self.assertEqual(
            timeline.records,
            [{"screen_index": 0, "response": None, "rt": None, "markers": [], "messages": []}],
        )

    def test_run_if_false_skips_screen_without_row(self):
        """run_if should skip presentation and data writing."""
        calls = []

        def skip_screen(ctx):
            """Skip the screen and record that the condition was checked."""
            calls.append(ctx.row["plan_id"])
            return False

        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=0.1, run_if=skip_screen)
        trial = beh.trials.Trial([screen])
        timeline = beh.timeline.setup_timeline()

        timeline.run(FakeWindow(), trial, rows=[{"plan_id": "exp_0001"}])

        self.assertEqual(calls, ["exp_0001"])
        self.assertEqual(timeline.records, [])

    def test_on_start_can_edit_data_and_current_screen(self):
        """on_start should receive data and access the current screen through ctx."""
        def prepare_screen(ctx, data):
            """Attach trial fields and shorten the current screen."""
            data["stim_file"] = ctx.row["stim_file"]
            ctx.screen.update(duration=0.2)

        screen = beh.screens.make_screen(
            stimuli=[FakeStim()],
            duration=1.0,
            response=None,
            screen_name="sample",
            on_start=prepare_screen,
        )
        trial = beh.trials.Trial([screen])
        timeline = beh.timeline.setup_timeline()
        core = FakeCore([0.0, 0.0, 0.1, 0.3])
        event = FakeEvent(key_batches=[[], []])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.run(FakeWindow(), trial, rows=[{"stim_file": "sample.png"}])

        self.assertEqual(timeline.records[0]["stim_file"], "sample.png")
        self.assertEqual(screen.duration, 0.2)

    def test_on_load_can_save_sync_records_after_first_flip(self):
        """on_load should run after the first flip and let users save sync records."""
        eeg_sender = FakeEegSender()
        gaze_sender = FakeGazeSender()

        def mark_sample(ctx, data):
            """Send and explicitly save one sample-onset sync result."""
            data["flip_count_at_marker"] = ctx.win.flip_calls
            result = ctx.sync.send(21, gaze_message="sample")
            data["markers"].extend(result.markers)
            data["messages"].extend(result.messages)

        screen = beh.screens.make_screen(
            stimuli=[FakeStim()],
            duration=0.2,
            response=None,
            screen_name="sample",
            on_load=mark_sample,
        )
        timeline = beh.timeline.setup_timeline(eeg=eeg_sender, gaze=gaze_sender)
        core = FakeCore([0.0, 0.0, 0.3])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(FakeWindow(), screen)

        row = timeline.records[0]
        self.assertEqual(row["flip_count_at_marker"], 1)
        self.assertEqual(row["markers"], [{"source": "eeg", "code": 21, "status": "sent"}])
        self.assertEqual(row["messages"], [{"source": "eyelink", "text": "sample", "status": "sent"}])
        self.assertEqual(eeg_sender.sent, [21])
        self.assertEqual(gaze_sender.messages, ["sample"])

    def test_condition_specific_code_lookup_uses_screen_data(self):
        """Hooks can choose numeric codes from ctx.sync.code and inherited data."""
        eeg_sender = FakeEegSender()
        eeg_sender.code = {"left": 41, "right": 42}

        def mark_condition(ctx, data):
            """Look up a condition-specific code before sending."""
            code = ctx.sync.code[data["condition"]]
            result = ctx.sync.send(code)
            data["markers"].extend(result.markers)

        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=0.1, response=None, on_load=mark_condition)
        trial = beh.trials.Trial([screen])
        timeline = beh.timeline.setup_timeline(eeg=eeg_sender)
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.run(FakeWindow(), trial, rows=[{"condition": "right"}])

        self.assertEqual(timeline.records[0]["markers"], [{"source": "eeg", "code": 42, "status": "sent"}])
        self.assertEqual(eeg_sender.sent, [42])

    def test_on_response_runs_while_screen_continues(self):
        """on_response should run after the first valid response without ending the screen."""
        calls = []

        def mark_response(ctx, data):
            """Record response data at the response hook."""
            calls.append((data["response"], data["rt"], ctx.win.flip_calls))
            data["response_marked"] = True

        screen = beh.screens.make_screen(
            stimuli=[FakeStim()],
            duration=0.5,
            response="key",
            keys=["space"],
            end_on_response=False,
            on_response=mark_response,
        )
        timeline = beh.timeline.setup_timeline()
        core = FakeCore([0.0, 0.0, 0.2, 0.4, 0.6])
        event = FakeEvent(key_batches=[["space"], [], []])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(FakeWindow(), screen)

        self.assertEqual(calls, [("space", 0.2, 1)])
        self.assertTrue(timeline.records[0]["response_marked"])

    def test_on_finish_can_edit_returned_row(self):
        """on_finish should update the final screen row before it is stored."""
        def finish_screen(ctx, data):
            """Add final row metadata."""
            data["finished"] = True

        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=0.1, response=None, on_finish=finish_screen)
        timeline = beh.timeline.setup_timeline()
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(FakeWindow(), screen)

        self.assertTrue(timeline.records[0]["finished"])

    def test_f10_pause_global_action_sets_state_without_participant_response(self):
        """Researcher F10 should request pause without becoming a response."""
        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=0.3, response="key", keys=["space"])
        timeline = beh.timeline.setup_timeline()
        core = FakeCore([0.0, 0.0, 0.1, 0.4])
        event = FakeEvent(key_batches=[["f10"], []])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(FakeWindow(), screen)

        row = timeline.records[0]
        self.assertTrue(timeline.state["pause_experiment"])
        self.assertEqual(row["global_key_action"], "pause_requested")
        self.assertIsNone(row["response"])

    def test_f12_quit_global_action_ends_screen_and_sets_state(self):
        """Researcher F12 should request quit and show a confirmation screen."""
        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=5.0, response=None)
        timeline = beh.timeline.setup_timeline()
        core = FakeCore([0.0, 0.0, 0.1, 0.1, 0.1, 0.2])
        event = FakeEvent(key_batches=[["f12"], ["n"]])
        win = FakeWindow()

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                with mock.patch.object(beh_timeline, "_load_psychopy_visual") as visual_loader:
                    visual_loader.return_value.TextStim = FakeShape
                    timeline.show_screen(win, screen)

        row = timeline.records[0]
        self.assertFalse(timeline.state["quit_requested"])
        self.assertFalse(timeline.state["quit_confirmed"])
        self.assertEqual(row["global_key_action"], "quit_requested")
        self.assertEqual(timeline.records[1]["screen_name"], "quit_confirmation")
        self.assertEqual(timeline.records[1]["response"], "n")

    def test_global_key_conflict_is_checked_before_screen_runs(self):
        """Participant responses should not reuse researcher fallback keys."""
        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=1.0, response="key", keys=["f10"])
        timeline = beh.timeline.setup_timeline()

        with self.assertRaises(ValueError):
            timeline.show_screen(FakeWindow(), screen)

    def test_modified_global_shortcuts_register_with_psychopy_event(self):
        """Ctrl/command shortcuts should use PsychoPy globalKeys callbacks."""
        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=0.1, response=None)
        timeline = beh.timeline.setup_timeline()
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(FakeWindow(), screen)

        registered = {(item["key"], tuple(item["modifiers"])) for item in event.globalKeys.added}
        self.assertIn(("p", ("command",)), registered)
        self.assertIn(("p", ("ctrl",)), registered)
        self.assertIn(("q", ("command",)), registered)
        self.assertIn(("q", ("ctrl",)), registered)

    def test_custom_global_action_can_show_followup_screen(self):
        """Action screens should run after the interrupted screen and save once."""
        followup = beh.screens.make_screen(
            stimuli=[FakeStim()],
            duration=0.1,
            response=None,
            screen_name="researcher_pause",
        )
        action = beh_keys.GlobalKeyAction(
            name="custom_pause",
            keys=["F10"],
            set_state={"pause_experiment": True},
            end_screen=True,
            screen=followup,
        )
        screen = beh.screens.make_screen(stimuli=[FakeStim()], duration=5.0, response=None, screen_name="task")
        timeline = beh.timeline.setup_timeline(global_actions=[action])
        core = FakeCore([0.0, 0.0, 0.1, 0.1, 0.1, 0.3])
        event = FakeEvent(key_batches=[["f10"], []])

        with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                timeline.show_screen(FakeWindow(), screen)

        self.assertEqual([row["screen_name"] for row in timeline.records], ["task", "researcher_pause"])
        self.assertEqual(timeline.records[0]["global_key_action"], "custom_pause")

    def test_preflight_checks_only_enabled_subsystems(self):
        """Preflight should skip disabled hardware checks."""
        result = beh_preflight.check_preflight(require_psychopy=False)

        self.assertTrue(result.passed)
        self.assertEqual(result.issues, [])

    def test_preflight_reports_enabled_eeg_problem(self):
        """Enabled EEG sender must provide the marker send method."""
        result = beh_preflight.check_preflight(require_psychopy=False, eeg=object())

        self.assertFalse(result.passed)
        self.assertIn("EEG sender must provide send(code).", result.issues)

    def test_get_last_data_supports_trial_unit(self):
        """The last trial query should return all rows from the latest trial."""
        timeline = beh.timeline.setup_timeline()
        timeline.records.extend(
            [
                {"trial_id": 1, "screen_index": 0},
                {"trial_id": 1, "screen_index": 1},
                {"trial_id": 2, "screen_index": 0},
                {"trial_id": 2, "screen_index": 1},
            ]
        )

        rows = timeline.get_last_data(unit="trial").to_list()

        self.assertEqual(rows, [{"trial_id": 2, "screen_index": 0}, {"trial_id": 2, "screen_index": 1}])

    def test_button_responses_are_deferred_in_010(self):
        """Built-in button response helpers are not part of 0.1.0."""
        with self.assertRaises(ValueError):
            beh.screens.make_screen(
                stimuli=[FakeStim()],
                duration=1.0,
                response="button",
                choices=["Yes", "No"],
            )

    def test_build_trial_rows_returns_plain_runtime_rows(self):
        """Planner should return list rows with stable IDs and explicit fields."""
        conditions = beh.design.factor_conditions({"task": ["color", "shape"], "set_size": [2, 4]})
        rows = beh.design.build_trial_rows(
            conditions,
            repeats=1,
            session_by="task",
            block_size=1,
            random_order=True,
            seed=3,
            plan_prefix="exp",
        )

        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["plan_id"], "exp_0001")
        self.assertIn("session_id", rows[0])
        self.assertIn("block_id", rows[0])
        self.assertIn("trial_id", rows[0])

    def test_meta_state_tracks_remaining_rows_by_accepted_plan_id(self):
        """Recovery should filter only rows whose plan IDs were accepted."""
        rows = [{"plan_id": "exp_0001"}, {"plan_id": "exp_0002"}]
        state = beh_recovery.make_meta_state(session_info={"subject": "S01"}, planned_rows=rows)

        beh_recovery.mark_plan_completed(state, "exp_0001")

        self.assertEqual(beh_recovery.remaining_plan_rows(state), [{"plan_id": "exp_0002"}])

    def test_timeline_writes_raw_summary_and_completion_state(self):
        """Accepted trials should write raw JSONL, summary CSV, and meta completion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = f"{tmpdir}/raw.jsonl"
            summary_path = f"{tmpdir}/summary.csv"
            meta_path = f"{tmpdir}/meta.json"
            meta_state = beh_recovery.make_meta_state(planned_rows=[{"plan_id": "exp_0001"}])
            screen = beh.screens.make_screen(
                stimuli=[FakeStim()],
                duration=1.0,
                response="key",
                keys=["space"],
                screen_name="probe",
            )
            trial = beh.trials.Trial(
                [screen],
                data_format=lambda data: {
                    "plan_id": data[0]["plan_id"],
                    "response": data[0]["response"],
                },
            )
            timeline = beh.timeline.setup_timeline(
                raw_data_file=raw_path,
                summary_file=summary_path,
                meta_file=meta_path,
                meta_state=meta_state,
            )
            core = FakeCore([0.0, 0.0, 0.1])
            event = FakeEvent(key_batches=[["space"]])

            with mock.patch.object(beh_screens, "_load_psychopy_core", return_value=core):
                with mock.patch.object(beh_screens, "_load_psychopy_event", return_value=event):
                    timeline.run(FakeWindow(), trial, rows=[{"plan_id": "exp_0001", "trial_id": 1}])

            with open(raw_path, "r", encoding="utf-8") as f:
                raw_rows = [json.loads(line) for line in f]
            with open(summary_path, "r", encoding="utf-8", newline="") as f:
                summary_rows = list(csv.DictReader(f))
            loaded_meta = beh_recovery.load_meta_state(meta_path)

            self.assertEqual(raw_rows[0]["screen_name"], "probe")
            self.assertEqual(summary_rows[0]["plan_id"], "exp_0001")
            self.assertEqual(loaded_meta["completed_plan_ids"], ["exp_0001"])

    def test_rejected_trial_is_written_and_retried_in_same_block(self):
        """Rejected rows should not complete until the retry is accepted."""
        class FakeTrialRunner:
            """Trial-like object that rejects a row once, then accepts it."""

            def __init__(self):
                """Initialize per-plan call counts."""
                self.calls = {}

            def run(self, timeline, win, row):
                """Return a rejected outcome first and accepted outcome later."""
                plan_id = row["plan_id"]
                count = self.calls.get(plan_id, 0)
                self.calls[plan_id] = count + 1
                if plan_id == "exp_0001" and count == 0:
                    return beh.trials.TrialOutcome(
                        status="rejected",
                        reason="eye_movement",
                        row={"plan_id": plan_id},
                        screen_rows=[{"plan_id": plan_id, "block_id": row["block_id"]}],
                    )
                return beh.trials.TrialOutcome(
                    status="accepted",
                    reason="no",
                    row={"plan_id": plan_id},
                    screen_rows=[{"plan_id": plan_id, "block_id": row["block_id"]}],
                )

        rows = [
            {"plan_id": "exp_0001", "block_id": 1},
            {"plan_id": "exp_0002", "block_id": 1},
        ]
        state = beh_recovery.make_meta_state(planned_rows=rows)
        timeline = beh.timeline.setup_timeline(meta_state=state, seed=1)

        timeline.run(FakeWindow(), FakeTrialRunner(), rows=rows, replace_on_reject=True)

        statuses = [row["trial_status"] for row in timeline.summary_records]
        self.assertIn("rejected", statuses)
        self.assertEqual(set(state["completed_plan_ids"]), {"exp_0001", "exp_0002"})


if __name__ == "__main__":
    unittest.main()

"""Tests for behavior screen, trial, and timeline helpers."""

import csv
import json
import tempfile
import unittest
from unittest import mock

import trackflow
from trackflow import beh
from trackflow.beh import keys as beh_keys
from trackflow.beh import preflight as beh_preflight
from trackflow.beh import recovery as beh_recovery
from trackflow.beh import timeline as beh_timeline
from trackflow.beh.timeline import core as beh_timeline_core
from trackflow.beh.timeline import screen as beh_timeline_screen


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
        """The behavior package should expose timeline as the only runtime namespace."""
        self.assertTrue(hasattr(beh, "timeline"))
        self.assertTrue(hasattr(beh.timeline, "setup_timeline"))
        self.assertTrue(hasattr(beh.timeline, "Screen"))
        self.assertTrue(hasattr(beh.timeline, "RunContext"))
        self.assertTrue(hasattr(beh.timeline, "TrialOutcome"))
        self.assertTrue(hasattr(beh.timeline, "Timeline"))
        self.assertFalse(hasattr(trackflow, "sync"))
        self.assertFalse(hasattr(beh, "screens"))
        self.assertFalse(hasattr(beh, "trials"))
        self.assertFalse(hasattr(beh, "make_screen"))

    def test_screen_requires_an_end_condition(self):
        """Screens should not be allowed to run forever by accident."""
        with self.assertRaises(ValueError):
            beh_timeline.Screen(stimuli=[FakeStim()])

    def test_key_response_records_response_and_rt(self):
        """Key screens should append response and RT to timeline records."""
        stim = FakeStim()
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.1])
        event = FakeEvent(key_batches=[["space"]])
        screen = beh_timeline.Screen(
            stimuli=[stim],
            duration=1.0,
            response="key",
            choices=["space"],
        )
        timeline = beh.timeline.setup_timeline(win=win)

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                result = timeline.run(screen)

        self.assertIsNone(result)
        self.assertEqual(
            timeline.records,
            [
                {
                    "screen_index": 0,
                    "response": "space",
                    "rt": 0.1,
                    "markers": [],
                    "messages": [],
                    "trial_status": "accepted",
                    "rejection": "no",
                }
            ],
        )
        self.assertEqual(event.clear_calls, 1)
        self.assertEqual(event.clear_event_type, "keyboard")
        self.assertEqual(win.flip_calls, 1)
        self.assertEqual(stim.draw_calls, 1)

    def test_key_choices_filter_allowed_responses(self):
        """Keyboard choices should ignore queued keys outside the allowed list."""
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.1, 0.2])
        event = FakeEvent(key_batches=[["escape", "space"]])
        screen = beh_timeline.Screen(
            stimuli=[FakeStim()],
            duration=1.0,
            response="key",
            choices=["space"],
        )
        timeline = beh.timeline.setup_timeline(win=win)

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(timeline.records[0]["response"], "space")
        self.assertEqual(timeline.records[0]["rt"], 0.1)

    def test_key_response_without_choices_waits_until_duration(self):
        """choices=None should accept no participant keys and wait for duration."""
        stim = FakeStim()
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.1, 0.4])
        event = FakeEvent(key_batches=[["space"], ["other"]])
        screen = beh_timeline.Screen(
            stimuli=[stim],
            duration=0.3,
            response="key",
            choices=None,
        )
        timeline = beh.timeline.setup_timeline(win=win)

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertIsNone(timeline.records[0]["response"])
        self.assertIsNone(timeline.records[0]["rt"])
        self.assertNotIn("pause_experiment", timeline.state)
        self.assertEqual(win.flip_calls, 2)
        self.assertEqual(stim.draw_calls, 2)

    def test_explicit_no_response_mode_waits_until_duration(self):
        """response=None should remain valid for explicit no-response screens."""
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.1, 0.4])
        event = FakeEvent(key_batches=[["space"], ["other"]])
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.3, response=None)
        timeline = beh.timeline.setup_timeline(win=win)

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertIsNone(timeline.records[0]["response"])
        self.assertIsNone(timeline.records[0]["rt"])
        self.assertEqual(win.flip_calls, 2)

    def test_key_response_without_duration_requires_choices(self):
        """A no-duration key screen needs choices so a participant response can end it."""
        with self.assertRaisesRegex(ValueError, "choices is None"):
            beh_timeline.Screen(stimuli=[FakeStim()], duration=None, response="key", choices=None)

    def test_end_on_response_false_waits_until_duration(self):
        """Fixed-duration screens should record only the first response."""
        stim = FakeStim()
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.2, 0.4, 0.6])
        event = FakeEvent(key_batches=[["space"], ["other"], []])
        screen = beh_timeline.Screen(
            stimuli=[stim],
            duration=0.5,
            response="key",
            choices=["space", "other"],
            end_on_response=False,
        )
        timeline = beh.timeline.setup_timeline(win=win)

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(
            timeline.records,
            [
                {
                    "screen_index": 0,
                    "response": "space",
                    "rt": 0.2,
                    "markers": [],
                    "messages": [],
                    "trial_status": "accepted",
                    "rejection": "no",
                }
            ],
        )
        self.assertGreater(win.flip_calls, 1)

    def test_stimulus_timing_controls_draws(self):
        """Stimuli should draw only inside their timing windows."""
        always = beh.stimuli.wrap_stimulus(FakeStim())
        delayed = beh.stimuli.wrap_stimulus(FakeStim(), start=0.3, end=0.6)
        win = FakeWindow()
        core = FakeCore([0.0, 0.0, 0.2, 0.4, 0.7])
        event = FakeEvent(key_batches=[[], [], []])
        screen = beh_timeline.Screen(stimuli=[always, delayed], duration=0.5)
        timeline = beh.timeline.setup_timeline(win=win)

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(always.drawable.draw_calls, 3)
        self.assertEqual(delayed.drawable.draw_calls, 1)
        self.assertEqual(
            timeline.records,
            [
                {
                    "screen_index": 0,
                    "response": None,
                    "rt": None,
                    "markers": [],
                    "messages": [],
                    "trial_status": "accepted",
                    "rejection": "no",
                }
            ],
        )

    def test_trial_run_if_false_skips_trial_without_row(self):
        """trial run_if should skip presentation and raw data writing."""
        calls = []

        def skip_trial(ctx):
            """Skip the trial and record that the condition was checked."""
            calls.append(ctx.trial_data["plan_id"])
            return False

        state = beh_recovery.make_meta_state(planned_rows=[{"plan_id": "exp_0001"}])
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1)
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        timeline.meta_state = state
        trial = timeline.make_trial(screens=[screen], run_if=skip_trial)

        result = timeline.run(trial, trial_data={"plan_id": "exp_0001"}, return_status=True)

        self.assertTrue(result)
        self.assertEqual(calls, ["exp_0001"])
        self.assertEqual(timeline.records, [])
        self.assertEqual(state["completed_plan_ids"], ["exp_0001"])

    def test_on_start_can_edit_data_and_current_screen(self):
        """on_start should receive data and access the current screen through ctx."""
        def prepare_screen(ctx, data):
            """Attach trial fields and shorten the current screen."""
            data["stim_file"] = ctx.trial_data["stim_file"]
            ctx.screen.update(duration=0.2)

        screen = beh_timeline.Screen(
            stimuli=[FakeStim()],
            duration=1.0,
            data={"screen_name": "sample"},
            on_start=prepare_screen,
        )
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        trial = timeline.make_trial(screens=[screen])
        core = FakeCore([0.0, 0.0, 0.1, 0.3])
        event = FakeEvent(key_batches=[[], []])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(trial, trial_data={"stim_file": "sample.png"})

        self.assertEqual(timeline.records[0]["stim_file"], "sample.png")
        self.assertEqual(screen.duration, 0.2)

    def test_on_load_can_send_after_first_flip_without_mutating_row(self):
        """on_load should send after the first flip without saving records."""
        eeg_sender = FakeEegSender()
        gaze_sender = FakeGazeSender()

        def mark_sample(ctx, data):
            """Send one sample-onset event."""
            data["flip_count_at_marker"] = ctx.win.flip_calls
            ctx.send(21, message="sample")

        screen = beh_timeline.Screen(
            stimuli=[FakeStim()],
            duration=0.2,
            data={"screen_name": "sample"},
            on_load=mark_sample,
        )
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), eeg=eeg_sender, gaze=gaze_sender)
        core = FakeCore([0.0, 0.0, 0.3])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        row = timeline.records[0]
        self.assertEqual(row["flip_count_at_marker"], 1)
        self.assertEqual(row["markers"], [])
        self.assertEqual(row["messages"], [])
        self.assertEqual(eeg_sender.sent, [21])
        self.assertEqual(gaze_sender.messages, ["sample"])

    def test_condition_specific_code_lookup_uses_screen_data(self):
        """Hooks can choose numeric codes from ctx.code and inherited data."""
        eeg_sender = FakeEegSender()
        eeg_sender.code = {"left": 41, "right": 42}

        def mark_condition(ctx, data):
            """Look up a condition-specific code before sending."""
            code = ctx.code[data["condition"]]
            ctx.send(code)
            data["EEG"] = code

        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1, on_load=mark_condition)
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), eeg=eeg_sender)
        trial = timeline.make_trial(screens=[screen])
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(trial, trial_data={"condition": "right"})

        self.assertEqual(timeline.records[0]["markers"], [])
        self.assertEqual(timeline.records[0]["EEG"], 42)
        self.assertEqual(eeg_sender.sent, [42])

    def test_send_eeg_sends_marker_only(self):
        """ctx.send_eeg should send EEG without mutating row records."""
        eeg_sender = FakeEegSender()

        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1, on_load=lambda ctx: ctx.send_eeg(21))
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), eeg=eeg_sender)
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(timeline.records[0]["markers"], [])
        self.assertEqual(timeline.records[0]["messages"], [])
        self.assertEqual(eeg_sender.sent, [21])

    def test_send_gaze_sends_message_only(self):
        """ctx.send_gaze should send EyeLink text without mutating row records."""
        gaze_sender = FakeGazeSender()

        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1, on_load=lambda ctx: ctx.send_gaze("sample"))
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), gaze=gaze_sender)
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(timeline.records[0]["markers"], [])
        self.assertEqual(timeline.records[0]["messages"], [])
        self.assertEqual(gaze_sender.messages, ["sample"])

    def test_send_failure_sets_pause_state_without_row_record(self):
        """Failed sends should set pause state without adding row records."""
        eeg_sender = FakeEegSender(fail=True)

        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1, on_load=lambda ctx: ctx.send(21))
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), eeg=eeg_sender)
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(timeline.records[0]["markers"], [])
        self.assertTrue(timeline.state["pause_experiment"])
        self.assertIn("21", timeline.state["sync_error"])

    def test_timeline_send_works_outside_run_without_creating_rows(self):
        """timeline.send should support trial-outside sends without rows."""
        eeg_sender = FakeEegSender()
        gaze_sender = FakeGazeSender()
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), eeg=eeg_sender, gaze=gaze_sender)

        result = timeline.send(99, message="block_start")

        self.assertIsNone(result)
        self.assertEqual(timeline.records, [])
        self.assertEqual(eeg_sender.sent, [99])
        self.assertEqual(gaze_sender.messages, ["block_start"])

    def test_send_without_configured_devices_leaves_row_empty(self):
        """ctx.send should not add records when no sender is configured."""
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1, on_load=lambda ctx: ctx.send(21, message="sample"))
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(timeline.records[0]["markers"], [])
        self.assertEqual(timeline.records[0]["messages"], [])
        self.assertEqual(timeline.state, {})

    def test_on_finish_can_read_final_response_fields(self):
        """on_finish should see response fields after built-in key collection."""
        calls = []

        def mark_response(ctx, data):
            """Record response data at the finish hook."""
            calls.append((data["response"], data["rt"], ctx.win.flip_calls))
            data["response_marked"] = True

        screen = beh_timeline.Screen(
            stimuli=[FakeStim()],
            duration=0.5,
            response="key",
            choices=["space"],
            end_on_response=False,
            on_finish=mark_response,
        )
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        core = FakeCore([0.0, 0.0, 0.2, 0.4, 0.6])
        event = FakeEvent(key_batches=[["space"], [], []])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(calls, [("space", 0.2, 2)])
        self.assertTrue(timeline.records[0]["response_marked"])

    def test_on_finish_can_edit_returned_row(self):
        """on_finish should update the final screen row before it is stored."""
        def finish_screen(ctx, data):
            """Add final row metadata."""
            data["finished"] = True

        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1, on_finish=finish_screen)
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertTrue(timeline.records[0]["finished"])

    def test_timeline_screen_factories_do_not_run_units(self):
        """Timeline factories should create screens without writing records."""
        timeline = beh.timeline.setup_timeline(win=FakeWindow())

        with mock.patch.object(beh_timeline_core, "_load_psychopy_visual") as visual_loader:
            visual_loader.return_value.TextStim = FakeShape
            visual_loader.return_value.ImageStim = FakeShape
            text_screen = timeline.make_text_screen("Ready", duration=0.1)
            image_screen = timeline.make_image_screen("sample.png", duration=0.1)

        self.assertIsInstance(text_screen, beh_timeline.Screen)
        self.assertIsInstance(image_screen, beh_timeline.Screen)
        self.assertEqual(text_screen.data["screen_name"], "text")
        self.assertEqual(image_screen.data["screen_name"], "image")
        self.assertEqual(len(text_screen.stimuli), 1)
        self.assertEqual(len(image_screen.stimuli), 1)
        self.assertEqual(timeline.records, [])

    def test_text_image_helpers_forward_screen_and_stimulus_kwargs(self):
        """Text/image helpers should delegate screen behavior to make_screen."""
        calls = []

        def mark_frame(ctx, data, elapsed):
            """Record that the forwarded frame hook ran."""
            calls.append(elapsed)

        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        with mock.patch.object(beh_timeline_core, "_load_psychopy_visual") as visual_loader:
            visual_loader.return_value.TextStim = FakeShape
            visual_loader.return_value.ImageStim = FakeShape
            text_screen = timeline.make_text_screen(
                "Ready",
                duration=0.5,
                choices=["space"],
                response_start=0.2,
                end_on_response=False,
                clear_events=False,
                data={"phase": "instruction"},
                on_frame=mark_frame,
                text_kwargs={"height": 0.8, "color": "white"},
            )
            image_screen = timeline.make_image_screen(
                "instruction.png",
                duration=0.5,
                image_kwargs={"size": (10, 6)},
            )

        self.assertEqual(text_screen.choices, ["space"])
        self.assertEqual(text_screen.response_start, 0.2)
        self.assertFalse(text_screen.end_on_response)
        self.assertFalse(text_screen.clear_events)
        self.assertEqual(text_screen.data["screen_name"], "text")
        self.assertEqual(text_screen.data["phase"], "instruction")
        self.assertIs(text_screen.on_frame, mark_frame)
        self.assertEqual(text_screen.stimuli[0].drawable.kwargs["text"], "Ready")
        self.assertEqual(text_screen.stimuli[0].drawable.kwargs["height"], 0.8)
        self.assertEqual(text_screen.stimuli[0].drawable.kwargs["color"], "white")
        self.assertEqual(image_screen.stimuli[0].drawable.kwargs["image"], "instruction.png")
        self.assertEqual(image_screen.stimuli[0].drawable.kwargs["size"], (10, 6))

    def test_text_image_helpers_add_optional_prompt(self):
        """Prompt text should add one bottom prompt stimulus only when requested."""
        timeline = beh.timeline.setup_timeline(win=FakeWindow())

        with mock.patch.object(beh_timeline_core, "_load_psychopy_visual") as visual_loader:
            visual_loader.return_value.TextStim = FakeShape
            visual_loader.return_value.ImageStim = FakeShape
            text_screen = timeline.make_text_screen(
                "Ready",
                duration=0.1,
                prompt_text="Press Space to continue",
                prompt_kwargs={"pos": (0, -0.7), "height": 0.05},
            )
            image_screen = timeline.make_image_screen(
                "instruction.png",
                duration=0.1,
                prompt_text="Press Space to continue",
            )

        self.assertEqual(len(text_screen.stimuli), 2)
        self.assertEqual(text_screen.stimuli[1].label, "prompt")
        self.assertEqual(text_screen.stimuli[1].drawable.kwargs["text"], "Press Space to continue")
        self.assertEqual(text_screen.stimuli[1].drawable.kwargs["pos"], (0, -0.7))
        self.assertEqual(text_screen.stimuli[1].drawable.kwargs["height"], 0.05)
        self.assertEqual(len(image_screen.stimuli), 2)
        self.assertEqual(image_screen.stimuli[1].drawable.kwargs["units"], "norm")
        self.assertEqual(image_screen.stimuli[1].drawable.kwargs["pos"], (0, -0.85))

    def test_text_image_helpers_require_end_condition(self):
        """Instruction wrappers should preserve make_screen end-condition validation."""
        timeline = beh.timeline.setup_timeline(win=FakeWindow())

        with mock.patch.object(beh_timeline_core, "_load_psychopy_visual") as visual_loader:
            visual_loader.return_value.TextStim = FakeShape
            visual_loader.return_value.ImageStim = FakeShape
            with self.assertRaisesRegex(ValueError, "choices is None"):
                timeline.make_text_screen("Ready")
            with self.assertRaisesRegex(ValueError, "choices is None"):
                timeline.make_image_screen("instruction.png")

    def test_trial_data_dict_is_inherited_by_screen_rows(self):
        """trial_data should run once for one dictionary."""
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        screen = timeline.make_screen(stimuli=[FakeStim()], duration=0.1, data={"screen_name": "task"})
        trial = timeline.make_trial(screens=[screen])
        core = FakeCore([0.0, 0.0, 0.2, 0.2, 0.2, 0.4, 0.4, 0.4, 0.6])
        event = FakeEvent(key_batches=[[], [], []])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(trial, trial_data={"condition": "practice"})
                for row in [{"condition": "left"}, {"condition": "right"}]:
                    timeline.run(trial, trial_data=row)

        self.assertEqual([row["condition"] for row in timeline.records], ["practice", "left", "right"])
        self.assertEqual([row["screen_index"] for row in timeline.records], [0, 0, 0])

    def test_timeline_run_rejects_trial_data_lists(self):
        """Multiple planned rows should be run with an explicit user loop."""
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        screen = timeline.make_screen(stimuli=[FakeStim()], duration=0.1)
        trial = timeline.make_trial(screens=[screen])

        with self.assertRaisesRegex(TypeError, "Loop over planned trial-data rows explicitly"):
            timeline.run(trial, trial_data=[{"condition": "left"}])

    def test_timeline_run_record_false_uses_context_without_saving_rows(self):
        """record=False should run through the timeline without storing output rows."""
        calls = []

        def mark_break(ctx, data):
            """Record that the screen had timeline context."""
            calls.append((ctx.win, ctx.timeline, data["screen_name"]))
            data["break_seen"] = True

        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        screen = timeline.make_screen(
            stimuli=[FakeStim()],
            duration=0.1,
            data={"screen_name": "break"},
            on_load=mark_break,
        )
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                result = timeline.run(screen, record=False, return_status=True)

        self.assertTrue(result)
        self.assertEqual(calls, [(timeline.win, timeline, "break")])
        self.assertEqual(timeline.records, [])
        self.assertEqual(timeline.summary_records, [])

    def test_on_frame_can_mutate_screen_row(self):
        """on_frame should run inside the screen loop with elapsed time."""
        calls = []

        def mark_frame(ctx, data, elapsed):
            """Store frame-level information in the current row."""
            calls.append((ctx.timeline, elapsed))
            data["frame_checked"] = True

        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        screen = timeline.make_screen(
            stimuli=[FakeStim()],
            duration=0.1,
            on_frame=mark_frame,
        )
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        self.assertEqual(calls, [(timeline, 0.0)])
        self.assertTrue(timeline.records[0]["frame_checked"])

    def test_break_trial_interrupts_current_trial_and_runs_feedback_screen(self):
        """ctx.break_trial should stop later screens and show unrecorded feedback."""
        state = beh_recovery.make_meta_state(planned_rows=[{"plan_id": "exp_0001"}])
        feedback_stim = FakeStim()
        later_stim = FakeStim()

        def interrupt_trial(ctx, data, elapsed):
            """Interrupt the trial with additional data."""
            ctx.break_trial(
                reason="eye_movement",
                screen=feedback_screen,
                data={"eye_x": 12.5, "eye_y": -3.0},
            )

        timeline = beh.timeline.setup_timeline(win=FakeWindow(), meta_state=state)
        interrupting_screen = timeline.make_screen(
            stimuli=[FakeStim()],
            duration=1.0,
            data={"screen_name": "sample"},
            on_frame=interrupt_trial,
        )
        feedback_screen = timeline.make_screen(
            stimuli=[feedback_stim],
            duration=0.1,
            data={"screen_name": "eye_feedback"},
        )
        later_screen = timeline.make_screen(
            stimuli=[later_stim],
            duration=0.1,
            data={"screen_name": "response"},
        )
        trial = timeline.make_trial(screens=[interrupting_screen, later_screen])
        core = FakeCore([0.0, 0.0, 0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[], []])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                result = timeline.run(
                    trial,
                    trial_data={"plan_id": "exp_0001"},
                    return_status=True,
                )

        self.assertFalse(result)
        self.assertEqual(len(timeline.records), 1)
        row = timeline.records[0]
        self.assertEqual(row["screen_name"], "sample")
        self.assertEqual(row["trial_status"], "interrupted")
        self.assertEqual(row["interruption"], "eye_movement")
        self.assertEqual(row["rejection"], "no")
        self.assertEqual(row["eye_x"], 12.5)
        self.assertEqual(row["eye_y"], -3.0)
        self.assertEqual(state["completed_plan_ids"], [])
        self.assertEqual(feedback_stim.draw_calls, 1)
        self.assertEqual(later_stim.draw_calls, 0)

    def test_timeline_run_rejects_unit_sequences(self):
        """Multiple units should be run with explicit calls."""
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        first = timeline.make_screen(stimuli=[FakeStim()], duration=0.1, data={"screen_name": "first"})
        second = timeline.make_screen(stimuli=[FakeStim()], duration=0.1, data={"screen_name": "second"})
        trial = timeline.make_trial(screens=[second])

        with self.assertRaisesRegex(TypeError, "Loop over units explicitly"):
            timeline.run([first, trial])

    def test_f10_pause_global_action_sets_state_without_participant_response(self):
        """Researcher F10 should request pause without becoming a response."""
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.3, response="key", choices=["space"])
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        core = FakeCore([0.0, 0.0, 0.1, 0.4])
        event = FakeEvent(key_batches=[["f10"], []])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        row = timeline.records[0]
        self.assertTrue(timeline.state["pause_experiment"])
        self.assertEqual(row["global_key_action"], "pause_requested")
        self.assertIsNone(row["response"])

    def test_f12_quit_global_action_ends_screen_and_sets_state(self):
        """Researcher F12 should request quit and show a confirmation screen."""
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=5.0)
        win = FakeWindow()
        timeline = beh.timeline.setup_timeline(win=win)
        core = FakeCore([0.0, 0.0, 0.1, 0.1, 0.1, 0.2])
        event = FakeEvent(key_batches=[["f12"], ["n"]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                with mock.patch.object(beh_timeline_core, "_load_psychopy_visual") as visual_loader:
                    visual_loader.return_value.TextStim = FakeShape
                    timeline.run(screen)

        row = timeline.records[0]
        self.assertFalse(timeline.state["quit_requested"])
        self.assertFalse(timeline.state["quit_confirmed"])
        self.assertEqual(row["global_key_action"], "quit_requested")
        self.assertEqual(timeline.records[1]["screen_name"], "quit_confirmation")
        self.assertEqual(timeline.records[1]["response"], "n")

    def test_global_key_conflict_is_checked_before_screen_runs(self):
        """Participant responses should not reuse researcher fallback keys."""
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=1.0, response="key", choices=["f10"])
        timeline = beh.timeline.setup_timeline(win=FakeWindow())

        with self.assertRaises(ValueError):
            timeline.run(screen)

    def test_modified_global_shortcuts_register_with_psychopy_event(self):
        """Ctrl/command shortcuts should use PsychoPy globalKeys callbacks."""
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=0.1)
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
        core = FakeCore([0.0, 0.0, 0.2])
        event = FakeEvent(key_batches=[[]])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

        registered = {(item["key"], tuple(item["modifiers"])) for item in event.globalKeys.added}
        self.assertIn(("p", ("command",)), registered)
        self.assertIn(("p", ("ctrl",)), registered)
        self.assertIn(("q", ("command",)), registered)
        self.assertIn(("q", ("ctrl",)), registered)

    def test_custom_global_action_can_show_followup_screen(self):
        """Action screens should run after the interrupted screen and save once."""
        followup = beh_timeline.Screen(
            stimuli=[FakeStim()],
            duration=0.1,
            data={"screen_name": "researcher_pause"},
        )
        action = beh_keys.GlobalKeyAction(
            name="custom_pause",
            keys=["F10"],
            set_state={"pause_experiment": True},
            end_screen=True,
            screen=followup,
        )
        screen = beh_timeline.Screen(stimuli=[FakeStim()], duration=5.0, data={"screen_name": "task"})
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), global_actions=[action])
        core = FakeCore([0.0, 0.0, 0.1, 0.1, 0.1, 0.3])
        event = FakeEvent(key_batches=[["f10"], []])

        with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
            with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                timeline.run(screen)

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
        timeline = beh.timeline.setup_timeline(win=FakeWindow())
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

    def test_button_response_mode_is_not_supported(self):
        """Built-in response collection should stay limited to key/no-response modes."""
        with self.assertRaises(ValueError):
            beh_timeline.Screen(
                stimuli=[FakeStim()],
                duration=1.0,
                response="button",
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
            screen = beh_timeline.Screen(
                stimuli=[FakeStim()],
                duration=1.0,
                response="key",
                choices=["space"],
                data={"screen_name": "probe"},
            )
            timeline = beh.timeline.setup_timeline(
                win=FakeWindow(),
                raw_data_file=raw_path,
                summary_file=summary_path,
                meta_file=meta_path,
                meta_state=meta_state,
            )
            trial = timeline.make_trial(
                screens=[screen],
                data_format=lambda data: {
                    "plan_id": data[0]["plan_id"],
                    "response": data[0]["response"],
                },
            )
            core = FakeCore([0.0, 0.0, 0.1])
            event = FakeEvent(key_batches=[["space"]])

            with mock.patch.object(beh_timeline_screen, "_load_psychopy_core", return_value=core):
                with mock.patch.object(beh_timeline_screen, "_load_psychopy_event", return_value=event):
                    result = timeline.run(
                        trial,
                        trial_data={"plan_id": "exp_0001", "trial_id": 1},
                        return_status=True,
                    )

            with open(raw_path, "r", encoding="utf-8") as f:
                raw_rows = [json.loads(line) for line in f]
            with open(summary_path, "r", encoding="utf-8", newline="") as f:
                summary_rows = list(csv.DictReader(f))
            loaded_meta = beh_recovery.load_meta_state(meta_path)

            self.assertTrue(result)
            self.assertEqual(raw_rows[0]["screen_name"], "probe")
            self.assertEqual(summary_rows[0]["plan_id"], "exp_0001")
            self.assertEqual(loaded_meta["completed_plan_ids"], ["exp_0001"])

    def test_rejected_trial_is_written_without_completion_or_retry(self):
        """Rejected rows should be auditable while retry policy stays user-managed."""
        class FakeTrialRunner:
            """Trial-like object that rejects every run."""

            def run(self, ctx):
                """Return a rejected outcome."""
                row = ctx.trial_data
                plan_id = row["plan_id"]
                return beh_timeline.TrialOutcome(
                    status="rejected",
                    reason="eye_movement",
                    row={"plan_id": plan_id},
                    screen_rows=[{"plan_id": plan_id, "block_id": row["block_id"]}],
                )

        rows = [
            {"plan_id": "exp_0001", "block_id": 1},
            {"plan_id": "exp_0002", "block_id": 1},
        ]
        state = beh_recovery.make_meta_state(planned_rows=rows)
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), meta_state=state)

        result = timeline.run(FakeTrialRunner(), trial_data=rows[0], return_status=True)
        default_result = timeline.run(FakeTrialRunner(), trial_data=rows[1])

        statuses = [row["trial_status"] for row in timeline.summary_records]
        self.assertFalse(result)
        self.assertIsNone(default_result)
        self.assertEqual(statuses, ["rejected", "rejected"])
        self.assertEqual(state["completed_plan_ids"], [])

    def test_accepted_custom_trial_returns_true_and_marks_completion(self):
        """Accepted custom trials should return True when status is requested."""
        class FakeTrialRunner:
            """Trial-like object that accepts one row."""

            def run(self, ctx):
                """Return an accepted outcome."""
                row = ctx.trial_data
                plan_id = row["plan_id"]
                return beh_timeline.TrialOutcome(
                    status="accepted",
                    reason="no",
                    row={"plan_id": plan_id},
                    screen_rows=[{"plan_id": plan_id}],
                )

        row = {"plan_id": "exp_0001"}
        state = beh_recovery.make_meta_state(planned_rows=[row])
        timeline = beh.timeline.setup_timeline(win=FakeWindow(), meta_state=state)

        result = timeline.run(FakeTrialRunner(), trial_data=row, return_status=True)

        self.assertTrue(result)
        self.assertEqual(state["completed_plan_ids"], ["exp_0001"])


if __name__ == "__main__":
    unittest.main()

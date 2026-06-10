"""Tests for EEG marker sending and sync result records."""

import unittest

from trackflow import eeg
from trackflow.sync import SyncController


class FakePort:
    """Parallel-port stand-in that records setData calls."""

    def __init__(self):
        """Initialize write log."""
        self.writes = []

    def setData(self, code):
        """Record one parallel-port write."""
        self.writes.append(int(code))


class FakeCore:
    """PsychoPy core stand-in that records waits."""

    def __init__(self):
        """Initialize wait log."""
        self.waits = []

    def wait(self, duration):
        """Record one wait duration."""
        self.waits.append(float(duration))


class FakeEegSender:
    """EEG sender stand-in with optional failure."""

    def __init__(self, fail=False):
        """Store failure mode and initialize code log."""
        self.fail = fail
        self.sent = []

    def send(self, code):
        """Record a code or raise a scripted failure."""
        if self.fail:
            raise RuntimeError("port failed")
        self.sent.append(int(code))


class FakeGazeSender:
    """EyeLink stand-in that records messages."""

    def __init__(self):
        """Initialize message log."""
        self.messages = []

    def send_msg(self, text):
        """Record one EyeLink message."""
        self.messages.append(str(text))


class EegTests(unittest.TestCase):
    """Check parallel-port marker sender behavior without hardware."""

    def test_setup_port_requires_explicit_address_for_real_hardware(self):
        """Real EEG setup should not assume a package-level port address."""
        with self.assertRaises(ValueError):
            eeg.setup_port()

    def test_parallel_sender_pulses_code_then_zero(self):
        """Parallel sender should preserve code-wait-zero pulse behavior."""
        port = FakePort()
        core = FakeCore()
        sender = eeg.setup_port(port=port, core=core)

        sender.send(21)

        self.assertEqual(port.writes, [21, 0])
        self.assertEqual(core.waits, [0.005])

    def test_debug_sender_records_codes_without_hardware(self):
        """Debug setup should not require a port address or PsychoPy import."""
        sender = eeg.setup_port(debug=True)

        sender.send(21)
        sender.send(22)

        self.assertEqual(sender.sent_codes, [21, 22])

    def test_sender_stores_code_dictionary(self):
        """EEG sender should keep a validated code dictionary for hooks."""
        sender = eeg.setup_port(debug=True, code={"sample": 21, "response": 31})

        self.assertEqual(sender.code, {"sample": 21, "response": 31})

    def test_invalid_marker_code_raises_clear_error(self):
        """Marker codes should stay in the 8-bit non-zero trigger range."""
        sender = eeg.setup_port(debug=True)

        with self.assertRaises(ValueError):
            sender.send(0)


class SyncTests(unittest.TestCase):
    """Check sync send records and failure state."""

    def test_sync_send_returns_marker_without_mutating_data(self):
        """Sync send should not append to behavior data automatically."""
        data = {"markers": [], "messages": []}
        state = {}
        eeg_sender = FakeEegSender()
        gaze_sender = FakeGazeSender()
        sync = SyncController(eeg=eeg_sender, gaze=gaze_sender, state=state)

        result = sync.send(21)

        self.assertEqual(data, {"markers": [], "messages": []})
        self.assertEqual(result.markers, [{"source": "eeg", "code": 21, "status": "sent"}])
        self.assertEqual(result.messages, [])
        self.assertEqual(eeg_sender.sent, [21])
        self.assertEqual(gaze_sender.messages, [])
        self.assertEqual(state, {})

    def test_sync_records_can_be_extended_into_data(self):
        """Users should be able to save returned records explicitly."""
        data = {"markers": [], "messages": []}
        sync = SyncController(eeg=FakeEegSender(), gaze=FakeGazeSender(), state={})

        result = sync.send(31, gaze_message="response")
        data["markers"].extend(result.markers)
        data["messages"].extend(result.messages)

        self.assertEqual(data["markers"][0]["code"], 31)
        self.assertEqual(data["messages"][0]["text"], "response")

    def test_sync_exposes_sender_code_dictionary(self):
        """ctx.sync.code should expose the EEG sender's code dictionary."""
        eeg_sender = FakeEegSender()
        eeg_sender.code = {"sample": 21}
        sync = SyncController(eeg=eeg_sender, state={})

        self.assertEqual(sync.code, {"sample": 21})

    def test_sync_send_rejects_string_code_keys(self):
        """Users should explicitly look up code keys before sending."""
        sync = SyncController(eeg=FakeEegSender(), state={})

        with self.assertRaises(ValueError):
            sync.send("sample")

    def test_explicit_gaze_message_sends_to_eyelink(self):
        """EyeLink messages should send only when gaze_message is explicit."""
        gaze_sender = FakeGazeSender()
        sync = SyncController(gaze=gaze_sender, state={})

        result = sync.send(21, gaze_message="sample")

        self.assertEqual(result.markers, [])
        self.assertEqual(result.messages, [{"source": "eyelink", "text": "sample", "status": "sent"}])
        self.assertEqual(gaze_sender.messages, ["sample"])

    def test_eeg_failure_returns_record_and_sets_pause_state(self):
        """Failed EEG sends should be visible in records and timeline state."""
        state = {}
        sync = SyncController(eeg=FakeEegSender(fail=True), state=state)

        result = sync.send(21)

        self.assertEqual(result.markers[0]["status"], "failed")
        self.assertIn("port failed", result.markers[0]["error"])
        self.assertTrue(state["pause_experiment"])
        self.assertIn("21", state["sync_error"])


if __name__ == "__main__":
    unittest.main()

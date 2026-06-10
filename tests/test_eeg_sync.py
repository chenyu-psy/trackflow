"""Tests for EEG marker sending."""

import unittest

from trackflow import eeg


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


if __name__ == "__main__":
    unittest.main()

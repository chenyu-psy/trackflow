"""Tests for the public gaze helper API."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trackflow import gaze
from trackflow.beh.timeline.context import TrackerRuntime
from trackflow.gaze import monitor as gaze_monitor
from trackflow.gaze import tracker as gaze_tracker


class FakeWindow:
    """Small PsychoPy-window stand-in for gaze monitor tests."""

    def __init__(self):
        """Create a fake 100 x 100 pixel window."""
        self.size = (100, 100)
        self.color = "#7F7F7F"

    def flip(self):
        """Match the PsychoPy window method used by gaze helpers."""
        return None


class FakeTracker:
    """Tracker stand-in with controllable gaze samples and recovery counters."""

    def __init__(self, samples, cfg=None):
        """Store samples for repeated gaze checks.

        Parameters
        ----------
        samples : list
            Sequence of ``(left, right)`` gaze sample pairs.
        cfg : gaze.GazeConfig | None, optional
            Gaze config used by monitor-default tests.
        """
        self.samples = list(samples)
        self.cfg = cfg or gaze.GazeConfig()
        self.stop_recording_calls = 0
        self.run_drift_correction_calls = 0
        self.run_calibration_calls = 0

    @property
    def gaze_data_both(self):
        """Return the next fake gaze sample."""
        if len(self.samples) > 1:
            return self.samples.pop(0)
        return self.samples[0]

    def stop_recording(self):
        """Record stop calls made after gaze breaks."""
        self.stop_recording_calls += 1

    def run_drift_correction(self, position=None, setup=1):
        """Record drift-correction calls."""
        self.run_drift_correction_calls += 1

    def run_calibration(self, **kwargs):
        """Record calibration calls."""
        self.run_calibration_calls += 1


class FakeClock:
    """Deterministic clock for wait-loop tests."""

    def __init__(self):
        """Start the fake clock at zero seconds."""
        self.t = 0.0

    def now(self):
        """Return the current fake time."""
        return self.t

    def sleep(self, duration):
        """Advance fake time instead of sleeping."""
        self.t += duration


class FakeVisual:
    """Capture PsychoPy visual calls made by feedback drawing."""

    calls = []

    class TextStim:
        """Fake TextStim that records color and text arguments."""

        def __init__(self, *args, **kwargs):
            """Store constructor arguments for later assertions."""
            FakeVisual.calls.append(("TextStim", args, kwargs))

        def draw(self):
            """Match PsychoPy draw API."""
            return None

    class Circle:
        """Fake Circle that records marker arguments."""

        def __init__(self, *args, **kwargs):
            """Store constructor arguments for later assertions."""
            FakeVisual.calls.append(("Circle", args, kwargs))

        def draw(self):
            """Match PsychoPy draw API."""
            return None

    class Rect:
        """Fake Rect that records background arguments."""

        def __init__(self, *args, **kwargs):
            """Store constructor arguments for later assertions."""
            FakeVisual.calls.append(("Rect", args, kwargs))

        def draw(self):
            """Match PsychoPy draw API."""
            return None


class GazeTests(unittest.TestCase):
    """Check import, sample monitoring, and gaze feedback behavior."""

    def test_gaze_config_defaults_match_discussed_api(self):
        """GazeConfig should contain gaze settings but no session switches."""
        cfg = gaze.GazeConfig()
        self.assertEqual(cfg.tracked_eye, "BOTH")
        self.assertEqual(cfg.calibration_type, "HV9")
        self.assertEqual(cfg.calibration_area, (0.5, 0.5))
        self.assertEqual(cfg.max_dist_deg, 1.25)
        self.assertEqual(cfg.bg_color, "#7F7F7F")
        self.assertFalse(hasattr(cfg, "enabled"))
        self.assertFalse(hasattr(cfg, "edf_name"))
        self.assertFalse(hasattr(cfg, "debug"))

    def test_tracking_settings_match_validation_area_to_calibration_area(self):
        """Internal EyeLink settings should keep validation and calibration areas aligned."""
        cfg = gaze.GazeConfig(
            calibration_type="HV5",
            calibration_area=(0.35, 0.4),
            bg_color="#FFFFFF",
            eyelink_settings={"sample_rate": 500, "validation_area_proportion": (1.0, 1.0)},
        )
        settings = gaze._make_tracking_settings(cfg)
        self.assertEqual(settings["calibration_type"], "HV5")
        self.assertEqual(settings["calibration_area_proportion"], (0.35, 0.4))
        self.assertEqual(settings["validation_area_proportion"], (0.35, 0.4))
        self.assertEqual(settings["background_color"], "#FFFFFF")
        self.assertEqual(settings["foreground_color"], "#000000")
        self.assertEqual(settings["sample_rate"], 500)

    def test_run_calibration_sends_settings_and_enters_calibration_only(self):
        """run_calibration should not own participant instruction pages."""
        tracker = object.__new__(gaze.ConnectedEyeLinker)
        tracker.cfg = gaze.GazeConfig(calibration_type="HV9", calibration_area=(0.5, 0.5))
        sent_settings = []
        calibrate_calls = []

        def send_tracking_settings(settings):
            """Capture settings sent before calibration."""
            sent_settings.append(settings)

        def calibrate():
            """Record calibration entry."""
            calibrate_calls.append(True)

        tracker.send_tracking_settings = send_tracking_settings
        tracker.calibrate = calibrate

        tracker.run_calibration(calibration_type="HV5", calibration_area=(0.35, 0.4))

        self.assertEqual(len(sent_settings), 1)
        self.assertEqual(sent_settings[0]["calibration_type"], "HV5")
        self.assertEqual(sent_settings[0]["calibration_area_proportion"], (0.35, 0.4))
        self.assertEqual(sent_settings[0]["validation_area_proportion"], (0.35, 0.4))
        self.assertEqual(calibrate_calls, [True])

    def test_setup_tracker_debug_returns_debug_tracker_without_pylink(self):
        """Debug setup should not import or connect to EyeLink."""
        cfg = gaze.GazeConfig()
        with mock.patch.object(gaze_tracker, "_load_pylink", side_effect=AssertionError("pylink should not load")):
            tracker = gaze.setup_tracker(FakeWindow(), cfg=cfg, edf_name="S01.edf", monitor="mon", debug=True)
        self.assertIsInstance(tracker, gaze.DebugEyeLinker)
        self.assertTrue(tracker.debug)
        self.assertIs(tracker.cfg, cfg)
        self.assertEqual(tracker.monitor, "mon")

    def test_debug_tracker_skips_calibration_and_drift(self):
        """Debug tracker calibration and drift methods should be no-ops."""
        tracker = gaze.setup_tracker(FakeWindow(), cfg=gaze.GazeConfig(), edf_name="S01.edf", debug=True)
        self.assertIsNone(tracker.run_calibration())
        self.assertIsNone(tracker.run_drift_correction())
        self.assertEqual(tracker.gaze_data_both, (None, None))

    def test_setup_tracker_requires_real_eyelink_outside_debug(self):
        """Non-debug setup should raise if pylink/EyeLink is unavailable."""
        with mock.patch.object(gaze_tracker, "_load_pylink", side_effect=RuntimeError("missing pylink")):
            with self.assertRaises(RuntimeError):
                gaze.setup_tracker(FakeWindow(), cfg=gaze.GazeConfig(), edf_name="S01.edf", debug=False)

    def test_eye_tracking_metadata_returns_verified_files_in_run_order(self):
        """Metadata readers should expose only verified EDFs in run order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subject_dir = Path(tmpdir) / "sub01"
            subject_dir.mkdir()
            state = {"version": 1}
            gaze.register_edf_file(
                state,
                run_id=2,
                filename="sub01_r002.edf",
                host_filename="P001R002.edf",
            )
            gaze.register_edf_file(
                state,
                run_id=1,
                filename="sub01_r001.edf",
                host_filename="P001R001.edf",
            )
            for run_id in (1, 2):
                path = subject_dir / f"sub01_r{run_id:03d}.edf"
                path.write_bytes(f"edf-{run_id}".encode("ascii"))
                gaze.mark_edf_transferred(state, run_id, path)
            meta_path = subject_dir / "sub01_meta.json"
            meta_path.write_text(json.dumps(state), encoding="utf-8")

            files = gaze.get_eye_tracking_files(meta_path, subject_dir)

        self.assertEqual([path.name for path in files], ["sub01_r001.edf", "sub01_r002.edf"])

    def test_eye_tracking_metadata_excludes_missing_or_changed_files(self):
        """Metadata readers should omit files that no longer match their digest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subject_dir = Path(tmpdir) / "sub01"
            subject_dir.mkdir()
            state = {"version": 1}
            gaze.register_edf_file(
                state,
                run_id=1,
                filename="sub01_r001.edf",
                host_filename="P001R001.edf",
            )
            path = subject_dir / "sub01_r001.edf"
            path.write_bytes(b"original")
            gaze.mark_edf_transferred(state, 1, path)
            path.write_bytes(b"changed")
            meta_path = subject_dir / "sub01_meta.json"
            meta_path.write_text(json.dumps(state), encoding="utf-8")

            files = gaze.get_eye_tracking_files(meta_path, subject_dir)

        self.assertEqual(files, [])

    def test_eye_tracking_metadata_remains_portable_after_directory_copy(self):
        """Relative registry filenames should resolve in a copied subject directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subject_dir = Path(tmpdir) / "original" / "sub01"
            subject_dir.mkdir(parents=True)
            state = {"version": 1}
            gaze.register_edf_file(
                state,
                run_id=1,
                filename="sub01_r001.edf",
                host_filename="P001R001.edf",
            )
            edf_path = subject_dir / "sub01_r001.edf"
            edf_path.write_bytes(b"portable-edf")
            gaze.mark_edf_transferred(state, 1, edf_path)
            meta_path = subject_dir / "sub01_meta.json"
            meta_path.write_text(json.dumps(state), encoding="utf-8")

            copied_dir = Path(tmpdir) / "copied" / "sub01"
            shutil.copytree(subject_dir, copied_dir)
            files = gaze.get_eye_tracking_files(copied_dir / meta_path.name, copied_dir)

        self.assertEqual([path.parent for path in files], [copied_dir])
        self.assertEqual(files[0].name, "sub01_r001.edf")

    def test_eye_tracking_metadata_falls_back_to_legacy_subject_edf(self):
        """Old metadata without a registry should find the legacy EDF filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subject_dir = Path(tmpdir) / "sub01"
            subject_dir.mkdir()
            legacy = subject_dir / "sub01.edf"
            legacy.write_bytes(b"legacy")
            meta_path = subject_dir / "sub01_meta.json"
            meta_path.write_text(json.dumps({"version": 1}), encoding="utf-8")

            files = gaze.get_eye_tracking_files(meta_path, subject_dir)

        self.assertEqual(files, [legacy])

    def test_transfer_edf_accepts_registered_host_source_and_protects_destination(self):
        """Transfers should support historical host names without local overwrite."""
        calls = []

        class TransferHandle:
            """Write deterministic bytes for one simulated Host transfer."""

            def receiveDataFile(self, source, destination):
                """Record the source and create the requested local file."""
                calls.append((source, destination))
                Path(destination).write_bytes(b"edf-data")
                return len(b"edf-data")

        tracker = object.__new__(gaze.ConnectedEyeLinker)
        tracker.edf_name = "P001R002.edf"
        tracker.tracker = TransferHandle()
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / ".sub01_r001.edf.part"
            size = tracker.transfer_edf(
                destination,
                source_name="P001R001.edf",
            )
            with self.assertRaises(FileExistsError):
                tracker.transfer_edf(destination, source_name="P001R001.edf")

        self.assertEqual(size, len(b"edf-data"))
        self.assertEqual(calls, [("P001R001.edf", str(destination))])

    def test_continue_key_split_allows_mouse_tokens(self):
        """Continue-key parsing should keep PsychoPy key names unchanged."""
        keys, buttons = gaze._split_continue_keys(("space", "mouse_left", "return", "mouse_right"))
        self.assertEqual(keys, ["space", "return"])
        self.assertEqual(buttons, [0, 2])

    def test_check_accepts_gaze_inside_radius(self):
        """A centered gaze sample should not raise a gaze break."""
        tracker = FakeTracker(samples=[((52, 50), None)])
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=10,
        )
        monitor.start_tracking()
        self.assertFalse(monitor.check_fixation())
        self.assertEqual(monitor.rejection_streak, 0)

    def test_check_ignores_empty_eye_tuples(self):
        """Missing x/y values should be treated as no usable gaze sample."""
        tracker = FakeTracker(samples=[((None, None), (None, None))])
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=10,
        )
        monitor.start_tracking()
        self.assertFalse(monitor.check_fixation())
        self.assertEqual(monitor.rejection_streak, 0)

    def test_check_raises_for_gaze_outside_radius(self):
        """A far gaze sample should raise and update rejection state."""
        tracker = FakeTracker(samples=[((80, 50), None)])
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=10,
        )
        monitor.start_tracking()
        with self.assertRaises(gaze.GazeBreakError) as err_ctx:
            monitor.check_fixation()
        self.assertEqual(err_ctx.exception.pos, (30.0, 0.0))
        self.assertEqual(monitor.rejection_streak, 1)
        self.assertEqual(tracker.stop_recording_calls, 1)

    def test_monitor_reports_consecutive_rejection_streak(self):
        """Repeated gaze breaks should accumulate in the public streak API."""
        tracker = FakeTracker(samples=[((80, 50), None), ((50, 80), None)])
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=10,
        )
        monitor.start_tracking()
        for _ in range(2):
            with self.assertRaises(gaze.GazeBreakError):
                monitor.check_fixation()

        self.assertEqual(monitor.get_rejection_streak(), 2)

    def test_monitor_reset_rejections_clears_streak_and_error(self):
        """Resetting rejection state should clear both count and last error."""
        tracker = FakeTracker(samples=[((80, 50), None)])
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=10,
        )
        monitor.start_tracking()
        with self.assertRaises(gaze.GazeBreakError):
            monitor.check_fixation()

        monitor.reset_rejections()

        self.assertEqual(monitor.get_rejection_streak(), 0)
        self.assertIsNone(monitor.last_error)

    def test_wait_checks_until_duration_passes(self):
        """wait should repeatedly check gaze while advancing through duration."""
        clock = FakeClock()
        tracker = FakeTracker(samples=[((50, 50), None)])
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=10,
            time_func=clock.now,
            sleep_func=clock.sleep,
        )
        monitor.start_tracking()
        self.assertFalse(monitor.wait(0.03, sample_interval=0.01))
        self.assertGreaterEqual(clock.t, 0.03)

    def test_monitor_uses_tracker_config_defaults(self):
        """GazeMonitor should use tracker cfg for gaze-radius defaults."""
        cfg = gaze.GazeConfig(max_dist_deg=2.0)
        tracker = FakeTracker(samples=[((50, 50), None)], cfg=cfg)
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=12,
        )
        self.assertEqual(monitor.max_dist_deg, 2.0)
        self.assertEqual(monitor.pix_radius, 12)

    def test_monitor_explicit_overrides_beat_config(self):
        """Explicit monitor arguments should override cfg defaults."""
        cfg = gaze.GazeConfig(max_dist_deg=2.0)
        tracker = FakeTracker(samples=[((50, 50), None)], cfg=cfg)
        monitor = gaze_monitor.GazeMonitor(
            tracker=tracker,
            win=FakeWindow(),
            pix_radius=9,
            max_dist_deg=0.8,
        )
        self.assertEqual(monitor.max_dist_deg, 0.8)

    def test_debug_tracker_make_monitor_uses_saved_context(self):
        """make_monitor should use saved cfg, win, and monitor context."""
        cfg = gaze.GazeConfig(max_dist_deg=1.7)
        win = FakeWindow()
        tracker = gaze.setup_tracker(win, cfg=cfg, edf_name="S01.edf", monitor="mon", debug=True)
        monitor = tracker.make_monitor(pix_radius=11)
        self.assertIs(monitor.tracker, tracker)
        self.assertIs(monitor.win, win)
        self.assertEqual(monitor.monitor, "mon")
        self.assertEqual(monitor.max_dist_deg, 1.7)

    def test_debug_tracker_reuses_internal_monitor_for_fixation_helpers(self):
        """Tracker fixation helpers should use one internally managed monitor."""
        tracker = gaze.setup_tracker(FakeWindow(), cfg=gaze.GazeConfig(), edf_name="S01.edf", debug=True)
        monitor = mock.Mock()
        monitor.check_fixation.return_value = True

        with mock.patch.object(tracker, "make_monitor", return_value=monitor) as make_monitor:
            tracker.start_tracking()
            result = tracker.check_fixation()
            tracker.stop_tracking()

        make_monitor.assert_called_once_with()
        monitor.start_tracking.assert_called_once_with()
        monitor.check_fixation.assert_called_once_with()
        monitor.stop_tracking.assert_called_once_with()
        self.assertTrue(result)

    def test_tracker_wrappers_forward_rejection_state_helpers(self):
        """Tracker wrappers should expose the internal monitor rejection state."""
        tracker = gaze.setup_tracker(FakeWindow(), cfg=gaze.GazeConfig(), edf_name="S01.edf", debug=True)
        monitor = mock.Mock()
        monitor.get_rejection_streak.return_value = 4

        with mock.patch.object(tracker, "make_monitor", return_value=monitor):
            self.assertEqual(tracker.get_rejection_streak(), 4)
            tracker.reset_rejections()

        monitor.get_rejection_streak.assert_called_once_with()
        monitor.reset_rejections.assert_called_once_with()

    def test_connected_tracker_forwards_rejection_state_helpers(self):
        """Connected tracker wrapper should expose internal monitor rejection state."""
        tracker = object.__new__(gaze.ConnectedEyeLinker)
        monitor = mock.Mock()
        monitor.get_rejection_streak.return_value = 5
        tracker._gaze_monitor = monitor

        self.assertEqual(tracker.get_rejection_streak(), 5)
        tracker.reset_rejections()

        monitor.get_rejection_streak.assert_called_once_with()
        monitor.reset_rejections.assert_called_once_with()

    def test_tracker_runtime_facade_forwards_rejection_state_helpers(self):
        """Screen-hook tracker facade should expose rejection streak helpers."""
        tracker = mock.Mock()
        tracker.get_rejection_streak.return_value = 3
        runtime = TrackerRuntime(tracker=tracker)

        self.assertEqual(runtime.get_rejection_streak(), 3)
        runtime.reset_rejections()

        tracker.get_rejection_streak.assert_called_once_with()
        tracker.reset_rejections.assert_called_once_with()

    def test_tracker_runtime_facade_uses_monitor_fallback(self):
        """TrackerRuntime should use a created monitor when tracker lacks helpers."""
        monitor = mock.Mock()
        monitor.get_rejection_streak.return_value = 2
        tracker = mock.Mock(spec=["make_monitor"])
        tracker.make_monitor.return_value = monitor
        runtime = TrackerRuntime(tracker=tracker)

        self.assertEqual(runtime.get_rejection_streak(), 2)
        runtime.reset_rejections()

        tracker.make_monitor.assert_called_once_with()
        monitor.get_rejection_streak.assert_called_once_with()
        monitor.reset_rejections.assert_called_once_with()

    def test_gaze_break_feedback_uses_neutral_text_and_red_marker(self):
        """Feedback should reserve red for the measured gaze marker."""
        cfg = gaze.GazeConfig(bg_color="#7F7F7F")
        tracker = FakeTracker(samples=[((80, 50), None)], cfg=cfg)
        monitor = gaze_monitor.GazeMonitor(tracker=tracker, win=FakeWindow(), pix_radius=10)
        monitor.last_error = gaze.GazeBreakError("break", x=30, y=0)
        FakeVisual.calls = []
        with mock.patch.object(gaze_monitor, "_load_psychopy_module", return_value=FakeVisual):
            with mock.patch.object(gaze_monitor, "_wait_for_continue", return_value="space"):
                monitor.show_feedback()

        text_calls = [call for call in FakeVisual.calls if call[0] == "TextStim"]
        circle_calls = [call for call in FakeVisual.calls if call[0] == "Circle"]
        rect_calls = [call for call in FakeVisual.calls if call[0] == "Rect"]
        self.assertEqual(rect_calls[0][2]["fillColor"], "#7F7F7F")
        self.assertIn("Press the space bar to continue.", text_calls[0][2]["text"])
        self.assertNotEqual(text_calls[0][2]["color"], "#FF0000")
        self.assertEqual(circle_calls[-1][2]["fillColor"], "#FF0000")


if __name__ == "__main__":
    unittest.main()

"""EyeLink tracker wrappers and setup entrypoint."""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable, Optional, Sequence, Tuple

from .config import (
    GazeConfig,
    _make_tracking_settings,
    _readable_text_color,
    _validate_edf_name,
)
from .display import _make_eyelink_display
from .monitor import GazeBreakError, GazeMonitor
from .runtime import (
    _hex_to_rgb255,
    _load_pylink,
)


def _try_connection() -> Tuple[bool, Any, Optional[BaseException]]:
    """Attempt one EyeLink connection.

    Returns
    -------
    tuple[bool, object | None, BaseException | None]
        Connected flag, tracker handle, and any connection exception.
    """
    pylink = _load_pylink()
    print("Attempting to connect to eye tracker...")
    try:
        tracker = pylink.EyeLink()
        return True, tracker, None
    except RuntimeError as exc:
        return False, None, exc


class ConnectedEyeLinker:
    """Wrapper around a connected EyeLink tracker.

    The method names mirror the stable behavior from `trackNeuAct` while the
    public package API exposes smaller helper functions around this object.
    """

    def __init__(
        self,
        win: Any,
        cfg: GazeConfig,
        edf_name: str,
        monitor: Any = None,
        tracker: Any = None,
    ):
        """Create a connected EyeLink wrapper.

        Parameters
        ----------
        win : psychopy.visual.Window
            Window used for EyeLink setup screens.
        edf_name : str
            EDF filename on the EyeLink host. Must end with ``.edf`` and fit
            EyeLink's short filename limit.
        cfg : GazeConfig
            Gaze settings used for tracker setup and monitor defaults.
        monitor : psychopy.monitors.Monitor | None, optional
            Monitor object used later for degree-to-pixel conversion.
        tracker : object | None, optional
            Existing pylink tracker handle. A new connection is opened when
            omitted.
        """
        _validate_edf_name(edf_name)
        self.win = win
        self.cfg = cfg
        self.monitor = monitor
        self.edf_name = edf_name
        self.edf_open = False
        self.tracked_eye = cfg.tracked_eye
        self.resolution = tuple(win.size)
        self.tracker = tracker if tracker is not None else _load_pylink().EyeLink()
        self.display = _make_eyelink_display(win, self.tracker)
        self.debug = False
        self.graphics_initialized = False
        self.text_color = _readable_text_color(cfg.bg_color)
        self._gaze_monitor = None

    def initialize_graphics(self) -> None:
        """Open EyeLink calibration graphics through PsychoPy.

        Returns
        -------
        None
            Initializes pylink graphics once.
        """
        if self.graphics_initialized:
            return
        pylink = _load_pylink()
        try:
            pylink.closeGraphics()
        except Exception:
            pass
        self.set_offline_mode()
        pylink.openGraphicsEx(self.display)
        time.sleep(0.05)
        self.graphics_initialized = True

    def open_edf(self) -> None:
        """Open the EDF file on the EyeLink host.

        Returns
        -------
        None
            Marks the EDF as open.
        """
        self.tracker.openDataFile(self.edf_name)
        self.edf_open = True

    def initialize_tracker(self) -> None:
        """Send basic tracker commands that should be stable across tasks.

        Returns
        -------
        None
            Configures screen coordinates and data filters.
        """
        if not self.edf_open:
            raise RuntimeError("EDF file must be open before tracker initialization.")
        pylink = _load_pylink()
        pylink.flushGetkeyQueue()
        self.set_offline_mode()
        self.send_command("screen_pixel_coords = 0 0 %d %d" % self.resolution)
        self.send_msg("DISPLAY_COORDS 0 0 %d %d" % self.resolution)
        self.tracker.setFileEventFilter("LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON")
        self.tracker.setFileSampleFilter("LEFT,RIGHT,GAZE,AREA,GAZERES,STATUS")
        self.tracker.setLinkEventFilter("LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON")
        self.tracker.setLinkSampleFilter("LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS")

    def send_tracking_settings(self, settings: Optional[dict] = None) -> None:
        """Send EyeLink calibration and sampling settings.

        Parameters
        ----------
        settings : dict | None, optional
            Settings that override default EyeLink tracking settings.

        Returns
        -------
        None
            Sends commands to the tracker.
        """
        if not self.graphics_initialized:
            self.initialize_graphics()
        pylink = _load_pylink()
        cfg = _make_tracking_settings(self.cfg)
        if settings is not None:
            cfg.update(settings)

        self.send_command("elcl_select_configuration = %s" % cfg["elcl_configuration"])
        calibration_set = False
        for attempt in range(3):
            try:
                pylink.setCalibrationColors(
                    _hex_to_rgb255(cfg["foreground_color"]),
                    _hex_to_rgb255(cfg["background_color"]),
                )
                pylink.setCalibrationSounds(cfg["target_sound"], cfg["good_sound"], cfg["error_sound"])
                calibration_set = True
                break
            except RuntimeError as exc:
                if "opengraphics" not in str(exc).lower():
                    raise
                if attempt == 2:
                    break
                self.graphics_initialized = False
                try:
                    pylink.closeGraphics()
                except Exception:
                    pass
                time.sleep(0.05)
                self.initialize_graphics()
        if not calibration_set:
            print("[warn] EyeLink calibration colors/sounds could not be set. Continuing with defaults.")

        if self.tracked_eye in ("LEFT", "RIGHT"):
            self.send_command("active_eye = %s" % self.tracked_eye)
        self.send_command("automatic_calibration_pacing = %i" % cfg["automatic_calibration_pacing"])
        self.send_command("binocular_enabled = YES" if self.tracked_eye == "BOTH" else "binocular_enabled = NO")
        self.send_command("calibration_area_proportion %f %f" % cfg["calibration_area_proportion"])
        self.send_command("calibration_type = %s" % cfg["calibration_type"])
        self.send_command("enable_automatic_calibration = %s" % cfg["enable_automatic_calibration"])
        if cfg["preamble_text"] is not None:
            self.send_command('add_file_preamble_text "%s"' % cfg["preamble_text"])
        self.send_command("pupil_size_diameter = %s" % cfg["pupil_size_diameter"])
        self.send_command("saccade_acceleration_threshold = %i" % cfg["saccade_acceleration_threshold"])
        self.send_command("saccade_motion_threshold = %f" % cfg["saccade_motion_threshold"])
        self.send_command("saccade_pursuit_fixup = %i" % cfg["saccade_pursuit_fixup"])
        self.send_command("saccade_velocity_threshold = %i" % cfg["saccade_velocity_threshold"])
        self.send_command("sample_rate = %i" % cfg["sample_rate"])
        self.send_command("validation_area_proportion %f %f" % cfg["validation_area_proportion"])

    def run_calibration(
        self,
        calibration_type: Optional[str] = None,
        calibration_area: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Run EyeLink calibration with optional per-call settings.

        Parameters
        ----------
        calibration_type : str | None, optional
            Calibration type for this calibration only. Defaults to
            ``self.cfg.calibration_type``.
        calibration_area : tuple[float, float] | None, optional
            Calibration area for this calibration only. Validation area is
            matched to the same values.

        Returns
        -------
        None
            Runs the calibration workflow.
        """
        settings = _make_tracking_settings(
            self.cfg,
            calibration_type=calibration_type,
            calibration_area=calibration_area,
        )
        self.send_tracking_settings(settings)
        self.calibrate()

    def run_drift_correction(self, position: Optional[Tuple[int, int]] = None, setup: int = 1) -> None:
        """Run EyeLink drift correction.

        Parameters
        ----------
        position : tuple[int, int] | None, optional
            EyeLink host pixel coordinate. Defaults to screen center.
        setup : int, optional
            EyeLink setup flag passed through to drift correction.

        Returns
        -------
        None
            Runs drift correction when EyeLink accepts it.
        """
        self.drift_correct(position=position, setup=setup)

    def make_monitor(
        self,
        max_dist_deg: Optional[float] = None,
        pix_radius: Optional[float] = None,
        fixation: Any = None,
        time_func: Optional[Callable[[], float]] = None,
        sleep_func: Optional[Callable[[float], None]] = None,
    ) -> GazeMonitor:
        """Create a realtime gaze monitor using this tracker's defaults.

        Parameters
        ----------
        max_dist_deg : float | None, optional
            Optional gaze-radius override in visual degrees.
        pix_radius : float | None, optional
            Optional pixel-radius override. Takes priority over
            ``max_dist_deg``.
        fixation : object | None, optional
            Optional fixation stimulus used by feedback drawing.
        time_func : callable | None, optional
            Test hook returning current time in seconds.
        sleep_func : callable | None, optional
            Test hook used instead of PsychoPy ``core.wait``.

        Returns
        -------
        GazeMonitor
            Monitor configured from ``self.cfg`` and this tracker.
        """
        return GazeMonitor(
            tracker=self,
            win=self.win,
            monitor=self.monitor,
            max_dist_deg=max_dist_deg,
            pix_radius=pix_radius,
            fixation=fixation,
            time_func=time_func,
            sleep_func=sleep_func,
        )

    def _get_gaze_monitor(self) -> GazeMonitor:
        """Return the internally managed realtime gaze monitor."""
        if self._gaze_monitor is None:
            self._gaze_monitor = self.make_monitor()
        return self._gaze_monitor

    def start_tracking(self) -> None:
        """Start realtime fixation tracking through the internal monitor."""
        self._get_gaze_monitor().start_tracking()
        return None

    def stop_tracking(self) -> None:
        """Stop realtime fixation tracking through the internal monitor."""
        self._get_gaze_monitor().stop_tracking()
        return None

    def check_fixation(self) -> bool:
        """Check realtime fixation through the internal monitor."""
        return bool(self._get_gaze_monitor().check_fixation())

    def show_feedback(self, error: Optional[GazeBreakError] = None, continue_keys: Sequence[str] = ("space",)) -> None:
        """Show gaze-break feedback through the internal monitor."""
        self._get_gaze_monitor().show_feedback(error=error, continue_keys=continue_keys)
        return None

    def get_rejection_streak(self) -> int:
        """Return consecutive gaze rejection events from the internal monitor."""
        return int(self._get_gaze_monitor().get_rejection_streak())

    def reset_rejections(self) -> None:
        """Reset consecutive gaze rejection state on the internal monitor."""
        self._get_gaze_monitor().reset_rejections()
        return None

    def close_edf(self) -> None:
        """Close the EDF file on the EyeLink host.

        Returns
        -------
        None
            Marks the EDF as closed.
        """
        self.tracker.closeDataFile()
        self.edf_open = False

    def transfer_edf(self, save_as: Optional[str] = None) -> None:
        """Transfer the EDF from the EyeLink host to the PsychoPy computer.

        Parameters
        ----------
        save_as : str | None, optional
            Destination EDF filename. Defaults to the original EDF filename.

        Returns
        -------
        None
            Receives the EDF and prints a short confirmation.
        """
        filename = os.fspath(save_as) if save_as is not None else self.edf_name
        if not filename.endswith(".edf"):
            raise ValueError("save_as must include the .edf extension.")
        old_stdout = sys.stdout
        devnull_handle = open(os.devnull, "w")
        sys.stdout = devnull_handle
        try:
            self.tracker.receiveDataFile(self.edf_name, filename)
        finally:
            sys.stdout = old_stdout
            devnull_handle.close()
        print(f"{filename} has been transferred successfully.")

    def setup_tracker(self) -> None:
        """Open the EyeLink tracker setup menu.

        Returns
        -------
        None
            Flips the PsychoPy window and enters EyeLink setup.
        """
        self.win.flip()
        self.tracker.doTrackerSetup()

    def calibrate(self) -> None:
        """Run the EyeLink tracker setup menu for calibration.

        Returns
        -------
        None
            Enters EyeLink setup.
        """
        self.setup_tracker()

    def drift_correct(self, position: Optional[Tuple[int, int]] = None, setup: int = 1) -> None:
        """Run EyeLink drift correction.

        Parameters
        ----------
        position : tuple[int, int] | None, optional
            Pixel coordinate on the EyeLink host. Defaults to screen center.
        setup : int, optional
            EyeLink setup flag passed to ``doDriftCorrect``.

        Returns
        -------
        None
            Applies drift correction when EyeLink accepts it.
        """
        if position is None:
            position = tuple(int(round(value / 2)) for value in self.resolution)
        try:
            self.tracker.doDriftCorrect(position[0], position[1], 1, setup)
            self.tracker.applyDriftCorrect()
        except RuntimeError as exc:
            print(exc)

    def start_recording(self) -> None:
        """Start EyeLink recording.

        Returns
        -------
        None
            Starts recording and waits briefly, matching the source template.
        """
        self.tracker.startRecording(1, 1, 1, 1)
        time.sleep(0.1)

    def stop_recording(self) -> None:
        """Stop EyeLink recording.

        Returns
        -------
        None
            Waits briefly before stopping, matching the source template.
        """
        time.sleep(0.1)
        self.tracker.stopRecording()

    @property
    def gaze_data_both(self) -> Tuple[Any, Any]:
        """Return the newest left and right gaze samples.

        Returns
        -------
        tuple
            ``(left_gaze, right_gaze)`` with unavailable eyes represented by
            ``None``.
        """
        sample = self.tracker.getNewestSample()
        if not sample:
            return None, None
        if self.tracked_eye == "LEFT":
            return sample.getLeftEye().getGaze(), None
        if self.tracked_eye == "RIGHT":
            return None, sample.getRightEye().getGaze()
        return sample.getLeftEye().getGaze(), sample.getRightEye().getGaze()

    def set_offline_mode(self) -> None:
        """Set the EyeLink host to offline mode.

        Returns
        -------
        None
            Calls ``setOfflineMode`` on the tracker.
        """
        self.tracker.setOfflineMode()

    def send_command(self, cmd: str) -> None:
        """Send a command to the EyeLink host.

        Parameters
        ----------
        cmd : str
            EyeLink command string.

        Returns
        -------
        None
            Sends the command.
        """
        self.tracker.sendCommand(cmd)

    def send_msg(self, msg: str) -> None:
        """Send a message to the EDF file.

        Parameters
        ----------
        msg : str
            Message saved by EyeLink.

        Returns
        -------
        None
            Sends the message.
        """
        self.tracker.sendMessage(str(msg))

    def send_status(self, status: str) -> None:
        """Send a status line to the EyeLink host display.

        Parameters
        ----------
        status : str
            Researcher-facing status text.

        Returns
        -------
        None
            Sends a ``record_status_message`` command.
        """
        if len(status) >= 80:
            print("Warning: status should be less than 80 characters.")
        self.send_command("record_status_message '%s'" % status)

    def close_connection(self) -> None:
        """Close the EyeLink connection and graphics.

        Returns
        -------
        None
            Closes the tracker connection and pylink graphics.
        """
        self.tracker.close()
        _load_pylink().closeGraphics()

    def close(self, save_as: Optional[str] = None) -> None:
        """Finalize EyeLink recording and transfer the EDF file.

        Parameters
        ----------
        save_as : str | os.PathLike | None, optional
            Destination EDF path on the PsychoPy/presenter computer. Defaults
            to the short EyeLink host EDF filename.

        Returns
        -------
        None
            Attempts the safe close sequence used by the source template:
            stop recording, set offline mode, close EDF, transfer EDF, and
            close the EyeLink connection.
        """
        try:
            try:
                self.stop_recording()
            except Exception:
                pass
            self.set_offline_mode()
            time.sleep(0.5)
            self.close_edf()
            time.sleep(0.5)
            self.transfer_edf(save_as=save_as)
        finally:
            self.close_connection()


class DebugEyeLinker:
    """Debug tracker used when a session should not connect to EyeLink."""

    def __init__(self, win: Any, cfg: GazeConfig, edf_name: str, monitor: Any = None):
        """Create a debug tracker with the same core methods as the real wrapper.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window used by the experiment.
        cfg : GazeConfig
            Gaze settings kept for monitor defaults.
        edf_name : str
            EDF filename that would have been used.
        monitor : psychopy.monitors.Monitor | None, optional
            Monitor object used later for degree-to-pixel conversion.
        """
        _validate_edf_name(edf_name)
        self.win = win
        self.cfg = cfg
        self.monitor = monitor
        self.edf_name = edf_name
        self.edf_open = False
        self.tracked_eye = cfg.tracked_eye
        self.resolution = tuple(win.size)
        self.tracker = None
        self.display = None
        self.debug = True
        self.graphics_initialized = True
        self.text_color = _readable_text_color(cfg.bg_color)
        self.gaze_data_both = (None, None)
        self._gaze_monitor = None

    def initialize_graphics(self) -> None:
        """No-op graphics initialization for debug mode."""
        return None

    def open_edf(self) -> None:
        """Mark the debug EDF state as open."""
        self.edf_open = True

    def initialize_tracker(self) -> None:
        """No-op tracker initialization for debug mode."""
        return None

    def send_tracking_settings(self, settings: Optional[dict] = None) -> None:
        """No-op settings send for debug mode."""
        return None

    def close_edf(self) -> None:
        """Mark the debug EDF state as closed."""
        self.edf_open = False

    def transfer_edf(self, save_as: Optional[str] = None) -> None:
        """No-op EDF transfer for debug mode."""
        return None

    def setup_tracker(self) -> None:
        """No-op tracker setup for debug mode."""
        return None

    def calibrate(self) -> None:
        """No-op calibration for debug mode."""
        return None

    def run_calibration(
        self,
        calibration_type: Optional[str] = None,
        calibration_area: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Skip calibration in debug mode.

        Calibration settings are accepted so debug and connected trackers can
        be swapped without changing experiment flow code.
        """
        return None

    def drift_correct(self, position: Optional[Tuple[int, int]] = None, setup: int = 1) -> None:
        """No-op drift correction for debug mode."""
        return None

    def run_drift_correction(self, position: Optional[Tuple[int, int]] = None, setup: int = 1) -> None:
        """Skip drift correction in debug mode."""
        return None

    def start_recording(self) -> None:
        """No-op recording start for debug mode."""
        return None

    def stop_recording(self) -> None:
        """No-op recording stop for debug mode."""
        return None

    def set_offline_mode(self) -> None:
        """No-op offline mode for debug mode."""
        return None

    def send_command(self, cmd: str) -> None:
        """No-op command send for debug mode."""
        return None

    def send_msg(self, msg: str) -> None:
        """No-op EDF message send for debug mode."""
        return None

    def send_status(self, status: str) -> None:
        """No-op status send for debug mode."""
        return None

    def close_connection(self) -> None:
        """No-op connection close for debug mode."""
        return None

    def make_monitor(
        self,
        max_dist_deg: Optional[float] = None,
        pix_radius: Optional[float] = None,
        fixation: Any = None,
        time_func: Optional[Callable[[], float]] = None,
        sleep_func: Optional[Callable[[float], None]] = None,
    ) -> GazeMonitor:
        """Create a realtime monitor using debug tracker defaults.

        Returns
        -------
        GazeMonitor
            Monitor object that will not produce real gaze breaks because the
            debug tracker has no EyeLink samples.
        """
        return GazeMonitor(
            tracker=self,
            win=self.win,
            monitor=self.monitor,
            max_dist_deg=max_dist_deg,
            pix_radius=pix_radius,
            fixation=fixation,
            time_func=time_func,
            sleep_func=sleep_func,
        )

    def _get_gaze_monitor(self) -> GazeMonitor:
        """Return the internally managed debug gaze monitor."""
        if self._gaze_monitor is None:
            self._gaze_monitor = self.make_monitor()
        return self._gaze_monitor

    def start_tracking(self) -> None:
        """Start realtime fixation tracking through the internal monitor."""
        self._get_gaze_monitor().start_tracking()
        return None

    def stop_tracking(self) -> None:
        """Stop realtime fixation tracking through the internal monitor."""
        self._get_gaze_monitor().stop_tracking()
        return None

    def check_fixation(self) -> bool:
        """Check realtime fixation through the internal monitor."""
        return bool(self._get_gaze_monitor().check_fixation())

    def show_feedback(self, error: Optional[GazeBreakError] = None, continue_keys: Sequence[str] = ("space",)) -> None:
        """Show gaze-break feedback through the internal monitor."""
        self._get_gaze_monitor().show_feedback(error=error, continue_keys=continue_keys)
        return None

    def get_rejection_streak(self) -> int:
        """Return consecutive gaze rejection events from the internal monitor."""
        return int(self._get_gaze_monitor().get_rejection_streak())

    def reset_rejections(self) -> None:
        """Reset consecutive gaze rejection state on the internal monitor."""
        self._get_gaze_monitor().reset_rejections()
        return None

    def close(self, save_as: Optional[str] = None) -> None:
        """No-op close for debug mode."""
        return None


def setup_tracker(
    win: Any,
    cfg: GazeConfig,
    edf_name: str,
    monitor: Any = None,
    debug: bool = False,
) -> Any:
    """Create and initialize an EyeLink tracker object.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window used for tracker setup.
    cfg : GazeConfig
        Gaze settings used for EyeLink setup and monitor defaults.
    edf_name : str
        EDF filename to create on the EyeLink host.
    monitor : psychopy.monitors.Monitor | None, optional
        Monitor object saved for later degree-to-pixel conversion.
    debug : bool, optional
        If True, return a debug tracker without importing or connecting to
        pylink/EyeLink. If False, a real EyeLink connection is required.

    Returns
    -------
    object
        Initialized tracker. Calibration is not run automatically.
    """
    if debug:
        return DebugEyeLinker(win=win, cfg=cfg, edf_name=edf_name, monitor=monitor)

    connected, tracker_handle, exc = _try_connection()
    if connected:
        tracker = ConnectedEyeLinker(win=win, cfg=cfg, edf_name=edf_name, monitor=monitor, tracker=tracker_handle)
    else:
        if exc is not None:
            raise exc
        raise RuntimeError("Eye tracker connection failed.")

    tracker.initialize_graphics()
    tracker.open_edf()
    tracker.initialize_tracker()
    tracker.send_tracking_settings(_make_tracking_settings(cfg))
    return tracker

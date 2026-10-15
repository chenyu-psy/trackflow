"""Shared runtime context and outcome types for behavior timelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class TrialInterrupted(Exception):
    """Internal signal used to stop the current trial from a screen hook."""

    def __init__(
        self,
        screen: Any = None,
        data: Optional[Dict[str, Any]] = None,
        row: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store interruption metadata for trial outcome creation."""
        self.screen = screen
        self.data = dict(data or {})
        self.row = dict(row) if row is not None else None
        super().__init__("interrupted")


@dataclass
class TrackerRuntime:
    """Safe facade for eye-tracker recording and realtime fixation tracking."""

    tracker: Any = None
    _monitor: Any = None

    def start_recording(self) -> None:
        """Start tracker recording when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "start_recording"):
            self.tracker.start_recording()
        return None

    def stop_recording(self) -> None:
        """Stop tracker recording when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "stop_recording"):
            self.tracker.stop_recording()
        return None

    def send_status(self, status: str) -> None:
        """Send an EyeLink host status line when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "send_status"):
            self.tracker.send_status(str(status))
        return None

    def start_tracking(self) -> None:
        """Start realtime fixation tracking when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "start_tracking"):
            self.tracker.start_tracking()
            return None
        monitor = self._get_monitor()
        if monitor is not None and hasattr(monitor, "start_tracking"):
            monitor.start_tracking()
        return None

    def stop_tracking(self) -> None:
        """Stop realtime fixation tracking when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "stop_tracking"):
            self.tracker.stop_tracking()
            return None
        monitor = self._get_monitor()
        if monitor is not None and hasattr(monitor, "stop_tracking"):
            monitor.stop_tracking()
        return None

    def check_fixation(self) -> bool:
        """Check realtime fixation when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "check_fixation"):
            return bool(self.tracker.check_fixation())
        monitor = self._get_monitor()
        if monitor is None or not hasattr(monitor, "check_fixation"):
            return False
        return bool(monitor.check_fixation())

    def get_rejection_streak(self) -> int:
        """Return consecutive gaze rejection events when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "get_rejection_streak"):
            return int(self.tracker.get_rejection_streak())
        monitor = self._get_monitor()
        if monitor is None or not hasattr(monitor, "get_rejection_streak"):
            return 0
        return int(monitor.get_rejection_streak())

    def reset_rejections(self) -> None:
        """Reset consecutive gaze rejection state when a tracker is configured."""
        if self.tracker is not None and hasattr(self.tracker, "reset_rejections"):
            self.tracker.reset_rejections()
            return None
        monitor = self._get_monitor()
        if monitor is not None and hasattr(monitor, "reset_rejections"):
            monitor.reset_rejections()
        return None

    def _get_monitor(self) -> Any:
        """Return a tracker-created monitor when the tracker supports one."""
        if self._monitor is not None:
            return self._monitor
        if self.tracker is not None and hasattr(self.tracker, "make_monitor"):
            self._monitor = self.tracker.make_monitor()
        return self._monitor


@dataclass
class RunContext:
    """Runtime context passed to trial-like objects and screen hooks.

    Parameters
    ----------
    win : object
        PsychoPy window used for drawing.
    timeline : object
        Timeline running the current unit.
    trial_data : dict
        Data fields inherited by every screen row in the current trial run.
    params : dict
        Stable runtime parameters.
    state : dict
        Mutable runtime state.
    tracker : TrackerRuntime
        Facade for eye-tracker recording and realtime fixation tracking.
    screen : object, optional
        Current screen while hooks are running.

    Returns
    -------
    RunContext
        Context object for custom trial-like objects and hook functions.
    """

    win: Any
    timeline: Any
    trial_data: Dict[str, Any]
    params: Dict[str, Any]
    state: Dict[str, Any]
    tracker: TrackerRuntime = field(default_factory=TrackerRuntime)
    screen: Any = None

    @property
    def code(self) -> Dict[str, int]:
        """Return the configured EEG code dictionary.

        Returns
        -------
        dict
            Named EEG marker codes copied from the timeline's EEG sender.
        """
        return dict(getattr(getattr(self.timeline, "eeg", None), "code", {}) or {})

    def send(self, code: Optional[int] = None, message: Optional[str] = None) -> None:
        """Send one timeline event to configured EEG and EyeLink devices.

        Parameters
        ----------
        code : int, optional
            EEG marker code to send.
        message : str, optional
            EyeLink message text to send.

        Returns
        -------
        None
            Sends hardware side effects only. Experiment code should write any
            saved fields explicitly.
        """
        self.timeline.send(code=code, message=message)
        return None

    def send_eeg(self, code: int) -> None:
        """Send one EEG marker through the timeline."""
        self.timeline.send_eeg(code)
        return None

    def send_gaze(self, message: Any = None, status: Any = None) -> None:
        """Send EyeLink EDF messages and/or host status lines through the timeline."""
        self.timeline.send_gaze(message=message, status=status)
        return None

    def break_trial(
        self,
        screen: Any = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Interrupt the current trial from a screen hook.

        Parameters
        ----------
        screen : object, optional
            Optional feedback screen to show immediately after the interrupted
            screen. The feedback screen is not recorded as a trial row.
        data : dict, optional
            Extra interruption fields to merge into the interrupted screen row
            and outcome details.
            Use this or direct row edits for experiment-specific fields such as
            ``{"reason": "early_response"}``.

        Returns
        -------
        None
            Raises an internal interruption signal consumed by the timeline.
        """
        raise TrialInterrupted(screen=screen, data=data)


@dataclass
class TrialOutcome:
    """Result returned by one trial-like run.

    Parameters
    ----------
    status : str
        ``"accepted"``, ``"interrupted"``, or a custom nonaccepted status.
    reason : str
        Internal status detail retained for custom trial-like integrations.
    row : dict, optional
        Trial summary row.
    screen_rows : list[dict], optional
        Raw screen rows collected during the trial-like run.
    details : dict, optional
        Extra information such as eye position or hardware failure details.

    Returns
    -------
    TrialOutcome
        Trial result consumed by ``Timeline``.
    """

    status: str = "accepted"
    reason: str = "no"
    row: Optional[Dict[str, Any]] = None
    screen_rows: List[Dict[str, Any]] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def is_complete(self) -> bool:
        """Return whether this outcome should count as completed.

        Returns
        -------
        bool
            ``True`` only when ``status`` is ``"accepted"``.
        """
        return str(self.status).strip().lower() == "accepted"

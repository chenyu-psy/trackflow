"""Shared runtime context and outcome types for behavior timelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class TrialInterrupted(Exception):
    """Internal signal used to stop the current trial from a screen hook."""

    def __init__(
        self,
        reason: str,
        screen: Any = None,
        data: Optional[Dict[str, Any]] = None,
        row: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store interruption metadata for trial outcome creation."""
        reason_text = str(reason).strip()
        if not reason_text:
            raise ValueError("reason must be a non-empty string.")
        self.reason = reason_text
        self.screen = screen
        self.data = dict(data or {})
        self.row = dict(row) if row is not None else None
        super().__init__(reason_text)


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

    def send_gaze(self, message: str) -> None:
        """Send one EyeLink message through the timeline."""
        self.timeline.send_gaze(message)
        return None

    def break_trial(
        self,
        reason: str,
        screen: Any = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Interrupt the current trial from a screen hook.

        Parameters
        ----------
        reason : str
            Specific interruption cause, such as ``"eye_movement"`` or
            ``"early_press"``.
        screen : object, optional
            Optional feedback screen to show immediately after the interrupted
            screen. The feedback screen is not recorded as a trial row.
        data : dict, optional
            Extra interruption fields to merge into the interrupted screen row
            and outcome details.

        Returns
        -------
        None
            Raises an internal interruption signal consumed by the timeline.
        """
        raise TrialInterrupted(reason=reason, screen=screen, data=data)


@dataclass
class TrialOutcome:
    """Result returned by one trial-like run.

    Parameters
    ----------
    status : str
        ``"accepted"``, ``"rejected"``, or ``"interrupted"``.
    reason : str
        ``"no"`` for accepted trials, or a readable rejection/interruption
        cause.
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

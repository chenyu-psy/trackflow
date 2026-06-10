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
    sync : object, optional
        Sync helper for EEG and EyeLink sends during hooks.

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
    sync: Any = None

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

"""Shared runtime context and outcome types for behavior timelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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


@dataclass
class TrialOutcome:
    """Result returned by one trial-like run.

    Parameters
    ----------
    status : str
        ``"accepted"`` or ``"rejected"``.
    reason : str
        ``"no"`` for accepted trials, or a readable rejection reason.
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

    def is_rejected(self) -> bool:
        """Return whether this outcome should be retried.

        Returns
        -------
        bool
            ``True`` when ``status`` is ``"rejected"``.
        """
        return str(self.status).strip().lower() == "rejected"

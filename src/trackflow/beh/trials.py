"""Trial-level behavior runtime helpers.

A ``Trial`` runs a list of screens for one planned row and returns a
``TrialOutcome``. The timeline owns file writing and recovery bookkeeping so
the trial procedure remains easy to inspect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence


__all__ = ["RunContext", "Trial", "TrialOutcome"]


@dataclass
class RunContext:
    """Runtime context passed to trial and screen hooks.

    Parameters
    ----------
    win : object
        PsychoPy window used for drawing.
    timeline : object
        Timeline running the current screen or trial.
    params : dict
        Stable runtime parameters.
    state : dict
        Mutable runtime state.
    row : dict
        Planned trial row or screen row fields.
    screen : object, optional
        Current screen while hooks are running.
    sync : object, optional
        Sync helper for EEG and EyeLink sends during hooks.

    Returns
    -------
    RunContext
        Context object for hook functions.
    """

    win: Any
    timeline: Any
    params: Dict[str, Any]
    state: Dict[str, Any]
    row: Dict[str, Any]
    screen: Any = None
    sync: Any = None


@dataclass
class TrialOutcome:
    """Result returned by one trial run.

    Parameters
    ----------
    status : str
        ``"accepted"`` or ``"rejected"``.
    reason : str
        ``"no"`` for accepted trials, or a readable rejection reason.
    row : dict, optional
        Trial summary row.
    screen_rows : list[dict], optional
        Raw screen rows collected during the trial.
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


class Trial:
    """Run a list of screens for one planned trial row.

    Parameters
    ----------
    screen_list : sequence
        Screens to run in order.
    data_format : callable, optional
        Function that receives the current trial's raw screen rows and returns
        one trial summary row.

    Examples
    --------
    >>> trial = Trial([fix_screen, response_screen])
    >>> outcome = trial.run(timeline, win, {"trial_id": 1})
    """

    def __init__(
        self,
        screen_list: Sequence[Any],
        data_format: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
    ) -> None:
        """Store trial screens and optional summary formatter."""
        self.screen_list = list(screen_list)
        self.data_format = data_format

    def run(self, timeline: Any, win: Any, row: Optional[Dict[str, Any]] = None) -> TrialOutcome:
        """Run this trial and return an accepted outcome.

        Parameters
        ----------
        timeline : Timeline
            Runtime timeline that owns parameters, state, and raw row saving.
        win : psychopy.visual.Window
            PsychoPy drawing window.
        row : dict, optional
            Planned trial row copied into each screen row.

        Returns
        -------
        TrialOutcome
            Accepted trial outcome with raw screen rows and optional summary.
        """
        trial_row = dict(row or {})
        ctx = RunContext(
            win=win,
            timeline=timeline,
            params=timeline.params,
            state=timeline.state,
            row=trial_row,
            sync=timeline.sync,
        )

        screen_rows: List[Dict[str, Any]] = []
        for screen_index, screen in enumerate(self.screen_list):
            ctx.screen = screen
            if hasattr(timeline, "_prepare_screen_run"):
                timeline._prepare_screen_run(screen)
            if screen.run_if is not None and not bool(screen.run_if(ctx)):
                continue
            screen_row = screen.run(win, screen_index=screen_index, row=trial_row, ctx=ctx)
            screen_rows.append(screen_row)
            if hasattr(timeline, "_run_pending_action_screens"):
                screen_rows.extend(
                    timeline._run_pending_action_screens(
                        win,
                        trial_row,
                        record=False,
                        screen_index_start=len(screen_rows),
                    )
                )

        summary_row = None
        if self.data_format is not None:
            summary_row = self.data_format([dict(screen_row) for screen_row in screen_rows])

        return TrialOutcome(
            status="accepted",
            reason="no",
            row=summary_row,
            screen_rows=screen_rows,
        )

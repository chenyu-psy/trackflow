"""Internal screen sequence runner for behavior timelines."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from .context import RunContext, TrialOutcome


class _Trial:
    """Internal ordered screen group returned by ``Timeline.make_trial``."""

    def __init__(
        self,
        screens: Sequence[Any],
        data_format: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
        run_if: Optional[Callable[[RunContext], bool]] = None,
    ) -> None:
        """Store trial screens and optional summary formatter."""
        self.screens = list(screens)
        self.data_format = data_format
        self.run_if = run_if

    def run(self, ctx: RunContext) -> TrialOutcome:
        """Run this screen group and return an accepted outcome."""
        if self.run_if is not None and not bool(self.run_if(ctx)):
            return TrialOutcome(status="accepted", reason="no", screen_rows=[])

        screen_rows: List[Dict[str, Any]] = []
        for screen_index, screen in enumerate(self.screens):
            ctx.screen = screen
            if hasattr(ctx.timeline, "_prepare_screen_run"):
                ctx.timeline._prepare_screen_run(screen)
            screen_row = screen.run(ctx.win, screen_index=screen_index, row=ctx.trial_data, ctx=ctx)
            screen_rows.append(screen_row)
            if hasattr(ctx.timeline, "_run_pending_action_screens"):
                screen_rows.extend(
                    ctx.timeline._run_pending_action_screens(
                        ctx,
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

"""Timeline runtime for behavior screens and trials.

The timeline owns in-memory rows, optional raw JSONL output, optional summary
CSV output, meta-JSON completion state, and same-block retry scheduling.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import _psychopy
from .keys import (
    GlobalKeyAction,
    coerce_global_actions,
    fallback_key_map,
    find_response_key_conflicts,
    register_modified_shortcuts,
)
from .data import DataRows, SummaryWriter, append_jsonl
from .screens import Screen, make_screen
from .stimuli import wrap_stimulus
from .trials import RunContext, Trial, TrialOutcome
from .recovery import mark_plan_completed, save_meta_state
from ..sync import SyncController


__all__ = ["Timeline", "setup_timeline"]


class Timeline:
    """Behavior timeline with runtime state and output bookkeeping.

    Parameters
    ----------
    records : list[dict], optional
        Existing in-memory raw rows to append to.
    raw_data_file : str or pathlib.Path, optional
        JSONL file that receives one row per completed screen.
    summary_file : str or pathlib.Path, optional
        CSV file that receives one row per trial summary.
    meta_file : str or pathlib.Path, optional
        Meta JSON path used for accepted-only completion state.
    meta_state : dict, optional
        Loaded or newly-created recovery state.
    params, state : dict, optional
        Stable runtime parameters and mutable runtime state.
    seed : int, optional
        Seed for timeline-owned random operations such as retry insertion.
    eeg, gaze : object, optional
        Configured EEG sender and EyeLink wrapper used by ``ctx.sync``.
    global_actions : sequence, optional
        Researcher global-key actions. When omitted, default pause and quit
        actions are enabled.
    use_default_global_actions : bool, optional
        Whether to create default pause/quit actions when ``global_actions`` is
        omitted.

    Examples
    --------
    >>> timeline = Timeline(seed=1)
    >>> timeline.show_screen(win, screen)
    """

    def __init__(
        self,
        records: Optional[List[Dict[str, Any]]] = None,
        raw_data_file: Optional[Any] = None,
        summary_file: Optional[Any] = None,
        meta_file: Optional[Any] = None,
        meta_state: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        eeg: Optional[Any] = None,
        gaze: Optional[Any] = None,
        global_actions: Optional[Sequence[Any]] = None,
        use_default_global_actions: bool = True,
    ) -> None:
        """Create a timeline with optional file outputs."""
        self.records: List[Dict[str, Any]] = records if records is not None else []
        self.summary_records: List[Dict[str, Any]] = []
        self.raw_data_file = Path(raw_data_file) if raw_data_file is not None else None
        self.summary_file = Path(summary_file) if summary_file is not None else None
        self.meta_file = Path(meta_file) if meta_file is not None else None
        self.meta_state = meta_state
        self.params = dict(params or {})
        self.state = dict(state or {})
        self.random = random.Random(seed)
        self.eeg = eeg
        self.gaze = gaze
        self.sync = SyncController(eeg=eeg, gaze=gaze, state=self.state)
        self.global_actions = coerce_global_actions(global_actions, use_defaults=use_default_global_actions)
        if global_actions is None and use_default_global_actions:
            _attach_default_quit_screen(self.global_actions)
        self._global_action_by_name = {action.name: action for action in self.global_actions}
        self._fallback_actions = fallback_key_map(self.global_actions)
        self._modified_shortcuts_registered = False
        self._pending_action_screens: List[Screen] = []
        self._summary_writer = SummaryWriter(self.summary_file) if self.summary_file is not None else None

    def show_screen(self, win: Any, screen: Screen) -> None:
        """Present one screen and store its raw response row.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window used for drawing and flipping.
        screen : Screen
            Screen specification created by ``make_screen``.

        Returns
        -------
        None
            Appends one raw row to ``self.records``.
        """
        ctx = RunContext(
            win=win,
            timeline=self,
            params=self.params,
            state=self.state,
            row={},
            screen=screen,
            sync=self.sync,
        )
        self._prepare_screen_run(screen)
        if screen.run_if is not None and not bool(screen.run_if(ctx)):
            return None
        row = screen.run(win, screen_index=len(self.records), row={}, ctx=ctx)
        self._record_screen_row(row)
        self._run_pending_action_screens(win, base_row={}, record=True)

    def show_text_screen(
        self,
        win: Any,
        text: str,
        duration: Optional[float] = None,
        response: Optional[str] = "key",
        keys: Optional[Sequence[str]] = ("space",),
        **text_kwargs: Any,
    ) -> None:
        """Show a simple text instruction screen.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window used for drawing.
        text : str
            Text displayed at the center of the screen.
        duration : float, optional
            Maximum screen duration in seconds.
        response : str, optional
            Response mode passed to ``make_screen``.
        keys : sequence[str], optional
            Allowed keys for key response.
        **text_kwargs
            Extra arguments forwarded to ``psychopy.visual.TextStim``.

        Returns
        -------
        None
            Appends one raw row to ``self.records``.
        """
        visual = _load_psychopy_visual()
        text_stim = visual.TextStim(win, text=str(text), **text_kwargs)
        stim = wrap_stimulus(text_stim, label="text")
        screen = make_screen(stimuli=[stim], duration=duration, response=response, keys=keys, screen_name="text")
        self.show_screen(win, screen)

    def show_image_screen(
        self,
        win: Any,
        image: Any,
        duration: Optional[float] = None,
        response: Optional[str] = "key",
        keys: Optional[Sequence[str]] = ("space",),
        **image_kwargs: Any,
    ) -> None:
        """Show a simple image instruction screen.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window used for drawing.
        image : object
            Image source passed to ``psychopy.visual.ImageStim``.
        duration : float, optional
            Maximum screen duration in seconds.
        response : str, optional
            Response mode passed to ``make_screen``.
        keys : sequence[str], optional
            Allowed keys for key response.
        **image_kwargs
            Extra arguments forwarded to ``psychopy.visual.ImageStim``.

        Returns
        -------
        None
            Appends one raw row to ``self.records``.
        """
        visual = _load_psychopy_visual()
        image_stim = visual.ImageStim(win, image=str(image), **image_kwargs)
        stim = wrap_stimulus(image_stim, label="image")
        screen = make_screen(stimuli=[stim], duration=duration, response=response, keys=keys, screen_name="image")
        self.show_screen(win, screen)

    def run(
        self,
        win: Any,
        unit: Any,
        rows: Optional[Sequence[Dict[str, Any]]] = None,
        replace_on_reject: bool = False,
    ) -> None:
        """Run one screen or a trial over planned rows.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window.
        unit : Screen or Trial-like object
            Screen to show once, or trial object with ``run(timeline, win, row)``.
        rows : sequence[dict], optional
            Planned rows for trial execution.
        replace_on_reject : bool, optional
            Whether rejected trials should be retried within the same block.

        Returns
        -------
        None
            Writes rows and updates timeline state in place.
        """
        if isinstance(unit, Screen):
            self.show_screen(win, unit)
            return
        if rows is None:
            outcome = self._run_one_trial(unit, win, {})
            self._record_trial_outcome(outcome, {})
            return

        pending = [dict(row) for row in rows]
        while pending:
            row = pending.pop(0)
            outcome = self._run_one_trial(unit, win, row)
            self._record_trial_outcome(outcome, row)
            if outcome.is_rejected():
                if not replace_on_reject:
                    raise RuntimeError("Trial was rejected, but replace_on_reject is False.")
                self._insert_retry(pending, row)

    def get_data(self, kind: str = "raw", **filters: Any) -> DataRows:
        """Return completed rows matching field filters.

        Parameters
        ----------
        kind : str, optional
            ``"raw"`` for screen rows or ``"summary"`` for trial summaries.
        **filters
            Field values to match exactly.

        Returns
        -------
        DataRows
            Queryable row view.
        """
        rows = self.records if kind == "raw" else self.summary_records
        return DataRows(rows).filter(**filters)

    def get_last_data(self, kind: str = "raw", unit: str = "screen") -> DataRows:
        """Return the most recent completed screen, trial, block, or session.

        Parameters
        ----------
        kind : str, optional
            ``"raw"`` for screen rows or ``"summary"`` for trial summaries.
        unit : str, optional
            ``"screen"``, ``"trial"``, ``"block"``, or ``"session"``.

        Returns
        -------
        DataRows
            Rows from the latest requested unit, or an empty view when no rows
            exist.
        """
        rows = self.records if kind == "raw" else self.summary_records
        if not rows:
            return DataRows([])
        unit_name = str(unit).strip().lower()
        if unit_name == "screen":
            return DataRows([rows[-1]])
        if unit_name == "trial":
            return DataRows(_latest_rows_by_fields(rows, ["session_id", "block_id", "trial_id"]))
        if unit_name == "block":
            return DataRows(_latest_rows_by_fields(rows, ["session_id", "block_id"]))
        if unit_name == "session":
            return DataRows(_latest_rows_by_fields(rows, ["session_id"]))
        raise ValueError("unit must be 'screen', 'trial', 'block', or 'session'.")

    def handle_global_keys(self, ctx: RunContext, data: Dict[str, Any], event: Any) -> bool:
        """Apply a queued or polled researcher global-key action.

        Parameters
        ----------
        ctx : RunContext
            Current behavior runtime context.
        data : dict
            Mutable raw screen row for the current screen.
        event : psychopy.event module
            Event module used to poll function-key fallbacks.

        Returns
        -------
        bool
            ``True`` when the current screen should end after the action.
        """
        action = self._pop_queued_global_action()
        if action is None:
            action = self._poll_fallback_action(event)
        if action is None:
            return False

        for key, value in action.set_state.items():
            self.state[key] = value
        if action.action is not None:
            action.action(ctx)
        if action.screen is not None:
            self._pending_action_screens.append(action.screen)
        if action.record:
            data["global_key_action"] = action.name
        return bool(action.end_screen)

    def _prepare_screen_run(self, screen: Screen) -> None:
        """Validate response-key conflicts before one screen runs."""
        self._validate_global_key_conflicts(screen)

    def register_global_keys(self, event: Any) -> None:
        """Register modified shortcuts once for the current PsychoPy event module."""
        if not self._modified_shortcuts_registered:
            register_modified_shortcuts(event, self.global_actions, self._queue_global_action)
            self._modified_shortcuts_registered = True

    def _queue_global_action(self, action_name: str) -> None:
        """Queue one action from a PsychoPy globalKeys callback."""
        self.state["_tf_global_key_action"] = str(action_name)

    def _pop_queued_global_action(self) -> Optional[GlobalKeyAction]:
        """Return and clear the action queued by a modified shortcut."""
        action_name = self.state.pop("_tf_global_key_action", None)
        if action_name is None:
            return None
        return self._global_action_by_name.get(str(action_name))

    def _poll_fallback_action(self, event: Any) -> Optional[GlobalKeyAction]:
        """Poll unmodified function-key fallback actions."""
        if not self._fallback_actions:
            return None
        pressed = event.getKeys(keyList=sorted(self._fallback_actions.keys()))
        if not pressed:
            return None
        key = str(pressed[0]).strip().lower()
        return self._fallback_actions.get(key)

    def _validate_global_key_conflicts(self, screen: Screen) -> None:
        """Raise when participant responses overlap researcher fallback keys."""
        if screen.response != "key":
            return
        conflicts = find_response_key_conflicts(screen.keys, self.global_actions)
        if not conflicts:
            return
        raise ValueError(
            "participant response keys overlap with global researcher keys: "
            + ", ".join(conflicts)
            + ". Use different participant keys or disable default global actions."
        )

    def _run_pending_action_screens(
        self,
        win: Any,
        base_row: Dict[str, Any],
        record: bool = False,
        screen_index_start: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run screens requested by global-key actions.

        Parameters
        ----------
        win : psychopy.visual.Window
            Window used to show the follow-up screen.
        base_row : dict
            Trial/session fields inherited by the follow-up screen.
        record : bool, optional
            Whether rows should be saved immediately. Trial runs collect rows
            first and let ``_record_trial_outcome`` save them once.
        screen_index_start : int, optional
            Screen index assigned to the first follow-up screen.

        Returns
        -------
        list[dict]
            Raw rows produced by action-triggered screens.
        """
        rows = []
        while self._pending_action_screens:
            screen = self._pending_action_screens.pop(0)
            ctx = RunContext(
                win=win,
                timeline=self,
                params=self.params,
                state=self.state,
                row=dict(base_row),
                screen=screen,
                sync=self.sync,
            )
            self._prepare_screen_run(screen)
            if screen.run_if is not None and not bool(screen.run_if(ctx)):
                continue
            if screen_index_start is None:
                screen_index = len(self.records)
            else:
                screen_index = screen_index_start + len(rows)
            row = screen.run(win, screen_index=screen_index, row=base_row, ctx=ctx)
            if record:
                self._record_screen_row(row)
            rows.append(row)
        return rows

    def _run_one_trial(self, unit: Any, win: Any, row: Dict[str, Any]) -> TrialOutcome:
        """Run a trial-like unit and normalize its outcome.

        Parameters
        ----------
        unit : object
            ``Trial`` or object with ``run(timeline, win, row)``.
        win : psychopy.visual.Window
            Window used by the trial.
        row : dict
            Planned trial row.

        Returns
        -------
        TrialOutcome
            Normalized accepted or rejected trial outcome.
        """
        if isinstance(unit, Trial):
            return unit.run(self, win, row)
        outcome = unit.run(self, win, row)
        if isinstance(outcome, TrialOutcome):
            return outcome
        if isinstance(outcome, dict):
            return TrialOutcome(
                status=str(outcome.get("status", "accepted")),
                reason=str(outcome.get("reason", "no")),
                row=outcome.get("row"),
                screen_rows=list(outcome.get("screen_rows", [])),
                details=dict(outcome.get("details", {})),
            )
        raise TypeError("trial.run(...) must return a TrialOutcome or dictionary.")

    def _record_trial_outcome(self, outcome: TrialOutcome, planned_row: Dict[str, Any]) -> None:
        """Write raw and summary rows for one trial outcome.

        Parameters
        ----------
        outcome : TrialOutcome
            Trial result returned by the trial runner.
        planned_row : dict
            Planned row used for accepted-only completion tracking.

        Returns
        -------
        None
            Updates memory, optional files, and optional meta state.
        """
        rejected = outcome.is_rejected()
        for screen_row in outcome.screen_rows:
            row = dict(screen_row)
            row.setdefault("trial_status", "rejected" if rejected else "accepted")
            row.setdefault("rejection", outcome.reason if rejected else "no")
            self._record_screen_row(row)

        if outcome.row is not None:
            summary_row = dict(outcome.row)
            summary_row.setdefault("trial_status", "rejected" if rejected else "accepted")
            summary_row.setdefault("rejection", outcome.reason if rejected else "no")
            self._record_summary_row(summary_row)

        if not rejected:
            self._mark_completed(planned_row, outcome.row)

    def _record_screen_row(self, row: Dict[str, Any]) -> None:
        """Append one raw screen row to memory and optional JSONL output.

        Parameters
        ----------
        row : dict
            Completed screen row.

        Returns
        -------
        None
            Adds default sync containers and writes JSONL when configured.
        """
        out_row = dict(row)
        out_row.setdefault("markers", [])
        out_row.setdefault("messages", [])
        self.records.append(out_row)
        if self.raw_data_file is not None:
            append_jsonl(self.raw_data_file, out_row)

    def _record_summary_row(self, row: Dict[str, Any]) -> None:
        """Append one trial summary row to memory and optional CSV output.

        Parameters
        ----------
        row : dict
            Trial-level summary row.

        Returns
        -------
        None
            Stores the row and writes CSV when configured.
        """
        out_row = dict(row)
        self.summary_records.append(out_row)
        if self._summary_writer is not None:
            self._summary_writer.append(out_row)

    def _mark_completed(self, planned_row: Dict[str, Any], summary_row: Optional[Dict[str, Any]]) -> None:
        """Record an accepted trial's plan ID in meta state.

        Parameters
        ----------
        planned_row : dict
            Planned row that usually contains ``plan_id``.
        summary_row : dict, optional
            Summary row fallback when the planned row has no ``plan_id``.

        Returns
        -------
        None
            Updates and saves meta state when available.
        """
        plan_id = str(planned_row.get("plan_id", "") or "")
        if not plan_id and summary_row is not None:
            plan_id = str(summary_row.get("plan_id", "") or "")
        if not plan_id or self.meta_state is None:
            return
        mark_plan_completed(self.meta_state, plan_id)
        if self.meta_file is not None:
            save_meta_state(self.meta_file, self.meta_state)

    def _insert_retry(self, pending: List[Dict[str, Any]], trial_row: Dict[str, Any]) -> None:
        """Insert a rejected trial randomly within the current block.

        Parameters
        ----------
        pending : list[dict]
            Mutable list of remaining planned rows.
        trial_row : dict
            Rejected planned row to retry.

        Returns
        -------
        None
            Mutates ``pending`` in place.
        """
        block_id = trial_row.get("block_id")
        same_block_count = 0
        for pending_row in pending:
            if pending_row.get("block_id") != block_id:
                break
            same_block_count += 1
        if same_block_count == 0:
            pending.insert(0, dict(trial_row))
            return
        insert_idx = self.random.randint(0, same_block_count)
        pending.insert(insert_idx, dict(trial_row))


def setup_timeline(**kwargs: Any) -> Timeline:
    """Create a behavior timeline.

    Parameters
    ----------
    **kwargs
        Arguments forwarded to ``Timeline``.

    Returns
    -------
    Timeline
        Timeline with empty in-memory row lists.
    """
    return Timeline(**kwargs)


def _latest_rows_by_fields(rows: Sequence[Dict[str, Any]], fields: Sequence[str]) -> List[Dict[str, Any]]:
    """Return trailing rows that share the latest row's ID fields.

    Parameters
    ----------
    rows : sequence[dict]
        Completed rows in saved order.
    fields : sequence[str]
        Candidate ID fields for the requested unit.

    Returns
    -------
    list[dict]
        Copied rows from the latest contiguous unit.
    """
    latest = rows[-1]
    active_fields = [field for field in fields if field in latest]
    if not active_fields:
        return [dict(latest)]

    latest_key = tuple(latest.get(field) for field in active_fields)
    selected: List[Dict[str, Any]] = []
    for row in reversed(rows):
        row_key = tuple(row.get(field) for field in active_fields)
        if row_key != latest_key:
            break
        selected.append(dict(row))
    selected.reverse()
    return selected


def _attach_default_quit_screen(actions: Sequence[GlobalKeyAction]) -> None:
    """Attach the default Y/N quit confirmation screen to the quit action.

    Parameters
    ----------
    actions : sequence[GlobalKeyAction]
        Configured global actions created by ``make_default_global_actions``.

    Returns
    -------
    None
        Mutates the default ``quit_requested`` action in place.
    """
    for action in actions:
        if action.name == "quit_requested":
            action.screen = _make_quit_confirmation_screen()
            return


def _make_quit_confirmation_screen() -> Screen:
    """Create the default researcher quit-confirmation screen.

    Parameters
    ----------
    None

    Returns
    -------
    Screen
        Key-response screen that quits only after ``Y`` and clears the quit
        request after ``N``.
    """
    text_stim = _LazyTextStim("Are you sure you want to exit?")

    def prepare_text(ctx: RunContext, data: Dict[str, Any]) -> None:
        """Create the PsychoPy text stimulus once the window is available.

        Parameters
        ----------
        ctx : RunContext
            Current confirmation-screen context.
        data : dict
            Mutable raw row for the confirmation screen.

        Returns
        -------
        None
            Updates the lazy text drawable.
        """
        text_stim.setup(ctx.win)

    def finish_quit(ctx: RunContext, data: Dict[str, Any]) -> None:
        """Apply the researcher Y/N quit confirmation response.

        Parameters
        ----------
        ctx : RunContext
            Current confirmation-screen context.
        data : dict
            Raw row containing the researcher response.

        Returns
        -------
        None
            Quits after ``Y`` or clears the quit request after ``N``.
        """
        response = str(data.get("response") or "").lower()
        if response == "y":
            ctx.state["quit_confirmed"] = True
            _close_window_and_quit(ctx.win)
            return
        ctx.state["quit_requested"] = False
        ctx.state["quit_confirmed"] = False

    return make_screen(
        stimuli=[text_stim],
        response="key",
        keys=["y", "n"],
        screen_name="quit_confirmation",
        on_start=prepare_text,
        on_finish=finish_quit,
    )


class _LazyTextStim:
    """Small drawable that creates a PsychoPy TextStim at screen start.

    Parameters
    ----------
    text : str
        Researcher-facing text displayed on the confirmation screen.
    """

    def __init__(self, text: str) -> None:
        """Store text until a PsychoPy window exists.

        Parameters
        ----------
        text : str
            Text to draw after ``setup`` creates the real PsychoPy stimulus.

        Returns
        -------
        None
            Initializes an empty drawable placeholder.
        """
        self.text = str(text)
        self.drawable: Optional[Any] = None

    def setup(self, win: Any) -> None:
        """Create the underlying PsychoPy text stimulus.

        Parameters
        ----------
        win : psychopy.visual.Window
            Window used for the confirmation screen.

        Returns
        -------
        None
            Stores the real ``TextStim`` for later ``draw`` calls.
        """
        visual = _load_psychopy_visual()
        self.drawable = visual.TextStim(win, text=self.text)

    def draw(self) -> None:
        """Draw the underlying text stimulus when it has been created.

        Parameters
        ----------
        None

        Returns
        -------
        None
            Draws nothing before ``setup`` runs.
        """
        if self.drawable is not None:
            self.drawable.draw()


def _close_window_and_quit(win: Any) -> None:
    """Close the PsychoPy window and quit after confirmed researcher exit.

    Parameters
    ----------
    win : psychopy.visual.Window
        Window to close after an explicit researcher ``Y`` response.

    Returns
    -------
    None
        Calls PsychoPy ``core.quit()``, which normally raises ``SystemExit``.
    """
    if hasattr(win, "saveFrameIntervals") and callable(win.saveFrameIntervals):
        win.saveFrameIntervals()
    if hasattr(win, "close") and callable(win.close):
        win.close()
    core = _psychopy.load_core()
    core.quit()


def _load_psychopy_visual() -> Any:
    """Import ``psychopy.visual`` only when convenience screens need it."""
    return _psychopy.load_visual()

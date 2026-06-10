"""Timeline runtime, factories, and data bookkeeping."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from .. import _psychopy
from ..data import DataRows, SummaryWriter, append_jsonl
from ..keys import (
    GlobalKeyAction,
    coerce_global_actions,
    fallback_key_map,
    find_response_key_conflicts,
    register_modified_shortcuts,
)
from ..recovery import mark_plan_completed, save_meta_state
from ..stimuli import wrap_stimulus
from ...sync import SyncController
from .context import RunContext, TrialOutcome
from .screen import Screen, _make_screen
from .trial import _Trial


class Timeline:
    """Behavior timeline with runtime factories, state, and output bookkeeping.

    Parameters
    ----------
    win : object, optional
        PsychoPy window used by screens created and run through this timeline.
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
    >>> timeline = Timeline(win=win, seed=1)
    >>> screen = timeline.make_screen(stimuli=[fix], duration=0.5)
    >>> timeline.run(screen, trial_data={"condition": "practice"})
    """

    def __init__(
        self,
        win: Optional[Any] = None,
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
        self.win = win
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

    def make_screen(
        self,
        stimuli: Sequence[Any],
        duration: Optional[float] = None,
        response: Optional[str] = None,
        keys: Optional[Sequence[str]] = None,
        choices: Optional[Any] = None,
        response_start: float = 0,
        end_on_response: bool = True,
        clear_events: bool = True,
        data: Optional[Dict[str, Any]] = None,
        on_start: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_load: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_response: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_finish: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
    ) -> Screen:
        """Create one screen owned by this timeline's runtime context.

        Parameters
        ----------
        stimuli : sequence
            Stimulus-like objects with ``draw()``. Objects with
            ``is_visible(elapsed)`` may control their own screen-relative
            visibility.
        duration : float, optional
            Maximum screen duration in seconds. ``None`` means the screen must
            end through a response.
        response : str, optional
            Response mode. Use ``None`` for no built-in response collection or
            ``"key"`` for keyboard responses.
        keys : sequence[str], optional
            Allowed keyboard responses when ``response="key"``. ``None``
            accepts any key.
        choices : object, optional
            Reserved for future button/clickable responses. Passing a value
            currently raises ``ValueError``.
        response_start : float, optional
            Seconds after screen onset before key responses are accepted.
        end_on_response : bool, optional
            Whether the screen ends immediately after the first accepted
            response.
        clear_events : bool, optional
            Whether keyboard events are cleared before the screen starts.
        data : dict, optional
            Static screen-level fields copied into each raw screen row.
        on_start, on_load, on_response, on_finish : callable, optional
            Lifecycle hooks receiving ``(ctx, data)``. ``data`` is the mutable
            raw screen row. ``on_load`` runs after the first flip, and
            ``on_response`` runs after the first accepted response.

        Returns
        -------
        Screen
            Screen that can be passed to ``timeline.run(...)`` or
            ``timeline.make_trial(screens=[...])``.
        """
        return _make_screen(
            stimuli=stimuli,
            duration=duration,
            response=response,
            keys=keys,
            choices=choices,
            response_start=response_start,
            end_on_response=end_on_response,
            clear_events=clear_events,
            data=data,
            on_start=on_start,
            on_load=on_load,
            on_response=on_response,
            on_finish=on_finish,
        )

    def make_text_screen(
        self,
        text: str,
        duration: Optional[float] = None,
        response: Optional[str] = "key",
        keys: Optional[Sequence[str]] = ("space",),
        data: Optional[Dict[str, Any]] = None,
        **text_kwargs: Any,
    ) -> Screen:
        """Create a text screen without running it.

        Parameters
        ----------
        text : str
            Text displayed by the PsychoPy ``TextStim``.
        duration : float, optional
            Maximum screen duration in seconds. ``None`` means the screen must
            end through a response.
        response : str, optional
            Response mode forwarded to ``make_screen``. Defaults to ``"key"``.
        keys : sequence[str], optional
            Allowed keyboard responses. Defaults to ``("space",)``.
        data : dict, optional
            Screen-level fields copied into each raw row. Defaults to
            ``{"screen_name": "text"}``.
        **text_kwargs
            Additional keyword arguments forwarded to
            ``psychopy.visual.TextStim``.

        Returns
        -------
        Screen
            Text screen that writes data only when run through the timeline.
        """
        win = self._require_window()
        visual = _load_psychopy_visual()
        text_stim = visual.TextStim(win, text=str(text), **text_kwargs)
        stim = wrap_stimulus(text_stim, label="text")
        screen_data = {"screen_name": "text", **dict(data or {})}
        return self.make_screen(stimuli=[stim], duration=duration, response=response, keys=keys, data=screen_data)

    def make_image_screen(
        self,
        image: Any,
        duration: Optional[float] = None,
        response: Optional[str] = "key",
        keys: Optional[Sequence[str]] = ("space",),
        data: Optional[Dict[str, Any]] = None,
        **image_kwargs: Any,
    ) -> Screen:
        """Create an image screen without running it.

        Parameters
        ----------
        image : object
            Image path or image object forwarded to ``psychopy.visual.ImageStim``.
        duration : float, optional
            Maximum screen duration in seconds. ``None`` means the screen must
            end through a response.
        response : str, optional
            Response mode forwarded to ``make_screen``. Defaults to ``"key"``.
        keys : sequence[str], optional
            Allowed keyboard responses. Defaults to ``("space",)``.
        data : dict, optional
            Screen-level fields copied into each raw row. Defaults to
            ``{"screen_name": "image"}``.
        **image_kwargs
            Additional keyword arguments forwarded to
            ``psychopy.visual.ImageStim``.

        Returns
        -------
        Screen
            Image screen that writes data only when run through the timeline.
        """
        win = self._require_window()
        visual = _load_psychopy_visual()
        image_stim = visual.ImageStim(win, image=str(image), **image_kwargs)
        stim = wrap_stimulus(image_stim, label="image")
        screen_data = {"screen_name": "image", **dict(data or {})}
        return self.make_screen(stimuli=[stim], duration=duration, response=response, keys=keys, data=screen_data)

    def make_trial(
        self,
        screens: Sequence[Any],
        data_format: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
        run_if: Optional[Callable[[RunContext], bool]] = None,
    ) -> Any:
        """Create one ordered screen group in presentation order.

        Parameters
        ----------
        screens : sequence
            Screens to run in order for each trial-data dictionary.
        data_format : callable, optional
            Function that receives one trial's raw screen rows and returns one
            summary row.
        run_if : callable, optional
            Predicate receiving ``RunContext``. When it returns ``False``, the
            entire trial is skipped, no raw rows are saved, and the trial is
            treated as accepted for completion tracking.

        Returns
        -------
        object
            Timeline-owned trial-like object that can be passed to
            ``timeline.run(...)``.
        """
        return _Trial(screens=screens, data_format=data_format, run_if=run_if)

    def run(
        self,
        unit: Any,
        trial_data: Optional[Any] = None,
        replace_on_reject: bool = False,
    ) -> None:
        """Run one screen, trial-like object, or unit sequence over trial data.

        Parameters
        ----------
        unit : Screen or trial-like object
            Screen, object with ``run(ctx)``, or a sequence of units. A screen
            is run as a one-screen trial.
        trial_data : dict or sequence[dict], optional
            ``None`` runs once with empty data. A dictionary runs once and is
            copied into every screen row. A sequence of dictionaries runs once
            per dictionary.
        replace_on_reject : bool, optional
            Whether rejected trials should be retried within the same block.

        Returns
        -------
        None
            Writes rows and updates timeline state in place.
        """
        self._require_window()
        if _is_unit_sequence(unit):
            for item in unit:
                self.run(item, trial_data=trial_data, replace_on_reject=replace_on_reject)
            return

        trial = self._coerce_trial_unit(unit)
        if trial_data is None:
            data_items = [{}]
        elif isinstance(trial_data, dict):
            data_items = [dict(trial_data)]
        else:
            data_items = [dict(item) for item in trial_data]

        pending = data_items
        while pending:
            data = pending.pop(0)
            outcome = self._run_one_trial(trial, data)
            self._record_trial_outcome(outcome, data)
            if outcome.is_rejected():
                if not replace_on_reject:
                    raise RuntimeError("Trial was rejected, but replace_on_reject is False.")
                self._insert_retry(pending, data)

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
        """Apply a queued or polled researcher global-key action."""
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
        ctx: RunContext,
        record: bool = False,
        screen_index_start: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run screens requested by global-key actions."""
        rows = []
        while self._pending_action_screens:
            screen = self._pending_action_screens.pop(0)
            screen_ctx = RunContext(
                win=ctx.win,
                timeline=self,
                trial_data=dict(ctx.trial_data),
                params=self.params,
                state=self.state,
                screen=screen,
                sync=self.sync,
            )
            self._prepare_screen_run(screen)
            if screen_index_start is None:
                screen_index = len(self.records)
            else:
                screen_index = screen_index_start + len(rows)
            row = screen.run(ctx.win, screen_index=screen_index, row=screen_ctx.trial_data, ctx=screen_ctx)
            if record:
                self._record_screen_row(row)
            rows.append(row)
        return rows

    def _run_one_trial(self, unit: Any, trial_data: Dict[str, Any]) -> TrialOutcome:
        """Run a trial-like unit and normalize its outcome."""
        ctx = self._make_run_context(trial_data)
        outcome = unit.run(ctx)
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
        raise TypeError("trial.run(ctx) must return a TrialOutcome or dictionary.")

    def _make_run_context(self, trial_data: Dict[str, Any]) -> RunContext:
        """Create the runtime context for one trial run."""
        return RunContext(
            win=self._require_window(),
            timeline=self,
            trial_data=dict(trial_data),
            params=self.params,
            state=self.state,
            sync=self.sync,
        )

    def _coerce_trial_unit(self, unit: Any) -> Any:
        """Return a trial-like object with ``run(ctx)``."""
        if isinstance(unit, Screen):
            return self.make_trial(screens=[unit])
        if isinstance(unit, _Trial):
            return unit
        if hasattr(unit, "run") and callable(unit.run):
            return unit
        raise TypeError("unit must be a Screen, trial-like object, or sequence of those units.")

    def _require_window(self) -> Any:
        """Return the configured PsychoPy window or raise a clear error."""
        if self.win is None:
            raise RuntimeError("Timeline requires win=. Create it with setup_timeline(win=win).")
        return self.win

    def _record_trial_outcome(self, outcome: TrialOutcome, planned_row: Dict[str, Any]) -> None:
        """Write raw and summary rows for one trial outcome."""
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
        """Append one raw screen row to memory and optional JSONL output."""
        out_row = dict(row)
        out_row.setdefault("markers", [])
        out_row.setdefault("messages", [])
        self.records.append(out_row)
        if self.raw_data_file is not None:
            append_jsonl(self.raw_data_file, out_row)

    def _record_summary_row(self, row: Dict[str, Any]) -> None:
        """Append one trial summary row to memory and optional CSV output."""
        out_row = dict(row)
        self.summary_records.append(out_row)
        if self._summary_writer is not None:
            self._summary_writer.append(out_row)

    def _mark_completed(self, planned_row: Dict[str, Any], summary_row: Optional[Dict[str, Any]]) -> None:
        """Record an accepted trial's plan ID in meta state."""
        plan_id = str(planned_row.get("plan_id", "") or "")
        if not plan_id and summary_row is not None:
            plan_id = str(summary_row.get("plan_id", "") or "")
        if not plan_id or self.meta_state is None:
            return
        mark_plan_completed(self.meta_state, plan_id)
        if self.meta_file is not None:
            save_meta_state(self.meta_file, self.meta_state)

    def _insert_retry(self, pending: List[Dict[str, Any]], trial_row: Dict[str, Any]) -> None:
        """Insert a rejected trial randomly within the current block."""
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


def _is_unit_sequence(unit: Any) -> bool:
    """Return whether ``unit`` is a sequence of runnable timeline units."""
    if isinstance(unit, (Screen, _Trial, str, bytes, dict)):
        return False
    return isinstance(unit, Sequence)


def _latest_rows_by_fields(rows: Sequence[Dict[str, Any]], fields: Sequence[str]) -> List[Dict[str, Any]]:
    """Return trailing rows that share the latest row's ID fields."""
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
    """Attach the default Y/N quit confirmation screen to the quit action."""
    for action in actions:
        if action.name == "quit_requested":
            action.screen = _make_quit_confirmation_screen()
            return


def _make_quit_confirmation_screen() -> Screen:
    """Create the default researcher quit-confirmation screen."""
    text_stim = _LazyTextStim("Are you sure you want to exit?")

    def prepare_text(ctx: RunContext, data: Dict[str, Any]) -> None:
        """Create the PsychoPy text stimulus once the window is available."""
        text_stim.setup(ctx.win)

    def finish_quit(ctx: RunContext, data: Dict[str, Any]) -> None:
        """Apply the researcher Y/N quit confirmation response."""
        response = str(data.get("response") or "").lower()
        if response == "y":
            ctx.state["quit_confirmed"] = True
            _close_window_and_quit(ctx.win)
            return
        ctx.state["quit_requested"] = False
        ctx.state["quit_confirmed"] = False

    return _make_screen(
        stimuli=[text_stim],
        response="key",
        keys=["y", "n"],
        data={"screen_name": "quit_confirmation"},
        on_start=prepare_text,
        on_finish=finish_quit,
    )


class _LazyTextStim:
    """Small drawable that creates a PsychoPy TextStim at screen start."""

    def __init__(self, text: str) -> None:
        """Store text until a PsychoPy window exists."""
        self.text = str(text)
        self.drawable: Optional[Any] = None

    def setup(self, win: Any) -> None:
        """Create the underlying PsychoPy text stimulus."""
        visual = _load_psychopy_visual()
        self.drawable = visual.TextStim(win, text=self.text)

    def draw(self) -> None:
        """Draw the underlying text stimulus when it has been created."""
        if self.drawable is not None:
            self.drawable.draw()


def _close_window_and_quit(win: Any) -> None:
    """Close the PsychoPy window and quit after confirmed researcher exit."""
    if hasattr(win, "saveFrameIntervals") and callable(win.saveFrameIntervals):
        win.saveFrameIntervals()
    if hasattr(win, "close") and callable(win.close):
        win.close()
    core = _psychopy.load_core()
    core.quit()


def _load_psychopy_visual() -> Any:
    """Import ``psychopy.visual`` only when convenience screens need it."""
    return _psychopy.load_visual()

"""Timeline runtime, factories, and data bookkeeping."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from .. import _psychopy
from ..data import DataCollection, SummaryWriter, append_jsonl
from ..keys import (
    DEFAULT_QUIT_KEYS,
    QUIT_REQUEST_NAME,
    _KeyBinding,
    build_request_bindings,
    fallback_key_map,
    find_response_key_conflicts,
    register_modified_shortcuts,
)
from ..recovery import mark_plan_completed, save_meta_state
from ..stimuli import wrap_stimulus
from .context import RunContext, TrackerRuntime, TrialOutcome
from .screen import Screen, _make_screen
from .sync import send_eeg, send_gaze
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
    eeg, tracker : object, optional
        Configured EEG sender and EyeLink tracker used by ``ctx.send(...)``.
    enable_quit_keys : bool, optional
        Whether trackflow's locked quit keys are active.
    quit_keys : sequence[str], optional
        Researcher quit shortcuts. These always use the built-in quit
        confirmation screen.
    global_key_requests : mapping, optional
        Deferred request shortcuts as ``state_name -> key list``. Pressing a
        request key sets ``timeline.state[state_name] = True``.

    Examples
    --------
    >>> timeline = Timeline(win=win)
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
        eeg: Optional[Any] = None,
        tracker: Optional[Any] = None,
        enable_quit_keys: bool = True,
        quit_keys: Optional[Sequence[str]] = None,
        global_key_requests: Optional[Dict[str, Sequence[str]]] = None,
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
        self.eeg = eeg
        self.tracker = tracker
        self.enable_quit_keys = bool(enable_quit_keys)
        self._quit_binding = (
            _KeyBinding(QUIT_REQUEST_NAME, list(quit_keys or DEFAULT_QUIT_KEYS))
            if self.enable_quit_keys
            else None
        )
        self._request_bindings = build_request_bindings(global_key_requests)
        self._global_bindings = self._build_global_bindings()
        self._request_names = {binding.name for binding in self._request_bindings}
        self._fallback_actions = fallback_key_map(self._global_bindings)
        self._modified_shortcuts_registered = False
        self._pending_system_rows: List[Dict[str, Any]] = []
        self._summary_writer = SummaryWriter(self.summary_file) if self.summary_file is not None else None

    def make_screen(
        self,
        stimuli: Sequence[Any],
        duration: Optional[float] = None,
        response: Optional[str] = "key",
        choices: Optional[Sequence[str]] = None,
        response_start: float = 0,
        end_on_response: bool = True,
        clear_events: bool = True,
        data: Optional[Dict[str, Any]] = None,
        on_start: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_load: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_frame: Optional[Callable[[Any, Dict[str, Any], float], None]] = None,
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
            ``"key"`` for keyboard responses. Defaults to ``"key"``.
        choices : sequence[str], optional
            Allowed response choices for the selected response mode. For
            ``response="key"``, these are PsychoPy key names. ``None`` accepts
            no participant response choices.
        response_start : float, optional
            Seconds after screen onset before key responses are accepted.
        end_on_response : bool, optional
            Whether the screen ends immediately after the first accepted
            response.
        clear_events : bool, optional
            Whether keyboard events are cleared before the screen starts.
        data : dict, optional
            Static screen-level fields copied into each raw screen row.
        on_start, on_load, on_frame, on_finish : callable, optional
            Lifecycle hooks. Hooks may receive only ``ctx`` for concise
            context-owned actions such as ``ctx.send(...)``. They may also
            receive the mutable row as ``(ctx, data)``; ``on_frame`` may
            receive elapsed time as ``(ctx, data, elapsed)``.

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
            choices=choices,
            response_start=response_start,
            end_on_response=end_on_response,
            clear_events=clear_events,
            data=data,
            on_start=on_start,
            on_load=on_load,
            on_frame=on_frame,
            on_finish=on_finish,
        )

    def make_text_screen(
        self,
        text: str,
        duration: Optional[float] = None,
        response: Optional[str] = "key",
        choices: Optional[Sequence[str]] = None,
        response_start: float = 0,
        end_on_response: bool = True,
        clear_events: bool = True,
        data: Optional[Dict[str, Any]] = None,
        on_start: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_load: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_frame: Optional[Callable[[Any, Dict[str, Any], float], None]] = None,
        on_finish: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        prompt_text: Optional[str] = None,
        text_kwargs: Optional[Dict[str, Any]] = None,
        prompt_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Screen:
        """Create a text screen without running it.

        Parameters
        ----------
        text : str
            Text displayed by the PsychoPy ``TextStim``.
        duration, response, choices, response_start, end_on_response, clear_events,
        data, on_start, on_load, on_frame, on_finish : optional
            Arguments used in ``make_screen(...)`` can also be used in this
            function. ``data`` defaults to ``{"screen_name": "text"}``.
        prompt_text : str, optional
            Optional prompt shown near the bottom of the screen.
        text_kwargs : dict, optional
            Keyword arguments forwarded to the main ``psychopy.visual.TextStim``.
        prompt_kwargs : dict, optional
            Keyword arguments forwarded to the prompt ``TextStim``.

        Returns
        -------
        Screen
            Text screen that writes data only when run through the timeline.
        """
        win = self._require_window()
        visual = _load_psychopy_visual()
        text_stim = visual.TextStim(win, text=str(text), **_default_text_kwargs(text_kwargs))
        stimuli = _make_instruction_stimuli(
            visual,
            win,
            wrap_stimulus(text_stim, label="text"),
            prompt_text,
            prompt_kwargs,
        )
        screen_kwargs = _screen_kwargs(locals(), screen_name="text")
        return self.make_screen(stimuli=stimuli, **screen_kwargs)

    def make_image_screen(
        self,
        image: Any,
        duration: Optional[float] = None,
        response: Optional[str] = "key",
        choices: Optional[Sequence[str]] = None,
        response_start: float = 0,
        end_on_response: bool = True,
        clear_events: bool = True,
        data: Optional[Dict[str, Any]] = None,
        on_start: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_load: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_frame: Optional[Callable[[Any, Dict[str, Any], float], None]] = None,
        on_finish: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        prompt_text: Optional[str] = None,
        image_kwargs: Optional[Dict[str, Any]] = None,
        prompt_kwargs: Optional[Dict[str, Any]] = None,
        image_units: str = "pix",
        image_size: Optional[Sequence[float]] = None,
        scale: Union[float, str] = 1.0,
        pos: Sequence[float] = (0, 0),
    ) -> Screen:
        """Create an image screen without running it.

        Parameters
        ----------
        image : object
            Image path or image object forwarded to ``psychopy.visual.ImageStim``.
        duration, response, choices, response_start, end_on_response, clear_events,
        data, on_start, on_load, on_frame, on_finish : optional
            Arguments used in ``make_screen(...)`` can also be used in this
            function. ``data`` defaults to ``{"screen_name": "image"}``.
        prompt_text : str, optional
            Optional prompt shown near the bottom of the screen.
        image_kwargs : dict, optional
            Keyword arguments forwarded to ``psychopy.visual.ImageStim``.
        prompt_kwargs : dict, optional
            Keyword arguments forwarded to the prompt ``TextStim``.
        image_units : str, optional
            Units used for image position and size. Defaults to ``"pix"``.
        image_size : sequence, optional
            Optional image size forwarded to ``ImageStim(size=...)``.
        scale : float or "auto", optional
            Positive image scale factor. Use ``"auto"`` to fit the image to
            the window while preserving its aspect ratio.
        pos : sequence, optional
            Image position in ``image_units``.

        Returns
        -------
        Screen
            Image screen that writes data only when run through the timeline.
        """
        win = self._require_window()
        visual = _load_psychopy_visual()
        image_stim = visual.ImageStim(
            win,
            image=str(image),
            **_image_stim_kwargs(
                image_kwargs=image_kwargs,
                image_units=image_units,
                image_size=image_size,
                pos=pos,
                scale=scale,
            ),
        )
        _apply_image_scale(image_stim, win, scale)
        stimuli = _make_instruction_stimuli(
            visual,
            win,
            wrap_stimulus(image_stim, label="image"),
            prompt_text,
            prompt_kwargs,
        )
        screen_kwargs = _screen_kwargs(locals(), screen_name="image")
        return self.make_screen(stimuli=stimuli, **screen_kwargs)

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
        record: bool = True,
        return_status: bool = False,
    ) -> Optional[bool]:
        """Run one screen or trial-like object over one trial-data dictionary.

        Parameters
        ----------
        unit : Screen or trial-like object
            Screen or object with ``run(ctx)``. A screen is run as a one-screen
            trial.
        trial_data : dict, optional
            Data copied into every screen row for this one run. Use an explicit
            Python loop to run multiple planned rows.
        record : bool, optional
            Whether to append raw rows, summary rows, and recovery completion
            state. Use ``False`` for timeline-owned screens that should run
            with timeline context but not be saved, such as break screens.
        return_status : bool, optional
            Whether to return ``True`` for accepted/completed trials and
            ``False`` for rejected or interrupted trials. When ``False``, this
            method returns ``None`` after recording side effects.

        Returns
        -------
        bool or None
            Optional completion status when ``return_status=True``.
        """
        self._require_window()
        if _is_unit_sequence(unit):
            raise TypeError("timeline.run() accepts one screen or trial-like object. Loop over units explicitly.")

        trial = self._coerce_trial_unit(unit)
        if trial_data is None:
            data = {}
        elif isinstance(trial_data, dict):
            data = dict(trial_data)
        else:
            raise TypeError("trial_data must be one dictionary or None. Loop over planned trial-data rows explicitly.")

        outcome = self._run_one_trial(trial, data)
        if record:
            self._record_trial_outcome(outcome, data)
        complete = outcome.is_complete()
        if return_status:
            return complete
        return None

    def get_data(self, kind: str = "raw", **filters: Any) -> DataCollection:
        """Return completed rows matching field filters.

        Parameters
        ----------
        kind : str, optional
            ``"raw"`` for screen rows or ``"summary"`` for trial summaries.
        **filters
            Field values to match exactly.

        Returns
        -------
        DataCollection
            Queryable row view.
        """
        rows = self.records if kind == "raw" else self.summary_records
        return DataCollection(rows).filter(**filters)

    @property
    def code(self) -> Dict[str, int]:
        """Return the configured EEG code dictionary."""
        return dict(getattr(self.eeg, "code", {}) or {})

    def send(self, code: Optional[int] = None, message: Optional[str] = None) -> None:
        """Send one EEG marker and/or EyeLink message.

        Parameters
        ----------
        code : int, optional
            EEG marker code to send.
        message : str, optional
            EyeLink message text to send.

        Returns
        -------
        None
            Sends hardware side effects only. This method does not create data
            rows or write marker/message fields.
        """
        if code is None and message is None:
            raise ValueError("timeline.send(...) requires code, message, or both.")
        if code is not None:
            self.send_eeg(code)
        if message is not None:
            self.send_gaze(str(message))
        return None

    def send_eeg(self, code: int) -> None:
        """Send one EEG marker through the configured sender."""
        send_eeg(self.eeg, self.state, code)
        return None

    def send_gaze(self, message: str) -> None:
        """Send one EyeLink message through the configured tracker."""
        send_gaze(self.tracker, self.state, str(message))
        return None

    def get_last_data(self, kind: str = "raw", unit: str = "screen") -> DataCollection:
        """Return the most recent completed screen, trial, block, or session.

        Parameters
        ----------
        kind : str, optional
            ``"raw"`` for screen rows or ``"summary"`` for trial summaries.
        unit : str, optional
            ``"screen"``, ``"trial"``, ``"block"``, or ``"session"``.

        Returns
        -------
        DataCollection
            Rows from the latest requested unit, or an empty view when no rows
            exist.
        """
        rows = self.records if kind == "raw" else self.summary_records
        if not rows:
            return DataCollection([])
        unit_name = str(unit).strip().lower()
        if unit_name == "screen":
            return DataCollection([rows[-1]])
        if unit_name == "trial":
            return DataCollection(_latest_rows_by_fields(rows, ["session_id", "block_id", "trial_id"]))
        if unit_name == "block":
            return DataCollection(_latest_rows_by_fields(rows, ["session_id", "block_id"]))
        if unit_name == "session":
            return DataCollection(_latest_rows_by_fields(rows, ["session_id"]))
        raise ValueError("unit must be 'screen', 'trial', 'block', or 'session'.")

    def handle_global_keys(self, ctx: RunContext, data: Dict[str, Any], event: Any) -> bool:
        """Apply a queued or polled researcher global-key binding."""
        action_name = self._pop_queued_global_action()
        if action_name is None:
            action_name = self._poll_fallback_action(event)
        if action_name is None:
            return False

        data["global_key_action"] = action_name
        if action_name == QUIT_REQUEST_NAME:
            self.state[QUIT_REQUEST_NAME] = True
            self._pending_system_rows.append(self._run_quit_confirmation(ctx))
            return True
        if action_name in self._request_names:
            self.state[action_name] = True
            return False
        return False

    def _prepare_screen_run(self, screen: Screen) -> None:
        """Validate response-key conflicts before one screen runs."""
        self._validate_global_key_conflicts(screen)

    def register_global_keys(self, event: Any) -> None:
        """Register modified shortcuts once for the current PsychoPy event module."""
        if not self._modified_shortcuts_registered:
            register_modified_shortcuts(event, self._global_bindings, self._queue_global_action)
            self._modified_shortcuts_registered = True

    def _queue_global_action(self, action_name: str) -> None:
        """Queue one action from a PsychoPy globalKeys callback."""
        self.state["_tf_global_key_action"] = str(action_name)

    def _pop_queued_global_action(self) -> Optional[str]:
        """Return and clear the action name queued by a modified shortcut."""
        action_name = self.state.pop("_tf_global_key_action", None)
        if action_name is None:
            return None
        action_name = str(action_name)
        if action_name == QUIT_REQUEST_NAME or action_name in self._request_names:
            return action_name
        return None

    def _poll_fallback_action(self, event: Any) -> Optional[str]:
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
        conflicts = find_response_key_conflicts(screen.choices, self._global_bindings)
        if not conflicts:
            return
        raise ValueError(
            "participant response choices overlap with global researcher keys: "
            + ", ".join(conflicts)
            + ". Use different participant choices or disable default global actions."
        )

    def _run_feedback_screen(self, ctx: RunContext, screen: Screen) -> Dict[str, Any]:
        """Run one immediate feedback screen without recording it as trial data."""
        screen_ctx = RunContext(
            win=ctx.win,
            timeline=self,
            trial_data=dict(ctx.trial_data),
            params=self.params,
            state=self.state,
            tracker=TrackerRuntime(self.tracker),
            screen=screen,
        )
        self._prepare_screen_run(screen)
        return screen.run(ctx.win, screen_index=0, row=screen_ctx.trial_data, ctx=screen_ctx)

    def _run_quit_confirmation(self, ctx: RunContext) -> Dict[str, Any]:
        """Run the built-in quit confirmation screen."""
        return self._run_feedback_screen(ctx, _make_quit_confirmation_screen())

    def _pop_pending_system_rows(self) -> List[Dict[str, Any]]:
        """Return and clear rows produced by built-in system key flows."""
        rows = [dict(row) for row in self._pending_system_rows]
        self._pending_system_rows = []
        return rows

    def _build_global_bindings(self) -> List[_KeyBinding]:
        """Return quit and request bindings in polling/registration order."""
        bindings: List[_KeyBinding] = []
        if self._quit_binding is not None:
            bindings.append(self._quit_binding)
        bindings.extend(self._request_bindings)
        return bindings

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
            tracker=TrackerRuntime(self.tracker),
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
        complete = outcome.is_complete()
        status = _normalize_outcome_status(outcome.status)
        for screen_row in outcome.screen_rows:
            row = dict(screen_row)
            if status == "interrupted":
                row.setdefault("status", "interrupted")
            self._record_screen_row(row)

        if outcome.row is not None:
            summary_row = dict(outcome.row)
            self._record_summary_row(summary_row)

        if complete:
            self._mark_completed(planned_row, outcome.row)

    def _record_screen_row(self, row: Dict[str, Any]) -> None:
        """Append one raw screen row to memory and optional JSONL output."""
        out_row = dict(row)
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


def _normalize_outcome_status(status: Any) -> str:
    """Return a supported trial status label."""
    status_text = str(status or "accepted").strip().lower()
    if status_text in {"accepted", "rejected", "interrupted"}:
        return status_text
    return status_text or "accepted"


def _make_quit_confirmation_screen() -> Screen:
    """Create the default researcher quit-confirmation screen."""
    text_stim = _LazyTextStim("Are you sure you want to exit?")

    def prepare_text(ctx: RunContext, data: Dict[str, Any]) -> None:
        """Create the PsychoPy text stimulus once the window is available."""
        text_stim.setup(ctx.win)

    def finish_quit(ctx: RunContext, data: Dict[str, Any]) -> None:
        """Apply the researcher Y/N quit confirmation response."""
        response = str(data.get("response_value") or "").lower()
        if response == "y":
            ctx.state["quit_confirmed"] = True
            _close_window_and_quit(ctx.win)
            return
        ctx.state["quit_requested"] = False
        ctx.state["quit_confirmed"] = False

    return _make_screen(
        stimuli=[text_stim],
        response="key",
        choices=["y", "n"],
        data={"screen_name": "quit_confirmation"},
        on_start=prepare_text,
        on_finish=finish_quit,
    )


_SCREEN_KWARG_NAMES = (
    "duration",
    "response",
    "choices",
    "response_start",
    "end_on_response",
    "clear_events",
    "data",
    "on_start",
    "on_load",
    "on_frame",
    "on_finish",
)


def _screen_kwargs(arguments: Dict[str, Any], screen_name: str) -> Dict[str, Any]:
    """Collect arguments shared with ``Timeline.make_screen``."""
    kwargs = {name: arguments[name] for name in _SCREEN_KWARG_NAMES}
    kwargs["data"] = {"screen_name": screen_name, **dict(arguments.get("data") or {})}
    return kwargs


def _make_instruction_stimuli(
    visual: Any,
    win: Any,
    main_stimulus: Any,
    prompt_text: Optional[str],
    prompt_kwargs: Optional[Dict[str, Any]],
) -> List[Any]:
    """Return the main instruction stimulus plus an optional prompt."""
    stimuli = [main_stimulus]
    prompt_stim = _make_prompt_stimulus(visual, win, prompt_text, prompt_kwargs)
    if prompt_stim is not None:
        stimuli.append(prompt_stim)
    return stimuli


def _make_prompt_stimulus(
    visual: Any,
    win: Any,
    prompt_text: Optional[str],
    prompt_kwargs: Optional[Dict[str, Any]],
) -> Optional[Any]:
    """Return an optional bottom prompt stimulus wrapped for screen drawing."""
    if prompt_text is None:
        return None
    text = str(prompt_text)
    if not text:
        return None
    kwargs: Dict[str, Any] = {
        "color": "#000000",
        "colorSpace": "hex",
        "units": "height",
        "height": 0.03,
        "pos": (0.0, -0.45),
        "alignHoriz": "center",
        "alignVert": "center",
        "wrapWidth": 1.6,
    }
    kwargs.update(dict(prompt_kwargs or {}))
    prompt = visual.TextStim(win, text=text, **kwargs)
    return wrap_stimulus(prompt, label="prompt")


def _default_text_kwargs(text_kwargs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return relative-unit defaults for timeline-owned text screens."""
    kwargs: Dict[str, Any] = {
        "color": "#000000",
        "colorSpace": "hex",
        "units": "height",
        "height": 0.033,
        "alignHoriz": "center",
        "alignVert": "center",
        "wrapWidth": 1.6,
    }
    kwargs.update(dict(text_kwargs or {}))
    return kwargs


def _image_stim_kwargs(
    image_kwargs: Optional[Dict[str, Any]],
    image_units: str,
    image_size: Optional[Sequence[float]],
    pos: Sequence[float],
    scale: Union[float, str],
) -> Dict[str, Any]:
    """Return ImageStim kwargs with explicit image screen defaults."""
    _validate_image_scale(scale)
    kwargs = dict(image_kwargs or {})
    kwargs.setdefault("units", "norm" if scale == "auto" else str(image_units))
    kwargs.setdefault("pos", tuple(pos))
    if image_size is not None:
        kwargs.setdefault("size", tuple(image_size))
    return kwargs


def _validate_image_scale(scale: Union[float, str]) -> None:
    """Validate image scale before ImageStim construction."""
    if scale == "auto":
        return
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise ValueError("scale must be either 'auto' or a positive number.")
    if float(scale) <= 0:
        raise ValueError("scale must be either 'auto' or a positive number.")


def _apply_image_scale(image_stim: Any, win: Any, scale: Union[float, str]) -> None:
    """Apply numeric or automatic image scaling to an ImageStim."""
    if scale == "auto":
        image_stim.size = _auto_image_size(image_stim, win)
        return
    if float(scale) == 1.0:
        return
    stim_w, stim_h = (float(value) for value in image_stim.size)
    image_stim.size = (stim_w * float(scale), stim_h * float(scale))


def _auto_image_size(image_stim: Any, win: Any) -> tuple:
    """Return a norm-units image size that fits the window aspect ratio."""
    frame_size = getattr(win, "frameBufferSize", None)
    if frame_size is not None and len(frame_size) == 2:
        win_w, win_h = (float(value) for value in frame_size)
    else:
        win_w, win_h = (float(value) for value in getattr(win, "size", (0, 0)))
    native_size = getattr(image_stim, "_origSize", None)
    if native_size is not None and len(native_size) == 2:
        img_w, img_h = (abs(float(value)) for value in native_size)
    else:
        img_w, img_h = (abs(float(value)) for value in image_stim.size)
    if win_w <= 0 or win_h <= 0 or img_w <= 0 or img_h <= 0:
        return (2.0, 2.0)
    win_ratio = win_w / win_h
    img_ratio = img_w / img_h
    if img_ratio >= win_ratio:
        return (2.0, 2.0 * (win_ratio / img_ratio))
    return (2.0 * (img_ratio / win_ratio), 2.0)


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

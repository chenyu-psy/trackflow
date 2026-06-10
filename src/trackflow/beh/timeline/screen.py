"""Screen presentation unit used by behavior timelines."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .. import _psychopy
from .context import TrialInterrupted


class Screen:
    """One timeline-owned presentation and keyboard-response unit.

    Parameters
    ----------
    stimuli : sequence
        Stimulus-like objects with ``draw()``. Objects with ``is_visible()`` use
        their own timing; other drawable objects are shown for the full screen.
    duration : float, optional
        Maximum screen duration in seconds. ``None`` means the screen must end
        through a key response.
    response : str, optional
        Response mode: ``None`` or ``"key"``. Defaults to ``"key"``.
    choices : sequence[str], optional
        Allowed response choices for the selected response mode. For
        ``response="key"``, these are PsychoPy key names. ``None`` accepts no
        participant response choices.
    response_start : float, optional
        Seconds after screen onset before responses are accepted.
    end_on_response : bool, optional
        Whether the screen ends immediately after the first response.
    clear_events : bool, optional
        Whether keyboard events should be cleared before the screen starts.
    data : dict, optional
        Screen-level fields copied into the returned raw screen row. Use this
        for readable labels such as ``{"screen_name": "fixation"}``.
    on_start, on_load, on_frame, on_finish : callable, optional
        Lifecycle hooks. Hooks may receive only ``RunContext`` for concise
        context-owned actions, or explicit row arguments: ``(ctx, data)`` for
        start/load/finish and ``(ctx, data, elapsed)`` for frame hooks.

    Examples
    --------
    >>> timeline = setup_timeline(win=win)
    >>> screen = timeline.make_screen(stimuli=[fix], duration=1.0, response="key", choices=["space"])
    """

    def __init__(
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
    ) -> None:
        """Create and validate one screen specification."""
        self.stimuli = _validate_stimuli(stimuli)
        self.duration = _validate_optional_duration(duration)
        self.response = _validate_response_mode(response)
        self.choices = _validate_choices(choices)
        self.response_start = _validate_response_start(response_start)
        self.end_on_response = bool(end_on_response)
        self.clear_events = bool(clear_events)
        self.data = dict(data or {})
        self.on_start = on_start
        self.on_load = on_load
        self.on_frame = on_frame
        self.on_finish = on_finish

        _validate_screen_end_condition(self.duration, self.response, self.choices, self.end_on_response)

    def update(
        self,
        stimuli: Optional[Sequence[Any]] = None,
        duration: Optional[float] = None,
        response: Optional[str] = None,
        choices: Optional[Sequence[str]] = None,
        response_start: Optional[float] = None,
        end_on_response: Optional[bool] = None,
        clear_events: Optional[bool] = None,
        data: Optional[Dict[str, Any]] = None,
        on_frame: Optional[Callable[[Any, Dict[str, Any], float], None]] = None,
    ) -> None:
        """Update screen settings in place.

        Parameters
        ----------
        stimuli, duration, response, choices, response_start, end_on_response,
        clear_events, data, on_frame : optional
            Screen settings to replace before a run starts. Omitted settings
            keep their current values.

        Returns
        -------
        None
            Mutates this screen. Changing these fields can change task timing,
            response collection, or saved screen data.
        """
        if stimuli is not None:
            self.stimuli = _validate_stimuli(stimuli)
        if duration is not None:
            self.duration = _validate_optional_duration(duration)
        if response is not None:
            self.response = _validate_response_mode(response)
        if choices is not None:
            self.choices = _validate_choices(choices)
        if response_start is not None:
            self.response_start = _validate_response_start(response_start)
        if end_on_response is not None:
            self.end_on_response = bool(end_on_response)
        if clear_events is not None:
            self.clear_events = bool(clear_events)
        if data is not None:
            self.data = dict(data)
        if on_frame is not None:
            self.on_frame = on_frame

        _validate_screen_end_condition(self.duration, self.response, self.choices, self.end_on_response)

    def run(
        self,
        win: Any,
        screen_index: int = 0,
        row: Optional[Dict[str, Any]] = None,
        ctx: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Present this screen and return one raw screen row.

        This is a low-level method. It returns a raw row but does not write to
        timeline records. Ordinary experiment scripts should call
        ``timeline.run(screen)``.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window used for drawing and flipping.
        screen_index : int, optional
            Zero-based screen index within the current trial.
        row : dict, optional
            Trial-data fields copied into the raw screen row.
        ctx : RunContext, optional
            Current run context passed to lifecycle hooks.

        Returns
        -------
        dict
            Raw screen row with response, RT, markers, and messages fields.
        """
        out = _make_screen_row(row, self.data, screen_index)
        response_value = None
        rt = None
        try:
            if self.on_start is not None:
                _require_context(ctx, "on_start")
                _call_row_hook(self.on_start, ctx, out)

            core = _load_psychopy_core()
            event = _load_psychopy_event()
            if ctx is not None and hasattr(ctx.timeline, "register_global_keys"):
                ctx.timeline.register_global_keys(event)
            if self.clear_events:
                event.clearEvents(eventType="keyboard")

            loaded = False
            start_time = core.getTime()

            while True:
                elapsed = core.getTime() - start_time
                if self.duration is not None and elapsed >= self.duration:
                    break

                _draw_visible_stimuli(self.stimuli, elapsed)
                win.flip()
                if not loaded:
                    loaded = True
                    if self.on_load is not None:
                        _require_context(ctx, "on_load")
                        _call_row_hook(self.on_load, ctx, out)

                if self.on_frame is not None:
                    _require_context(ctx, "on_frame")
                    _call_frame_hook(self.on_frame, ctx, out, elapsed)

                if ctx is not None and hasattr(ctx.timeline, "handle_global_keys"):
                    if ctx.timeline.handle_global_keys(ctx, out, event):
                        break

                if elapsed >= self.response_start and response_value is None and self.response == "key":
                    response_value, rt = _collect_key_response(event, self.choices, start_time, core)
                    if response_value is not None:
                        out["response"] = response_value
                        out["rt"] = rt

                if response_value is not None and self.end_on_response:
                    break

            out["response"] = response_value
            out["rt"] = rt
            if self.on_finish is not None:
                _require_context(ctx, "on_finish")
                _call_row_hook(self.on_finish, ctx, out)
        except TrialInterrupted as err:
            out["response"] = response_value
            out["rt"] = rt
            out["trial_status"] = "interrupted"
            out["interruption"] = err.reason
            out.update(err.data)
            err.row = dict(out)
            raise
        return out


def _make_screen(
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
    """Create one validated screen-level presentation unit."""
    return Screen(
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


def _load_psychopy_core() -> Any:
    """Import ``psychopy.core`` only when a screen is shown."""
    return _psychopy.load_core()


def _load_psychopy_event() -> Any:
    """Import ``psychopy.event`` only when a screen is shown."""
    return _psychopy.load_event()


def _validate_stimuli(stimuli: Sequence[Any]) -> List[Any]:
    """Return a list of drawable stimuli."""
    if stimuli is None:
        raise ValueError("stimuli must be provided.")
    stim_list = list(stimuli)
    for stim in stim_list:
        if not hasattr(stim, "draw") or not callable(stim.draw):
            raise TypeError("Each stimulus must have a callable draw() method.")
    return stim_list


def _validate_optional_duration(duration: Optional[float]) -> Optional[float]:
    """Return ``duration`` as a non-negative float or ``None``."""
    if duration is None:
        return None
    value = float(duration)
    if value < 0:
        raise ValueError("duration must be greater than or equal to 0.")
    return value


def _validate_response_start(response_start: float) -> float:
    """Return ``response_start`` as a non-negative float."""
    value = float(response_start)
    if value < 0:
        raise ValueError("response_start must be greater than or equal to 0.")
    return value


def _validate_response_mode(response: Optional[str]) -> Optional[str]:
    """Validate and normalize the response mode."""
    if response is None:
        return None
    value = str(response).strip().lower()
    if value != "key":
        raise ValueError("response must be None or 'key' in the current trackflow.beh runtime.")
    return value


def _validate_choices(choices: Optional[Sequence[str]]) -> Optional[List[str]]:
    """Return allowed response choices as strings, or ``None`` for no choices."""
    if choices is None:
        return None
    return [str(choice) for choice in choices]


def _validate_screen_end_condition(
    duration: Optional[float],
    response: Optional[str],
    choices: Optional[Sequence[str]],
    end_on_response: bool,
) -> None:
    """Raise when a screen has no possible end condition."""
    if duration is None and response is None:
        raise ValueError("duration or response must be provided.")
    if duration is None and response == "key" and choices is None:
        raise ValueError("duration is required when response='key' and choices is None.")
    if duration is None and response == "key" and not end_on_response:
        raise ValueError("duration is required when end_on_response is False.")


def _make_screen_row(
    row: Optional[Dict[str, Any]],
    screen_data: Dict[str, Any],
    screen_index: int,
) -> Dict[str, Any]:
    """Create the mutable row shared by all screen lifecycle hooks."""
    out = dict(row or {})
    out.update(screen_data)
    out.setdefault("screen_index", int(screen_index))
    out["response"] = None
    out["rt"] = None
    out.setdefault("markers", [])
    out.setdefault("messages", [])
    return out


def _require_context(ctx: Optional[Any], hook_name: str) -> None:
    """Raise a clear error when a lifecycle hook runs without context."""
    if ctx is None:
        raise RuntimeError(f"{hook_name} requires a RunContext. Use Timeline.run(...) for screens with hooks.")


def _call_row_hook(hook: Callable[..., None], ctx: Any, data: Dict[str, Any]) -> None:
    """Call a row hook with either ``ctx`` or ``ctx, data``."""
    if _accepts_n_positional_args(hook, 1) and not _accepts_n_positional_args(hook, 2):
        hook(ctx)
        return
    hook(ctx, data)


def _call_frame_hook(hook: Callable[..., None], ctx: Any, data: Dict[str, Any], elapsed: float) -> None:
    """Call a frame hook with concise or explicit arguments."""
    if _accepts_n_positional_args(hook, 1) and not _accepts_n_positional_args(hook, 2):
        hook(ctx)
        return
    if _accepts_n_positional_args(hook, 2) and not _accepts_n_positional_args(hook, 3):
        hook(ctx, elapsed)
        return
    hook(ctx, data, elapsed)


def _accepts_n_positional_args(hook: Callable[..., None], count: int) -> bool:
    """Return whether ``hook`` can be called with ``count`` positional args."""
    try:
        signature = inspect.signature(hook)
    except (TypeError, ValueError):
        return True
    positional = [
        param
        for param in signature.parameters.values()
        if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
    ]
    if any(param.kind == param.VAR_POSITIONAL for param in signature.parameters.values()):
        return True
    required = [param for param in positional if param.default is param.empty]
    return len(required) <= count <= len(positional)


def _draw_visible_stimuli(stimuli: Sequence[Any], elapsed: float) -> None:
    """Draw all stimuli visible at the current elapsed time."""
    for stim in stimuli:
        if hasattr(stim, "is_visible") and callable(stim.is_visible):
            if not stim.is_visible(elapsed):
                continue
        stim.draw()


def _collect_key_response(
    event: Any,
    choices: Optional[List[str]],
    start_time: float,
    core: Any,
) -> Tuple[Any, Optional[float]]:
    """Return the first queued key response and RT, or ``(None, None)``."""
    if choices is None:
        return None, None
    pressed = event.getKeys(keyList=choices)
    if not pressed:
        return None, None
    return pressed[0], core.getTime() - start_time

"""Screen helpers for key-based behavior presentation.

This module defines the smallest presentation unit used by the 0.1.0 behavior
runtime. A ``Screen`` can be fixed-duration with no response, or it can collect
one keyboard response after an optional response-start delay.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import _psychopy


__all__ = ["Screen", "make_screen"]


class Screen:
    """One screen-level presentation and keyboard-response unit.

    Parameters
    ----------
    stimuli : sequence
        Stimulus-like objects with ``draw()``. Objects with ``is_visible()`` use
        their own timing; other drawable objects are shown for the full screen.
    duration : float, optional
        Maximum screen duration in seconds. ``None`` means the screen must end
        through a key response.
    response : str, optional
        Response mode: ``None`` or ``"key"``. Built-in button responses are
        deferred until a later version.
    keys : sequence[str], optional
        Allowed keys for key response. ``None`` accepts any key.
    response_start : float, optional
        Seconds after screen onset before responses are accepted.
    end_on_response : bool, optional
        Whether the screen ends immediately after the first response.
    clear_events : bool, optional
        Whether keyboard events should be cleared before the screen starts.
    data : dict, optional
        Screen-level fields copied into the returned screen row.
    run_if, on_start, on_load, on_response, on_finish : callable, optional
        Lifecycle hooks used by ``Trial`` and ``Timeline``. Hooks receive the
        current run context and screen data row, except ``run_if`` which
        receives only the context.

    Examples
    --------
    >>> screen = Screen(stimuli=[fix], duration=1.0, response="key", keys=["space"])
    """

    def __init__(
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
        screen_name: Optional[str] = None,
        run_if: Optional[Callable[[Any], bool]] = None,
        on_start: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_load: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_response: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
        on_finish: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
    ) -> None:
        """Create and validate one screen specification."""
        if choices is not None:
            raise ValueError("button/clickable choices are not supported by trackflow.beh 0.1.0.")
        self.stimuli = _validate_stimuli(stimuli)
        self.duration = _validate_optional_duration(duration)
        self.response = _validate_response_mode(response)
        self.keys = _validate_keys(keys)
        self.response_start = _validate_response_start(response_start)
        self.end_on_response = bool(end_on_response)
        self.clear_events = bool(clear_events)
        self.data = dict(data or {})
        self.screen_name = screen_name
        self.run_if = run_if
        self.on_start = on_start
        self.on_load = on_load
        self.on_response = on_response
        self.on_finish = on_finish

        if self.duration is None and self.response is None:
            raise ValueError("duration or response must be provided.")
        if self.duration is None and not self.end_on_response:
            raise ValueError("duration is required when end_on_response is False.")

    def update(
        self,
        stimuli: Optional[Sequence[Any]] = None,
        duration: Optional[float] = None,
        response: Optional[str] = None,
        keys: Optional[Sequence[str]] = None,
        response_start: Optional[float] = None,
        end_on_response: Optional[bool] = None,
        clear_events: Optional[bool] = None,
        data: Optional[Dict[str, Any]] = None,
        screen_name: Optional[str] = None,
    ) -> None:
        """Update screen settings in place.

        Parameters
        ----------
        stimuli, duration, response, keys, response_start, end_on_response,
        clear_events, data, screen_name : optional
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
        if keys is not None:
            self.keys = _validate_keys(keys)
        if response_start is not None:
            self.response_start = _validate_response_start(response_start)
        if end_on_response is not None:
            self.end_on_response = bool(end_on_response)
        if clear_events is not None:
            self.clear_events = bool(clear_events)
        if data is not None:
            self.data = dict(data)
        if screen_name is not None:
            self.screen_name = str(screen_name)

        if self.duration is None and self.response is None:
            raise ValueError("duration or response must be provided.")
        if self.duration is None and not self.end_on_response:
            raise ValueError("duration is required when end_on_response is False.")

    def run(
        self,
        win: Any,
        screen_index: int = 0,
        row: Optional[Dict[str, Any]] = None,
        ctx: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Present this screen and return one raw screen row.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window used for drawing and flipping.
        screen_index : int, optional
            Zero-based screen index within the current trial.
        row : dict, optional
            Trial/session fields copied into the raw screen row.
        ctx : RunContext, optional
            Current run context passed to lifecycle hooks.

        Returns
        -------
        dict
            Raw screen row with response, RT, markers, and messages fields.
        """
        out = _make_screen_row(row, self.data, screen_index, self.screen_name)
        if self.on_start is not None:
            _require_context(ctx, "on_start")
            self.on_start(ctx, out)

        core = _load_psychopy_core()
        event = _load_psychopy_event()
        if ctx is not None and hasattr(ctx.timeline, "register_global_keys"):
            ctx.timeline.register_global_keys(event)
        if self.clear_events:
            event.clearEvents(eventType="keyboard")

        response_value = None
        rt = None
        loaded = False
        response_hook_called = False
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
                    self.on_load(ctx, out)

            if ctx is not None and hasattr(ctx.timeline, "handle_global_keys"):
                if ctx.timeline.handle_global_keys(ctx, out, event):
                    break

            if elapsed >= self.response_start and response_value is None and self.response == "key":
                response_value, rt = _collect_key_response(event, self.keys, start_time, core)
                if response_value is not None:
                    out["response"] = response_value
                    out["rt"] = rt
                    if not response_hook_called and self.on_response is not None:
                        response_hook_called = True
                        _require_context(ctx, "on_response")
                        self.on_response(ctx, out)

            if response_value is not None and self.end_on_response:
                break

        out["response"] = response_value
        out["rt"] = rt
        if self.on_finish is not None:
            _require_context(ctx, "on_finish")
            self.on_finish(ctx, out)
        return out


def make_screen(
    stimuli: Sequence[Any],
    duration: Optional[float] = None,
    response: Optional[str] = None,
    keys: Optional[Sequence[str]] = None,
    choices: Optional[Any] = None,
    response_start: float = 0,
    end_on_response: bool = True,
    clear_events: bool = True,
    data: Optional[Dict[str, Any]] = None,
    screen_name: Optional[str] = None,
    run_if: Optional[Callable[[Any], bool]] = None,
    on_start: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
    on_load: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
    on_response: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
    on_finish: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
) -> Screen:
    """Create one screen-level presentation unit.

    Parameters
    ----------
    stimuli : sequence
        Stimulus-like objects to draw.
    duration : float, optional
        Maximum screen duration.
    response : str, optional
        ``None`` for no response or ``"key"`` for keyboard responses.
    keys : sequence[str], optional
        Allowed keyboard responses.
    choices : object, optional
        Unsupported in 0.1.0 and reserved for future button responses.
    response_start, end_on_response, clear_events
        Screen timing and keyboard response settings; see ``Screen``.
    data : dict, optional
        Static screen-level fields copied into each raw row.
    screen_name : str, optional
        Readable screen label.
    run_if, on_start, on_load, on_response, on_finish : callable, optional
        Lifecycle hooks used by ``Trial`` and ``Timeline``.

    Returns
    -------
    Screen
        Validated screen specification for ``Timeline.show_screen``.
    """
    return Screen(
        stimuli=stimuli,
        duration=duration,
        response=response,
        keys=keys,
        choices=choices,
        response_start=response_start,
        end_on_response=end_on_response,
        clear_events=clear_events,
        data=data,
        screen_name=screen_name,
        run_if=run_if,
        on_start=on_start,
        on_load=on_load,
        on_response=on_response,
        on_finish=on_finish,
    )


def _load_psychopy_core() -> Any:
    """Import ``psychopy.core`` only when a screen is shown."""
    return _psychopy.load_core()


def _load_psychopy_event() -> Any:
    """Import ``psychopy.event`` only when a screen is shown."""
    return _psychopy.load_event()


def _load_psychopy_visual() -> Any:
    """Import ``psychopy.visual`` only when built-in visual stimuli are needed."""
    return _psychopy.load_visual()


def _validate_stimuli(stimuli: Sequence[Any]) -> List[Any]:
    """Return a list of drawable stimuli.

    Parameters
    ----------
    stimuli : sequence
        Candidate stimulus objects.

    Returns
    -------
    list
        Drawable stimulus objects.
    """
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
        raise ValueError("response must be None or 'key' in trackflow.beh 0.1.0.")
    return value


def _validate_keys(keys: Optional[Sequence[str]]) -> Optional[List[str]]:
    """Return allowed keys as strings, or ``None`` to accept any key."""
    if keys is None:
        return None
    return [str(key) for key in keys]


def _make_screen_row(
    row: Optional[Dict[str, Any]],
    screen_data: Dict[str, Any],
    screen_index: int,
    screen_name: Optional[str],
) -> Dict[str, Any]:
    """Create the mutable row shared by all screen lifecycle hooks.

    Parameters
    ----------
    row : dict, optional
        Trial/session fields inherited by this screen.
    screen_data : dict
        Static screen-level fields.
    screen_index : int
        Zero-based index within the current trial.
    screen_name : str, optional
        Readable screen label.

    Returns
    -------
    dict
        Screen row initialized with response, RT, markers, and messages fields.
    """
    out = dict(row or {})
    out.update(screen_data)
    out.setdefault("screen_index", int(screen_index))
    if screen_name is not None:
        out.setdefault("screen_name", str(screen_name))
    out["response"] = None
    out["rt"] = None
    out.setdefault("markers", [])
    out.setdefault("messages", [])
    return out


def _require_context(ctx: Optional[Any], hook_name: str) -> None:
    """Raise a clear error when a lifecycle hook runs without context."""
    if ctx is None:
        raise RuntimeError(f"{hook_name} requires a RunContext. Use Timeline or Trial to run screens with hooks.")


def _draw_visible_stimuli(stimuli: Sequence[Any], elapsed: float) -> None:
    """Draw all stimuli visible at the current elapsed time."""
    for stim in stimuli:
        if hasattr(stim, "is_visible") and callable(stim.is_visible):
            if not stim.is_visible(elapsed):
                continue
        stim.draw()


def _collect_key_response(event: Any, keys: Optional[List[str]], start_time: float, core: Any) -> Tuple[Any, Optional[float]]:
    """Return the first queued key response and RT, or ``(None, None)``."""
    if keys is None:
        pressed = event.getKeys()
    else:
        pressed = event.getKeys(keyList=keys)
    if not pressed:
        return None, None
    return pressed[0], core.getTime() - start_time

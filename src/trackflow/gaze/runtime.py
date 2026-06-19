"""Runtime helpers shared by eye-tracking modules.

This module keeps optional PsychoPy and pylink imports lazy so importing
``trackflow.gaze`` does not initialize hardware or require an EyeLink runtime.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple

MOUSE_TOKENS = {
    "mouse_left": 0,
    "mouse_middle": 1,
    "mouse_right": 2,
}

DEFAULT_REJECTION_PROMPT = (
    "There may be a problem with the eye tracker.\n\n"
    "Press C to calibrate, D for drift correction, or S to skip."
)
REJECTION_ALERT_BG = "#E9954D"


def _load_psychopy_module(name: str) -> Any:
    """Import one PsychoPy submodule when a runtime helper needs it.

    Parameters
    ----------
    name : str
        PsychoPy submodule name, such as ``"event"`` or ``"visual"``.

    Returns
    -------
    module
        Imported PsychoPy submodule.

    Raises
    ------
    RuntimeError
        If PsychoPy or the requested submodule cannot be imported.
    """
    try:
        module = __import__(f"psychopy.{name}", fromlist=[name])
    except Exception as exc:
        raise RuntimeError(f"psychopy.{name} is required for this gaze helper.") from exc
    return module


def _load_pylink() -> Any:
    """Import pylink only when an EyeLink connection is requested.

    Returns
    -------
    module
        Imported ``pylink`` module.

    Raises
    ------
    RuntimeError
        If pylink is not installed or cannot load on the current machine.
    """
    try:
        return __import__("pylink")
    except Exception as exc:
        raise RuntimeError("pylink is required for connected EyeLink use.") from exc


def _normalize_hex(hex_color: str) -> str:
    """Normalize a HEX color to ``#RRGGBB``.

    Parameters
    ----------
    hex_color : str
        Color string with or without a leading ``#``.

    Returns
    -------
    str
        Normalized uppercase HEX color.

    Raises
    ------
    ValueError
        If the color is not a 6-digit HEX value.
    """
    text = str(hex_color).strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise ValueError("HEX colors must use six digits, for example '#7F7F7F'.")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError("HEX colors must contain only 0-9 and A-F.") from exc
    return f"#{text.upper()}"


def _hex_to_rgb255(hex_color: str) -> Tuple[int, int, int]:
    """Convert a HEX color to 0-255 RGB values.

    Parameters
    ----------
    hex_color : str
        Color string such as ``"#FFFFFF"``.

    Returns
    -------
    tuple[int, int, int]
        Red, green, and blue channel values.
    """
    text = _normalize_hex(hex_color)[1:]
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _should_use_dark_text(color: Any) -> bool:
    """Return whether dark text should be readable on a background color.

    Parameters
    ----------
    color : object
        PsychoPy window color. HEX strings are handled directly; other values
        fall back to dark text.

    Returns
    -------
    bool
        ``True`` when black text should be readable.
    """
    if not isinstance(color, str):
        return True
    red, green, blue = _hex_to_rgb255(color)
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    return luminance > 186


def _draw_text_page(
    win: Any,
    text: str,
    text_color: Optional[str] = None,
    bg_color: Optional[str] = None,
) -> None:
    """Draw a simple centered text page and flip the PsychoPy window.

    Parameters
    ----------
    win : psychopy.visual.Window
        Window used for drawing.
    text : str
        Message shown to the participant or researcher.
    text_color : str | None, optional
        HEX text color. If omitted, chosen from the window background.
    bg_color : str | None, optional
        Optional HEX background color.

    Returns
    -------
    None
        Draws and flips the window.
    """
    visual = _load_psychopy_module("visual")
    if text_color is None:
        text_color = "#000000" if _should_use_dark_text(getattr(win, "color", "#FFFFFF")) else "#FFFFFF"
    if bg_color is not None:
        visual.Rect(win, units="norm", width=2, height=2, fillColor=bg_color, colorSpace="hex").draw()
    visual.TextStim(
        win,
        text=str(text),
        color=text_color,
        colorSpace="hex",
        units="norm",
        height=0.05,
        wrapWidth=1.6,
    ).draw()
    win.flip()


def _split_continue_keys(continue_keys: Optional[Iterable[str]]) -> Tuple[List[str], List[int]]:
    """Split keyboard names and supported mouse tokens.

    Parameters
    ----------
    continue_keys : iterable[str] | None
        PsychoPy key names plus optional ``mouse_left``, ``mouse_middle``, or
        ``mouse_right`` tokens.

    Returns
    -------
    tuple[list[str], list[int]]
        PsychoPy keyboard names and PsychoPy mouse button indices.
    """
    if continue_keys is None:
        return [], []
    key_names: List[str] = []
    mouse_buttons: List[int] = []
    for item in continue_keys:
        token = str(item)
        if token in MOUSE_TOKENS:
            mouse_buttons.append(MOUSE_TOKENS[token])
        else:
            key_names.append(token)
    return key_names, mouse_buttons


def _has_gaze_xy(sample: Any) -> bool:
    """Return whether a gaze sample contains numeric x/y values.

    Parameters
    ----------
    sample : object
        Gaze sample returned by EyeLink for one eye.

    Returns
    -------
    bool
        ``True`` when the sample looks like ``(x, y)`` and both values are
        present.
    """
    if sample is None:
        return False
    try:
        return sample[0] is not None and sample[1] is not None
    except (TypeError, IndexError):
        return False


def _wait_for_continue(win: Any, continue_keys: Sequence[str] = ("space",)) -> str:
    """Wait for a keyboard key or supported mouse button.

    Parameters
    ----------
    win : psychopy.visual.Window
        Window used to create a PsychoPy mouse when mouse tokens are allowed.
    continue_keys : sequence[str], optional
        PsychoPy key names plus optional ``mouse_left``, ``mouse_middle``, or
        ``mouse_right`` tokens.

    Returns
    -------
    str
        The key name or mouse token that ended the wait.

    Raises
    ------
    ValueError
        If no keyboard or mouse response is allowed.
    """
    key_names, mouse_buttons = _split_continue_keys(continue_keys)
    if not key_names and not mouse_buttons:
        raise ValueError("continue_keys must allow at least one key or mouse button.")

    event = _load_psychopy_module("event")
    core = _load_psychopy_module("core")
    mouse = event.Mouse(win=win) if mouse_buttons else None
    previous_buttons = [0, 0, 0]
    if mouse is not None:
        previous_buttons = list(mouse.getPressed())

    while True:
        if key_names:
            keys = event.getKeys(keyList=key_names)
            if keys:
                return str(keys[0])

        if mouse is not None:
            buttons = list(mouse.getPressed())
            for button_idx in mouse_buttons:
                if buttons[button_idx] and not previous_buttons[button_idx]:
                    for token, idx in MOUSE_TOKENS.items():
                        if idx == button_idx:
                            return token
            previous_buttons = buttons

        core.wait(0.01)

"""Timeline-owned EEG and EyeLink send helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def send_eeg(eeg: Optional[Any], state: Dict[str, Any], code: int) -> None:
    """Send one EEG marker when a sender is configured."""
    marker_code = validate_numeric_code(code, caller="send")
    if eeg is None:
        return None
    try:
        eeg.send(marker_code)
    except Exception as exc:
        record_failure(state, f"EEG marker {marker_code} failed: {exc}")
    return None


def send_gaze(gaze: Optional[Any], state: Dict[str, Any], message: str) -> None:
    """Send one EyeLink message when a tracker is configured."""
    message_text = str(message)
    if gaze is None:
        return None
    try:
        _send_gaze_message(gaze, message_text)
    except Exception as exc:
        record_failure(state, f"EyeLink message failed: {exc}")
    return None


def record_failure(state: Dict[str, Any], message: str) -> None:
    """Store readable failure information for a later researcher pause."""
    state["pause_experiment"] = True
    state["sync_error"] = message


def validate_numeric_code(code: int, caller: str = "send") -> int:
    """Return an integer EEG code and reject code-dictionary keys."""
    if isinstance(code, bool) or isinstance(code, str):
        raise ValueError(f"{caller}(...) requires a numeric EEG code. Look up string keys before sending.")
    try:
        return int(code)
    except (TypeError, ValueError):
        raise ValueError(f"{caller}(...) requires a numeric EEG code.")


def _send_gaze_message(gaze: Any, message_text: str) -> None:
    """Send an EyeLink message using the available tracker method."""
    if hasattr(gaze, "send_msg") and callable(gaze.send_msg):
        gaze.send_msg(message_text)
        return
    if hasattr(gaze, "send_message") and callable(gaze.send_message):
        gaze.send_message(message_text)
        return
    raise TypeError("gaze device must provide send_msg(text) or send_message(text).")


__all__: Tuple[str, ...] = ("send_eeg", "send_gaze", "validate_numeric_code")

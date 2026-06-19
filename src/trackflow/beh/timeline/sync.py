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


def send_gaze(gaze: Optional[Any], state: Dict[str, Any], message: Any = None, status: Any = None) -> None:
    """Send EyeLink EDF messages and/or host status lines when configured."""
    if message is None and status is None:
        raise ValueError("timeline.send_gaze(...) requires message, status, or both.")
    if gaze is None:
        return None
    if message is not None:
        try:
            _send_gaze_message(gaze, str(message))
        except Exception as exc:
            record_failure(state, f"EyeLink message failed: {exc}")
    if status is not None:
        try:
            _send_gaze_host_status(gaze, str(status))
        except Exception as exc:
            record_failure(state, f"EyeLink status failed: {exc}")
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


def _send_gaze_host_status(gaze: Any, status_text: str) -> None:
    """Send an EyeLink host status line using the tracker status method."""
    if hasattr(gaze, "send_status") and callable(gaze.send_status):
        gaze.send_status(status_text)
        return
    raise TypeError("gaze device must provide send_status(text).")


__all__: Tuple[str, ...] = ("send_eeg", "send_gaze", "validate_numeric_code")

"""EEG and EyeLink synchronization send helpers.

The sync helper sends hardware signals and returns JSON-friendly records.
It does not mutate behavior screen rows; experiment hooks decide what to save.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SyncResult:
    """Records returned after one sync send attempt.

    Parameters
    ----------
    code : int
        EEG marker code requested by the experiment.
    markers : list[dict], optional
        EEG marker records to append to screen data when desired.
    messages : list[dict], optional
        EyeLink message records to append to screen data when desired.
    """

    code: int
    markers: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)


class SyncController:
    """Send sync events to configured EEG and EyeLink devices.

    Parameters
    ----------
    eeg : object, optional
        EEG sender with a ``send(code)`` method.
    gaze : object, optional
        EyeLink wrapper with ``send_msg(text)`` or ``send_message(text)``.
    state : dict, optional
        Mutable timeline state updated when sync sends fail.
    """

    def __init__(self, eeg: Optional[Any] = None, gaze: Optional[Any] = None, state: Optional[Dict[str, Any]] = None) -> None:
        """Store sync devices and mutable failure state."""
        self.eeg = eeg
        self.gaze = gaze
        self.state = state if state is not None else {}
        self.code = dict(getattr(eeg, "code", {}) or {})

    def send(self, code: int, gaze_message: Optional[str] = None) -> SyncResult:
        """Send one sync event and return records for optional saving.

        Parameters
        ----------
        code : int
            EEG marker code.
        gaze_message : str, optional
            EyeLink message text. When omitted, no EyeLink message is sent.

        Returns
        -------
        SyncResult
            Marker/message records describing successful and failed sends.
        """
        marker_code = _validate_numeric_code(code)
        result = SyncResult(code=marker_code)

        if self.eeg is not None:
            result.markers.append(self._send_eeg(marker_code))
        if self.gaze is not None and gaze_message is not None:
            result.messages.append(self._send_gaze(str(gaze_message)))

        return result

    def _send_eeg(self, code: int) -> Dict[str, Any]:
        """Send one EEG code and return a marker record."""
        record = {"source": "eeg", "code": int(code), "status": "sent"}
        try:
            self.eeg.send(code)
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            self._record_failure(f"EEG marker {code} failed: {exc}")
        return record

    def _send_gaze(self, message_text: str) -> Dict[str, Any]:
        """Send one EyeLink message and return a message record."""
        record = {"source": "eyelink", "text": message_text, "status": "sent"}
        try:
            _send_gaze_message(self.gaze, message_text)
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            self._record_failure(f"EyeLink message failed: {exc}")
        return record

    def _record_failure(self, message: str) -> None:
        """Store readable failure information for a later researcher pause."""
        self.state["pause_experiment"] = True
        self.state["sync_error"] = message


def _send_gaze_message(gaze: Any, message_text: str) -> None:
    """Send an EyeLink message using the available tracker method."""
    if hasattr(gaze, "send_msg") and callable(gaze.send_msg):
        gaze.send_msg(message_text)
        return
    if hasattr(gaze, "send_message") and callable(gaze.send_message):
        gaze.send_message(message_text)
        return
    raise TypeError("gaze device must provide send_msg(text) or send_message(text).")


def _validate_numeric_code(code: int) -> int:
    """Return an integer EEG code and reject code-dictionary keys."""
    if isinstance(code, bool) or isinstance(code, str):
        raise ValueError("ctx.sync.send(...) requires a numeric EEG code. Look up string keys with ctx.sync.code[key].")
    try:
        return int(code)
    except (TypeError, ValueError):
        raise ValueError("ctx.sync.send(...) requires a numeric EEG code.")


__all__: Tuple[str, ...] = ("SyncController", "SyncResult")

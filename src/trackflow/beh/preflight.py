"""Explicit preflight checks for behavior experiment sessions.

Preflight checks are intentionally opt-in. They verify only the subsystems that
the experiment enables, so a behavior-only session does not require EyeLink or
EEG hardware imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from . import _psychopy


__all__ = ["PreflightResult", "check_preflight", "preflight_or_raise"]


@dataclass
class PreflightResult:
    """Result from checking enabled runtime subsystems.

    Parameters
    ----------
    passed : bool
        Whether all requested checks passed.
    issues : list[str], optional
        Readable problems for the researcher to fix before running.
    """

    passed: bool
    issues: List[str] = field(default_factory=list)

    def raise_for_issues(self) -> None:
        """Raise a clear error when any preflight check failed.

        Returns
        -------
        None
            Returns silently when ``passed`` is true.
        """
        if self.passed:
            return
        raise RuntimeError("Preflight checks failed: " + "; ".join(self.issues))


def check_preflight(
    *,
    require_psychopy: bool = True,
    eeg: Optional[Any] = None,
    gaze: Optional[Any] = None,
) -> PreflightResult:
    """Check enabled behavior, EEG, and eye-tracking runtime pieces.

    Parameters
    ----------
    require_psychopy : bool, optional
        Whether to check that core PsychoPy behavior modules import.
    eeg : object, optional
        Enabled EEG sender. When omitted, EEG is not checked.
    gaze : object, optional
        Enabled eye-tracker wrapper. When omitted, eye tracking is not checked.

    Returns
    -------
    PreflightResult
        Pass/fail result with readable issues.
    """
    issues: List[str] = []
    if require_psychopy:
        issues.extend(_check_psychopy())
    if eeg is not None:
        issues.extend(_check_eeg_sender(eeg))
    if gaze is not None:
        issues.extend(_check_gaze_sender(gaze))
    return PreflightResult(passed=not issues, issues=issues)


def preflight_or_raise(**kwargs: Any) -> PreflightResult:
    """Run ``check_preflight`` and raise if a requested check fails.

    Parameters
    ----------
    **kwargs
        Arguments forwarded to ``check_preflight``.

    Returns
    -------
    PreflightResult
        Passing result, useful for logging or tests.
    """
    result = check_preflight(**kwargs)
    result.raise_for_issues()
    return result


def _check_psychopy() -> List[str]:
    """Return import issues for core PsychoPy behavior modules."""
    issues: List[str] = []
    loaders = [
        ("psychopy.core", _psychopy.load_core),
        ("psychopy.event", _psychopy.load_event),
        ("psychopy.visual", _psychopy.load_visual),
    ]
    for label, loader in loaders:
        try:
            loader()
        except Exception as exc:
            issues.append(f"{label} is not available: {exc}")
    return issues


def _check_eeg_sender(eeg: Any) -> List[str]:
    """Return configuration issues for an enabled EEG sender."""
    issues: List[str] = []
    if not hasattr(eeg, "send") or not callable(eeg.send):
        issues.append("EEG sender must provide send(code).")
    code = getattr(eeg, "code", {})
    if code is not None and not isinstance(code, dict):
        issues.append("EEG sender code dictionary must be a dict when provided.")
    return issues


def _check_gaze_sender(gaze: Any) -> List[str]:
    """Return configuration issues for an enabled eye-tracker wrapper."""
    has_send_msg = hasattr(gaze, "send_msg") and callable(gaze.send_msg)
    has_send_message = hasattr(gaze, "send_message") and callable(gaze.send_message)
    has_message_method = has_send_msg or has_send_message
    if has_message_method:
        return []
    return ["Eye-tracker wrapper must provide send_msg(text) or send_message(text)."]

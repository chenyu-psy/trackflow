"""Eye-tracking helpers for PsychoPy experiments.

This package decomposes reusable eye-tracking behavior from the `trackNeuAct`
templates into small helpers that can be used in ordinary PsychoPy scripts.
Imports for PsychoPy and pylink stay delayed until the helper that needs them
is called, so importing `trackflow.gaze` does not require an EyeLink runtime.
"""

from .config import GazeConfig, _make_tracking_settings
from .files import (
    EYE_TRACKING_SCHEMA_VERSION,
    get_eye_tracking_entries,
    get_eye_tracking_files,
    is_edf_file_verified,
    mark_edf_transferred,
    next_edf_run_id,
    register_edf_file,
)
from .monitor import GazeBreakError
from .runtime import MOUSE_TOKENS, _split_continue_keys
from .tracker import ConnectedEyeLinker, DebugEyeLinker, setup_tracker

__all__ = [
    "ConnectedEyeLinker",
    "DebugEyeLinker",
    "EYE_TRACKING_SCHEMA_VERSION",
    "GazeBreakError",
    "GazeConfig",
    "MOUSE_TOKENS",
    "_make_tracking_settings",
    "_split_continue_keys",
    "get_eye_tracking_entries",
    "get_eye_tracking_files",
    "is_edf_file_verified",
    "mark_edf_transferred",
    "next_edf_run_id",
    "register_edf_file",
    "setup_tracker",
]

"""Eye-tracking helpers for PsychoPy experiments.

This package decomposes reusable eye-tracking behavior from the `trackNeuAct`
templates into small helpers that can be used in ordinary PsychoPy scripts.
Imports for PsychoPy and pylink stay delayed until the helper that needs them
is called, so importing `trackflow.gaze` does not require an EyeLink runtime.
"""

from .config import GazeConfig, _make_tracking_settings
from .monitor import GazeBreakError
from .runtime import MOUSE_TOKENS, _split_continue_keys
from .tracker import ConnectedEyeLinker, DebugEyeLinker, setup_tracker

__all__ = [
    "ConnectedEyeLinker",
    "DebugEyeLinker",
    "GazeBreakError",
    "GazeConfig",
    "MOUSE_TOKENS",
    "_make_tracking_settings",
    "_split_continue_keys",
    "setup_tracker",
]

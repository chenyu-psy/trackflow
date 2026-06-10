"""Behavior helpers for explicit PsychoPy experiment scripts.

The behavior package starts with small stimulus utilities that can be used in
ordinary PsychoPy code. Importing ``trackflow.beh`` does not open a PsychoPy
window or initialize hardware.
"""

from .data import DataRows
from .design import build_trial_rows, check_balance, factor_conditions
from .keys import GlobalKeyAction
from .preflight import PreflightResult, check_preflight, preflight_or_raise
from .recovery import (
    load_meta_state,
    make_meta_state,
    mark_plan_completed,
    prepare_meta_state,
    remaining_plan_rows,
    save_meta_state,
)
from .screens import Screen, make_screen
from .stimuli import FixationParams, FixationStim, Stimulus, Timing, make_fixation, wrap_stimulus
from .timeline import Timeline, setup_timeline
from .trials import RunContext, Trial, TrialOutcome

__all__ = [
    "DataRows",
    "FixationParams",
    "FixationStim",
    "GlobalKeyAction",
    "PreflightResult",
    "RunContext",
    "Screen",
    "Stimulus",
    "Timeline",
    "Timing",
    "Trial",
    "TrialOutcome",
    "build_trial_rows",
    "check_balance",
    "check_preflight",
    "factor_conditions",
    "load_meta_state",
    "make_meta_state",
    "make_fixation",
    "make_screen",
    "mark_plan_completed",
    "preflight_or_raise",
    "prepare_meta_state",
    "remaining_plan_rows",
    "save_meta_state",
    "setup_timeline",
    "wrap_stimulus",
]

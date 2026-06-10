"""Behavior helpers for explicit PsychoPy experiment scripts.

Importing ``trackflow.beh`` exposes behavior submodules without opening a
PsychoPy window or initializing hardware. Use the submodule namespace to keep
experiment scripts clear about which runtime layer they are using, for example
``beh.stimuli.make_fixation(...)`` and ``beh.screens.make_screen(...)``.
"""

from . import data, design, keys, preflight, recovery, screens, stimuli, timeline, trials

__all__ = [
    "data",
    "design",
    "keys",
    "preflight",
    "recovery",
    "screens",
    "stimuli",
    "timeline",
    "trials",
]

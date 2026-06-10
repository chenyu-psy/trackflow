"""Behavior helpers for explicit PsychoPy experiment scripts.

Importing ``trackflow.beh`` exposes the user-facing behavior submodules without
opening a PsychoPy window or initializing hardware. Use the submodule namespace
to keep experiment scripts clear about which runtime layer they are using, for
example ``beh.stimuli.make_fixation(...)`` and
``beh.timeline.setup_timeline(...)``.
"""

from . import data, design, stimuli, timeline

__all__ = [
    "data",
    "design",
    "stimuli",
    "timeline",
]

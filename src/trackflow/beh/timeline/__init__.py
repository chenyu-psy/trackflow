"""Timeline-owned behavior runtime API.

``beh.timeline`` is the public behavior runtime namespace. It owns timeline
setup, screen construction, ordered screen groups, execution, data output, and
custom trial return types.
"""

from .context import RunContext, TrackerRuntime, TrialOutcome
from .core import Timeline, setup_timeline
from .screen import Screen

__all__ = [
    "RunContext",
    "Screen",
    "Timeline",
    "TrackerRuntime",
    "TrialOutcome",
    "setup_timeline",
]

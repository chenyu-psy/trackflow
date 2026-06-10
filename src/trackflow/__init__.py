"""PsychoPy experiment framework helpers.

The package exposes small runtime modules that can be used directly from
research experiment scripts. Importing the package does not initialize hardware
or open PsychoPy windows.
"""

from ._version import __version__
from . import beh, eeg, gaze, sync

__all__ = ["__version__", "beh", "eeg", "gaze", "sync"]

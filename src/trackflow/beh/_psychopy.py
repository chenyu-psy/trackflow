"""Delayed PsychoPy imports for behavior runtime helpers.

Importing ``trackflow.beh`` should not open a PsychoPy window or require
PsychoPy display resources. These helpers import PsychoPy modules only when a
screen is actually shown or a built-in visual stimulus is created.
"""

from __future__ import annotations

from typing import Any


def load_core() -> Any:
    """Import ``psychopy.core`` when behavior timing is needed.

    Parameters
    ----------
    None

    Returns
    -------
    object
        The imported ``psychopy.core`` module.

    Raises
    ------
    RuntimeError
        If PsychoPy core cannot be imported in the current environment.
    """
    try:
        module = __import__("psychopy.core", fromlist=["core"])
    except Exception as exc:
        raise RuntimeError("psychopy.core is required to show behavior screens.") from exc
    return module


def load_event() -> Any:
    """Import ``psychopy.event`` when keyboard responses are needed.

    Parameters
    ----------
    None

    Returns
    -------
    object
        The imported ``psychopy.event`` module.

    Raises
    ------
    RuntimeError
        If PsychoPy event cannot be imported in the current environment.
    """
    try:
        module = __import__("psychopy.event", fromlist=["event"])
    except Exception as exc:
        raise RuntimeError("psychopy.event is required to collect behavior responses.") from exc
    return module


def load_visual() -> Any:
    """Import ``psychopy.visual`` when built-in behavior visuals are needed.

    Parameters
    ----------
    None

    Returns
    -------
    object
        The imported ``psychopy.visual`` module.

    Raises
    ------
    RuntimeError
        If PsychoPy visual cannot be imported in the current environment.
    """
    try:
        module = __import__("psychopy.visual", fromlist=["visual"])
    except Exception as exc:
        raise RuntimeError("psychopy.visual is required for this behavior helper.") from exc
    return module

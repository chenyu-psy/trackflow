"""Researcher global-key actions for behavior timelines.

This module keeps pause and quit shortcuts separate from participant response
keys. Modified shortcuts use PsychoPy ``event.globalKeys`` when available, and
unmodified function-key fallbacks are polled inside the screen loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


__all__ = ["GlobalKeyAction"]


@dataclass
class GlobalKeyAction:
    """One researcher key action available during behavior screens.

    Parameters
    ----------
    name : str
        Short action name stored in raw rows when ``record`` is true.
    keys : sequence[str]
        Trigger strings such as ``"ctrl + p"`` or ``"F10"``.
    set_state : dict, optional
        Timeline state fields written when the action is triggered.
    action : callable, optional
        Extra callback called with the current run context.
    end_screen : bool, optional
        Whether the current screen should stop after the action.
    screen : Screen, optional
        Optional screen to show immediately after the current screen.
    record : bool, optional
        Whether to mark the raw screen row with ``global_key_action``.
    """

    name: str
    keys: Sequence[str]
    set_state: Dict[str, Any] = field(default_factory=dict)
    action: Optional[Callable[[Any], None]] = None
    end_screen: bool = False
    screen: Optional[Any] = None
    record: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize the action definition."""
        self.name = str(self.name).strip()
        if not self.name:
            raise ValueError("global key action name must not be empty.")
        self.keys = [str(key) for key in self.keys]
        if not self.keys:
            raise ValueError("global key action requires at least one key.")
        self.set_state = dict(self.set_state or {})


def make_default_global_actions() -> List[GlobalKeyAction]:
    """Return the default researcher pause and quit actions.

    Parameters
    ----------
    None

    Returns
    -------
    list[GlobalKeyAction]
        Pause uses ``command+p``, ``ctrl+p``, and ``F10``. Quit uses
        ``command+q``, ``ctrl+q``, and ``F12``.
    """
    return [
        GlobalKeyAction(
            name="pause_requested",
            keys=["command + p", "ctrl + p", "F10"],
            set_state={"pause_experiment": True},
            end_screen=False,
        ),
        GlobalKeyAction(
            name="quit_requested",
            keys=["command + q", "ctrl + q", "F12"],
            set_state={"quit_requested": True},
            end_screen=True,
        ),
    ]


def coerce_global_actions(actions: Optional[Sequence[Any]], use_defaults: bool = True) -> List[GlobalKeyAction]:
    """Return validated global-key actions.

    Parameters
    ----------
    actions : sequence, optional
        ``GlobalKeyAction`` objects or dictionaries with matching fields.
    use_defaults : bool, optional
        Whether to use the default pause/quit actions when ``actions`` is
        omitted.

    Returns
    -------
    list[GlobalKeyAction]
        Validated actions ready for registration and polling.
    """
    if actions is None:
        if use_defaults:
            return make_default_global_actions()
        return []

    out: List[GlobalKeyAction] = []
    for action in actions:
        if isinstance(action, GlobalKeyAction):
            out.append(action)
        elif isinstance(action, dict):
            out.append(GlobalKeyAction(**action))
        else:
            raise TypeError("global_actions must contain GlobalKeyAction objects or dictionaries.")
    return out


def register_modified_shortcuts(event: Any, actions: Sequence[GlobalKeyAction], callback: Callable[[str], None]) -> None:
    """Register modified global shortcuts with PsychoPy when available.

    Parameters
    ----------
    event : psychopy.event module
        Event module that may provide ``globalKeys``.
    actions : sequence[GlobalKeyAction]
        Actions whose modified triggers should be registered.
    callback : callable
        Function called with the action name when a shortcut fires.

    Returns
    -------
    None
        Adds global-key callbacks where the PsychoPy backend supports them.
    """
    global_keys = getattr(event, "globalKeys", None)
    if global_keys is None or not hasattr(global_keys, "add"):
        return

    for action in actions:
        for key, modifiers in parse_action_keys(action):
            if not modifiers:
                continue
            _register_one_shortcut(global_keys, action.name, key, modifiers, callback)


def fallback_key_map(actions: Sequence[GlobalKeyAction]) -> Dict[str, GlobalKeyAction]:
    """Return unmodified fallback keys mapped to their actions.

    Parameters
    ----------
    actions : sequence[GlobalKeyAction]
        Global actions to inspect.

    Returns
    -------
    dict
        Mapping from normalized key names such as ``"f10"`` to actions.
    """
    key_map: Dict[str, GlobalKeyAction] = {}
    for action in actions:
        for key, modifiers in parse_action_keys(action):
            if modifiers:
                continue
            key_map[key] = action
    return key_map


def find_response_key_conflicts(screen_choices: Optional[Sequence[str]], actions: Sequence[GlobalKeyAction]) -> List[str]:
    """Return global fallback keys that overlap participant key choices.

    Parameters
    ----------
    screen_choices : sequence[str] or None
        Allowed participant key choices. ``None`` means no participant key is
        accepted.
    actions : sequence[GlobalKeyAction]
        Configured global key actions.

    Returns
    -------
    list[str]
        Conflicting unmodified global keys.
    """
    fallback_keys = sorted(fallback_key_map(actions).keys())
    if not fallback_keys:
        return []
    if screen_choices is None:
        return []

    response_keys = {normalize_key_name(key) for key in screen_choices}
    return [key for key in fallback_keys if key in response_keys]


def parse_action_keys(action: GlobalKeyAction) -> List[Tuple[str, Tuple[str, ...]]]:
    """Parse all trigger strings for one action.

    Parameters
    ----------
    action : GlobalKeyAction
        Action with researcher-friendly key strings.

    Returns
    -------
    list[tuple[str, tuple[str, ...]]]
        Normalized ``(key, modifiers)`` pairs.
    """
    return [parse_key_trigger(trigger) for trigger in action.keys]


def parse_key_trigger(trigger: str) -> Tuple[str, Tuple[str, ...]]:
    """Parse one key trigger string.

    Parameters
    ----------
    trigger : str
        Key string such as ``"ctrl + P"`` or ``"F10"``.

    Returns
    -------
    tuple
        ``(key, modifiers)`` with lowercase names and spaces removed.
    """
    parts = [part.strip().lower() for part in str(trigger).split("+")]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError("global key trigger must not be empty.")
    key = normalize_key_name(parts[-1])
    modifiers = tuple(normalize_key_name(part) for part in parts[:-1])
    return key, modifiers


def normalize_key_name(key: Any) -> str:
    """Normalize one PsychoPy key name for comparison.

    Parameters
    ----------
    key : object
        Key name returned by PsychoPy or written by the researcher.

    Returns
    -------
    str
        Lowercase key name without surrounding spaces.
    """
    return str(key).strip().lower()


def _register_one_shortcut(
    global_keys: Any,
    action_name: str,
    key: str,
    modifiers: Tuple[str, ...],
    callback: Callable[[str], None],
) -> None:
    """Register one modified shortcut, replacing an old handler if present."""
    name = f"trackflow_{action_name}_{'_'.join(modifiers)}_{key}"
    try:
        global_keys.remove(key, modifiers=list(modifiers))
    except Exception:
        pass
    try:
        global_keys.add(
            key=key,
            modifiers=list(modifiers),
            func=lambda action_name=action_name: callback(action_name),
            name=name,
        )
    except ValueError:
        # Some PsychoPy backends do not expose every modifier alias.
        return

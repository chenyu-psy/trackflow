"""Researcher global-key bindings for behavior timelines.

Quit keys are owned by trackflow and always use the built-in quit flow.
Task-level global keys are deferred requests: pressing one sets a timeline
state flag that task code can consume at an appropriate checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple


QUIT_REQUEST_NAME = "quit_requested"
DEFAULT_QUIT_KEYS = ["command + q", "ctrl + q", "F12"]

__all__ = [
    "DEFAULT_QUIT_KEYS",
    "QUIT_REQUEST_NAME",
    "build_request_bindings",
    "fallback_key_map",
    "find_response_key_conflicts",
    "register_modified_shortcuts",
]


@dataclass
class _KeyBinding:
    """Internal normalized binding from one action name to key triggers."""

    name: str
    keys: Sequence[str]

    def __post_init__(self) -> None:
        """Validate and normalize the binding."""
        self.name = str(self.name).strip()
        if not self.name:
            raise ValueError("global key binding name must not be empty.")
        self.keys = [str(key) for key in self.keys if str(key).strip()]
        if not self.keys:
            raise ValueError("global key binding requires at least one key.")


def build_request_bindings(global_key_requests: Optional[Mapping[str, Sequence[str]]]) -> List[_KeyBinding]:
    """Return validated deferred request bindings from state-name mapping."""
    bindings: List[_KeyBinding] = []
    for state_name, keys in dict(global_key_requests or {}).items():
        clean_name = str(state_name).strip()
        if clean_name == QUIT_REQUEST_NAME:
            raise ValueError("quit_requested is reserved for trackflow's built-in quit keys.")
        bindings.append(_KeyBinding(clean_name, list(keys or [])))
    return bindings


def register_modified_shortcuts(event: Any, bindings: Sequence[_KeyBinding], callback: Callable[[str], None]) -> None:
    """Register modified global shortcuts with PsychoPy when available."""
    global_keys = getattr(event, "globalKeys", None)
    if global_keys is None or not hasattr(global_keys, "add"):
        return

    for binding in bindings:
        for key, modifiers in parse_binding_keys(binding):
            if not modifiers:
                continue
            _register_one_shortcut(global_keys, binding.name, key, modifiers, callback)


def fallback_key_map(bindings: Sequence[_KeyBinding]) -> Dict[str, str]:
    """Return unmodified fallback keys mapped to binding names."""
    key_map: Dict[str, str] = {}
    for binding in bindings:
        for key, modifiers in parse_binding_keys(binding):
            if modifiers:
                continue
            key_map[key] = binding.name
    return key_map


def find_response_key_conflicts(screen_choices: Optional[Sequence[str]], bindings: Sequence[_KeyBinding]) -> List[str]:
    """Return global fallback keys that overlap participant key choices."""
    fallback_keys = sorted(fallback_key_map(bindings).keys())
    if not fallback_keys or screen_choices is None:
        return []

    response_keys = {normalize_key_name(key) for key in screen_choices}
    return [key for key in fallback_keys if key in response_keys]


def parse_binding_keys(binding: _KeyBinding) -> List[Tuple[str, Tuple[str, ...]]]:
    """Parse all trigger strings for one binding."""
    return [parse_key_trigger(trigger) for trigger in binding.keys]


def parse_key_trigger(trigger: str) -> Tuple[str, Tuple[str, ...]]:
    """Parse one key trigger such as ``"ctrl + P"`` or ``"F10"``."""
    parts = [part.strip().lower() for part in str(trigger).split("+")]
    parts = [part for part in parts if part]
    if not parts:
        raise ValueError("global key trigger must not be empty.")
    key = normalize_key_name(parts[-1])
    modifiers = tuple(normalize_key_name(part) for part in parts[:-1])
    return key, modifiers


def normalize_key_name(key: Any) -> str:
    """Normalize one PsychoPy key name for comparison."""
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
        return

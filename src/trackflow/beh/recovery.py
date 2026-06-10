"""Meta-JSON helpers for behavior recovery.

The meta file stores the planned trial rows and accepted completion IDs. It is
the authoritative source for continue-mode scheduling, while raw JSONL and
summary CSV remain the audit and analysis outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


META_VERSION = 1


def make_meta_state(
    session_info: Optional[Dict[str, Any]] = None,
    planned_rows: Optional[Sequence[Dict[str, Any]]] = None,
    session_order: Optional[Sequence[Any]] = None,
    paths: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a behavior recovery state dictionary.

    Parameters
    ----------
    session_info : dict, optional
        Stable participant/session fields.
    planned_rows : sequence[dict], optional
        Complete planned trial rows, each ideally containing ``plan_id``.
    session_order : sequence, optional
        Planned session order.
    paths : dict, optional
        Important output paths, such as raw JSONL and summary CSV.

    Returns
    -------
    dict
        JSON-compatible recovery state.
    """
    return {
        "version": META_VERSION,
        "session_info": dict(session_info or {}),
        "planned_rows": [dict(row) for row in planned_rows or []],
        "session_order": list(session_order or []),
        "completed_plan_ids": [],
        "paths": {str(key): str(value) for key, value in dict(paths or {}).items()},
    }


def save_meta_state(path: Any, state: Dict[str, Any]) -> None:
    """Write recovery state to a JSON file.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination JSON path.
    state : dict
        Recovery state to save.

    Returns
    -------
    None
        Writes ``state`` to disk.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def load_meta_state(path: Any) -> Dict[str, Any]:
    """Load and validate a recovery meta JSON file.

    Parameters
    ----------
    path : str or pathlib.Path
        Source JSON path.

    Returns
    -------
    dict
        Loaded recovery state.
    """
    in_path = Path(path)
    with in_path.open("r", encoding="utf-8") as f:
        state = json.load(f)
    version = int(state.get("version", 0) or 0)
    if version != META_VERSION:
        raise ValueError(f"Unsupported behavior meta version {version}. Expected {META_VERSION}.")
    return state


def mark_plan_completed(state: Dict[str, Any], plan_id: Any) -> None:
    """Add one accepted plan ID to recovery state.

    Parameters
    ----------
    state : dict
        In-memory recovery state.
    plan_id : object
        Stable planned trial identifier.

    Returns
    -------
    None
        Updates ``state`` in place.
    """
    plan_id_text = str(plan_id).strip()
    if not plan_id_text:
        return
    completed = {str(item) for item in state.get("completed_plan_ids", [])}
    completed.add(plan_id_text)
    state["completed_plan_ids"] = sorted(completed)


def remaining_plan_rows(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return planned rows whose ``plan_id`` has not been accepted.

    Parameters
    ----------
    state : dict
        Loaded recovery state.

    Returns
    -------
    list[dict]
        Remaining planned rows in original order.
    """
    completed = {str(item) for item in state.get("completed_plan_ids", [])}
    rows = []
    for row in state.get("planned_rows", []):
        plan_id = str(row.get("plan_id", "") or "")
        if plan_id not in completed:
            rows.append(dict(row))
    return rows


def prepare_meta_state(
    path: Any,
    action: str,
    session_info: Optional[Dict[str, Any]] = None,
    planned_rows: Optional[Sequence[Dict[str, Any]]] = None,
    session_order: Optional[Sequence[Any]] = None,
    paths: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create or load recovery state for a behavior run.

    Parameters
    ----------
    path : str or pathlib.Path
        Meta JSON path.
    action : str
        ``"continue"`` loads existing state; any other value creates a new
        state and writes it to ``path``.
    session_info, planned_rows, session_order, paths
        New-state fields passed to ``make_meta_state``.

    Returns
    -------
    dict
        Loaded or newly-created recovery state.
    """
    action_text = str(action or "new").strip().lower()
    if action_text == "continue":
        return load_meta_state(path)
    state = make_meta_state(
        session_info=session_info,
        planned_rows=planned_rows,
        session_order=session_order,
        paths=paths,
    )
    save_meta_state(path, state)
    return state

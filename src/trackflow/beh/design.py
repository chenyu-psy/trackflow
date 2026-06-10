"""Trial planning helpers for behavior experiments.

Planning helpers operate on plain dictionaries and return ``list[dict]``
trial-data values that can be passed directly to
``Timeline.run(..., trial_data=...)``. They only use explicit user inputs and
do not choose condition levels or trial counts.
"""

from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List, Optional, Sequence


__all__ = ["build_trial_rows", "check_balance", "factor_conditions"]


def factor_conditions(factors: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand a factor-to-level mapping into condition rows.

    Parameters
    ----------
    factors : dict
        Mapping from factor names to one value or a list/tuple of values.

    Returns
    -------
    list[dict]
        One row per condition combination.

    Examples
    --------
    >>> factor_conditions({"set_size": [2, 4], "task": "color"})
    [{'set_size': 2, 'task': 'color'}, {'set_size': 4, 'task': 'color'}]
    """
    if not isinstance(factors, dict):
        raise TypeError("factors must be a dictionary.")
    if not factors:
        return [{}]
    names = list(factors.keys())
    levels = []
    for name in names:
        value = factors[name]
        if isinstance(value, (list, tuple)):
            levels.append(list(value))
        else:
            levels.append([value])

    rows = []
    for combo in itertools.product(*levels):
        row = {}
        for idx, name in enumerate(names):
            row[name] = combo[idx]
        rows.append(row)
    return rows


def build_trial_rows(
    conditions: Sequence[Dict[str, Any]],
    repeats: int = 1,
    session_by: Optional[Any] = None,
    session_size: Optional[int] = None,
    block_size: Optional[int] = None,
    random_order: bool = False,
    seed: Optional[int] = None,
    plan_prefix: str = "trial",
) -> List[Dict[str, Any]]:
    """Build runtime-ready trial-data dictionaries.

    Parameters
    ----------
    conditions : sequence[dict]
        Explicit condition rows to repeat and schedule.
    repeats : int, optional
        Number of times to repeat each condition row.
    session_by : str or sequence[str], optional
        Field name or names that define sessions.
    session_size : int, optional
        Number of rows per session when not grouping by fields.
    block_size : int, optional
        Number of rows per block within each session.
    random_order : bool, optional
        Whether to shuffle rows within each session.
    seed : int, optional
        Seed for reproducible shuffling.
    plan_prefix : str, optional
        Prefix used for stable ``plan_id`` values.

    Returns
    -------
    list[dict]
        Trial-data dictionaries with ``plan_id``, ``session_id``, ``block_id``,
        ``trial_id``, and ``session_trial_id``.
    """
    _validate_build_inputs(conditions, repeats, session_size, block_size)
    base_rows = _repeat_conditions(conditions, repeats)
    grouped = _group_sessions(base_rows, session_by=session_by, session_size=session_size)
    rng = random.Random(seed)

    planned_rows: List[Dict[str, Any]] = []
    for session_idx, session_rows in enumerate(grouped, start=1):
        rows = [dict(row) for row in session_rows]
        if random_order:
            rng.shuffle(rows)
        planned_rows.extend(_assign_ids(rows, session_idx=session_idx, block_size=block_size))

    for idx, row in enumerate(planned_rows, start=1):
        row["plan_id"] = f"{plan_prefix}_{idx:04d}"
    return planned_rows


def check_balance(rows: Sequence[Dict[str, Any]], fields: Sequence[str]) -> Dict[Any, int]:
    """Count rows for combinations of selected fields.

    Parameters
    ----------
    rows : sequence[dict]
        Planned or condition rows to inspect.
    fields : sequence[str]
        Field names that define the balance cells.

    Returns
    -------
    dict
        Mapping from field-value tuples to counts.
    """
    field_list = [str(field) for field in fields]
    counts: Dict[Any, int] = {}
    for row in rows:
        key = tuple(row.get(field) for field in field_list)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _validate_build_inputs(
    conditions: Sequence[Dict[str, Any]],
    repeats: int,
    session_size: Optional[int],
    block_size: Optional[int],
) -> None:
    """Validate planning inputs before building rows."""
    if conditions is None:
        raise ValueError("conditions must be provided.")
    for row in conditions:
        if not isinstance(row, dict):
            raise TypeError("each condition row must be a dictionary.")
    if int(repeats) < 1:
        raise ValueError("repeats must be at least 1.")
    if session_size is not None and int(session_size) < 1:
        raise ValueError("session_size must be at least 1.")
    if block_size is not None and int(block_size) < 1:
        raise ValueError("block_size must be at least 1.")


def _repeat_conditions(conditions: Sequence[Dict[str, Any]], repeats: int) -> List[Dict[str, Any]]:
    """Return repeated copies of explicit condition rows."""
    rows: List[Dict[str, Any]] = []
    for condition in conditions:
        for _ in range(int(repeats)):
            rows.append(dict(condition))
    return rows


def _group_sessions(
    rows: Sequence[Dict[str, Any]],
    session_by: Optional[Any],
    session_size: Optional[int],
) -> List[List[Dict[str, Any]]]:
    """Group rows into sessions by fields or fixed session size."""
    if session_by is not None and session_size is not None:
        raise ValueError("Use session_by or session_size, not both.")
    if session_by is not None:
        fields = [session_by] if isinstance(session_by, str) else list(session_by)
        groups: Dict[Any, List[Dict[str, Any]]] = {}
        order = []
        for row in rows:
            key = tuple(row.get(field) for field in fields)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(dict(row))
        return [groups[key] for key in order]
    if session_size is not None:
        size = int(session_size)
        return [[dict(row) for row in rows[idx : idx + size]] for idx in range(0, len(rows), size)]
    return [[dict(row) for row in rows]]


def _assign_ids(rows: Sequence[Dict[str, Any]], session_idx: int, block_size: Optional[int]) -> List[Dict[str, Any]]:
    """Assign session, block, and trial IDs within one session."""
    if not rows:
        return []
    size = int(block_size) if block_size is not None else len(rows)
    planned: List[Dict[str, Any]] = []
    session_trial_id = 1
    block_id = 1
    for start in range(0, len(rows), size):
        block_rows = rows[start : start + size]
        for trial_id, row in enumerate(block_rows, start=1):
            out = dict(row)
            out["session_id"] = int(session_idx)
            out["block_id"] = int(block_id)
            out["trial_id"] = int(trial_id)
            out["session_trial_id"] = int(session_trial_id)
            planned.append(out)
            session_trial_id += 1
        block_id += 1
    return planned

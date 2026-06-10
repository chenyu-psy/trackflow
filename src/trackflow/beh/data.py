"""Data row helpers for behavior runtime output.

The behavior runtime stores raw screen rows as JSON-compatible dictionaries.
Optional trial-level summaries are written to CSV for researcher-facing
analysis and inspection.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


__all__ = ["DataRows"]


class DataRows:
    """Small query view over completed behavior rows.

    Parameters
    ----------
    rows : iterable[dict], optional
        Rows to include in the view. Each row is copied so later filtering does
        not mutate timeline storage.

    Returns
    -------
    DataRows
        Queryable row view.

    Examples
    --------
    >>> rows = DataRows([{"trial_id": 1, "screen_name": "test"}])
    >>> rows.filter(trial_id=1).to_list()
    [{'trial_id': 1, 'screen_name': 'test'}]
    """

    def __init__(self, rows: Optional[Iterable[Dict[str, Any]]] = None) -> None:
        """Store copied rows for lightweight querying."""
        self._rows = [dict(row) for row in rows or []]

    def filter(self, **fields: Any) -> "DataRows":
        """Return rows whose fields match all requested values.

        Parameters
        ----------
        **fields
            Field names and exact values to match.

        Returns
        -------
        DataRows
            New view containing only matching rows.
        """
        matching_rows = []
        for row in self._rows:
            keep = True
            for key, value in fields.items():
                if row.get(key) != value:
                    keep = False
                    break
            if keep:
                matching_rows.append(row)
        return DataRows(matching_rows)

    def to_list(self) -> List[Dict[str, Any]]:
        """Return copied rows as a plain list of dictionaries.

        Returns
        -------
        list[dict]
            Copied rows in their current order.
        """
        return [dict(row) for row in self._rows]

    def to_pandas(self) -> Any:
        """Convert rows to a pandas ``DataFrame``.

        Returns
        -------
        pandas.DataFrame
            Tabular view of the rows.
        """
        pd = _load_pandas()
        return pd.DataFrame(self.to_list())


class SummaryWriter:
    """Append trial summary rows to a fixed-schema CSV file.

    Parameters
    ----------
    path : str or pathlib.Path
        CSV file path.
    fieldnames : list[str], optional
        Existing fixed schema. If omitted, the first row establishes the
        schema.

    Returns
    -------
    SummaryWriter
        Writer that validates later rows against the first row schema.
    """

    def __init__(self, path: Any, fieldnames: Optional[List[str]] = None) -> None:
        """Create a summary CSV writer."""
        self.path = Path(path)
        self.fieldnames = list(fieldnames) if fieldnames is not None else None

    def append(self, row: Dict[str, Any]) -> None:
        """Validate and append one summary row.

        Parameters
        ----------
        row : dict
            One trial-level summary row.

        Returns
        -------
        None
            Writes the row to ``self.path``.
        """
        row = validate_summary_row(row)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.fieldnames is None:
            self.fieldnames = list(row.keys())
            write_header = True
        else:
            write_header = not self.path.exists()
            extra = [key for key in row.keys() if key not in self.fieldnames]
            if extra:
                raise ValueError(
                    "summary row has new columns after the CSV schema was fixed: "
                    + ", ".join(str(key) for key in extra)
                )

        out_row = {key: row.get(key, "") for key in self.fieldnames}
        with self.path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(out_row)


def append_jsonl(path: Any, row: Dict[str, Any]) -> None:
    """Append one raw behavior row to a JSONL file.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination JSONL path.
    row : dict
        JSON-compatible row to write.

    Returns
    -------
    None
        Appends one line to ``path``.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        f.write("\n")


def load_jsonl(path: Any) -> List[Dict[str, Any]]:
    """Load behavior rows from a JSONL file if it exists.

    Parameters
    ----------
    path : str or pathlib.Path
        Source JSONL path.

    Returns
    -------
    list[dict]
        Parsed rows. Missing files return an empty list.
    """
    in_path = Path(path)
    if not in_path.exists():
        return []
    rows = []
    with in_path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def validate_summary_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Validate one summary row with pandas-compatible tabular rules.

    Parameters
    ----------
    row : dict
        Candidate summary row returned by ``data_format(data)``.

    Returns
    -------
    dict
        Copied row after validation.
    """
    if not isinstance(row, dict):
        raise TypeError("data_format(data) must return one dictionary.")
    pd = _load_pandas()
    try:
        pd.DataFrame([dict(row)])
    except Exception as exc:
        raise ValueError("data_format(data) returned a row that cannot be written as a table.") from exc
    return dict(row)


def _load_pandas() -> Any:
    """Import pandas only when summary tables are used.

    Returns
    -------
    object
        Imported pandas module.
    """
    try:
        module = __import__("pandas")
    except Exception as exc:
        raise RuntimeError("pandas is required for behavior summary CSV output.") from exc
    return module

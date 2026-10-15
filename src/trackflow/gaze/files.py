"""EyeLink EDF metadata helpers for restart-safe experiment workflows."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from typing import Any, Dict, List

from .config import _validate_edf_name


EYE_TRACKING_SCHEMA_VERSION = 1

__all__ = [
    "EYE_TRACKING_SCHEMA_VERSION",
    "get_eye_tracking_entries",
    "get_eye_tracking_files",
    "is_edf_file_verified",
    "mark_edf_transferred",
    "next_edf_run_id",
    "register_edf_file",
]


def get_eye_tracking_entries(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return copied EDF registry entries ordered by run ID."""
    registry = _get_registry(state, create=False)
    if registry is None:
        return []
    return sorted(
        [dict(entry) for entry in registry["files"]],
        key=lambda entry: int(entry["run_id"]),
    )


def next_edf_run_id(state: Dict[str, Any]) -> int:
    """Return the next positive run ID in an EyeLink EDF registry."""
    entries = get_eye_tracking_entries(state)
    if not entries:
        return 1
    return max(int(entry["run_id"]) for entry in entries) + 1


def register_edf_file(
    state: Dict[str, Any],
    *,
    run_id: int,
    filename: str,
    host_filename: str,
) -> Dict[str, Any]:
    """Register one pending EyeLink EDF using portable relative filenames."""
    run_id = int(run_id)
    if run_id <= 0:
        raise ValueError("run_id must be a positive integer.")
    filename = _validate_local_filename(filename)
    host_filename = str(host_filename)
    _validate_edf_name(host_filename)

    registry = _get_registry(state, create=True)
    entries = registry["files"]
    for entry in entries:
        if int(entry["run_id"]) == run_id:
            raise ValueError(f"EyeLink run_id {run_id} is already registered.")
        if str(entry["filename"]) == filename:
            raise ValueError(f"EyeLink filename {filename!r} is already registered.")
        if str(entry["host_filename"]) == host_filename:
            raise ValueError(f"EyeLink host filename {host_filename!r} is already registered.")

    entry = {
        "run_id": run_id,
        "filename": filename,
        "host_filename": host_filename,
        "status": "registered",
    }
    entries.append(entry)
    entries.sort(key=lambda item: int(item["run_id"]))
    return dict(entry)


def mark_edf_transferred(state: Dict[str, Any], run_id: int, path: Any) -> Dict[str, Any]:
    """Mark one registered EDF transferred after recording its size and SHA-256."""
    registry = _get_registry(state, create=False)
    if registry is None:
        raise KeyError("EyeLink EDF registry is missing.")
    entry = _find_entry(registry["files"], int(run_id))
    edf_path = Path(path)
    if edf_path.name != str(entry["filename"]):
        raise ValueError("transferred EDF path does not match its registered filename.")
    try:
        file_stat = edf_path.stat()
    except OSError as exc:
        raise ValueError("transferred EDF must be a non-empty file.") from exc
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size <= 0:
        raise ValueError("transferred EDF must be a non-empty file.")
    entry["status"] = "transferred"
    entry["size_bytes"] = int(file_stat.st_size)
    entry["sha256"] = _sha256(edf_path)
    return dict(entry)


def is_edf_file_verified(entry: Dict[str, Any], subject_dir: Any) -> bool:
    """Return whether one transferred registry entry matches its local EDF."""
    if str(entry.get("status", "")) != "transferred":
        return False
    try:
        filename = _validate_local_filename(entry["filename"])
        expected_size = int(entry["size_bytes"])
        expected_hash = str(entry["sha256"])
    except (KeyError, TypeError, ValueError):
        return False
    path = Path(subject_dir) / filename
    if not path.is_file() or path.stat().st_size != expected_size:
        return False
    return bool(expected_hash) and _sha256(path) == expected_hash


def get_eye_tracking_files(meta_path: Any, subject_dir: Any) -> List[Path]:
    """Return verified EDF paths from metadata, with legacy single-file fallback."""
    with Path(meta_path).open("r", encoding="utf-8") as f:
        state = json.load(f)
    if not isinstance(state, dict):
        raise ValueError("EyeLink metadata must contain a JSON object.")

    if "eye_tracking" not in state:
        legacy_path = Path(subject_dir) / f"{Path(subject_dir).name}.edf"
        return [legacy_path] if legacy_path.is_file() and legacy_path.stat().st_size > 0 else []

    return [
        Path(subject_dir) / str(entry["filename"])
        for entry in get_eye_tracking_entries(state)
        if is_edf_file_verified(entry, subject_dir)
    ]


def _get_registry(state: Dict[str, Any], create: bool) -> Dict[str, Any] | None:
    """Return and validate the optional EyeLink registry in one meta-state object."""
    registry = state.get("eye_tracking")
    if registry is None:
        if not create:
            return None
        registry = {"schema_version": EYE_TRACKING_SCHEMA_VERSION, "files": []}
        state["eye_tracking"] = registry
    if not isinstance(registry, dict):
        raise ValueError("eye_tracking metadata must be a dictionary.")
    version = int(registry.get("schema_version", 0) or 0)
    if version != EYE_TRACKING_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported eye_tracking schema version {version}. "
            f"Expected {EYE_TRACKING_SCHEMA_VERSION}."
        )
    files = registry.get("files")
    if not isinstance(files, list):
        raise ValueError("eye_tracking.files must be a list.")
    return registry


def _find_entry(entries: List[Dict[str, Any]], run_id: int) -> Dict[str, Any]:
    """Return one mutable registry entry by run ID."""
    for entry in entries:
        if int(entry.get("run_id", 0) or 0) == int(run_id):
            return entry
    raise KeyError(f"EyeLink run_id {run_id} is not registered.")


def _validate_local_filename(filename: Any) -> str:
    """Return one portable subject-directory EDF filename."""
    text = str(filename)
    if not text or "/" in text or "\\" in text or Path(text).name != text:
        raise ValueError("EyeLink filename must be relative to the subject directory.")
    if not text.endswith(".edf"):
        raise ValueError("EyeLink filename must include the .edf extension.")
    return text


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one local EDF file."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

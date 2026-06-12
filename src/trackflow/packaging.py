"""Project packaging helpers for deployment-time ``trackflow`` vendoring."""

from __future__ import annotations

import ast
import fnmatch
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Union

from ._version import __version__


DEFAULT_CONFIG_NAME = "packaging_config.py"
MTIME_TOLERANCE_SECONDS = 2.1
MACOS_TEMP_FILE_PATTERNS = ("._*", ".DS_Store")
MANIFEST_NAME = "trackflow_vendored.json"


@dataclass(frozen=True)
class LauncherConfig:
    """Normalized launcher settings for one runnable entry in a project."""

    launcher_name: str
    settings_path: Path
    entry_script: Path
    python: Optional[str]
    settings_overrides: Mapping[str, Any]


@dataclass(frozen=True)
class PackageConfig:
    """Normalized project-level package settings."""

    project_name: str
    config_path: Path
    project_root: Path
    destination: Path
    paths: Sequence[Path]
    settings_overrides: Mapping[str, Any]
    launchers: Sequence[LauncherConfig]


@dataclass(frozen=True)
class PackageSummary:
    """Summary of a package operation for CLI reporting and tests."""

    project_name: str
    project_root: Path
    destination: Path
    config_path: Path
    launcher_paths: Sequence[Path]
    manifest_path: Path
    checked_files: int
    copied_files: int
    skipped_files: int
    removed_temp_files: int
    dry_run: bool


def load_package_config(
    *,
    config_path: Union[Path, str] = DEFAULT_CONFIG_NAME,
    destination: Optional[Union[Path, str]] = None,
) -> PackageConfig:
    """Read and validate project-level packaging settings.

    The config file is parsed statically. It must define literal top-level
    values such as ``PROJECT_NAME``, ``DESTINATION``, ``PATHS``,
    ``SETTINGS_OVERRIDES``, and ``LAUNCHERS``.
    """
    resolved_config = Path(config_path).expanduser().resolve()
    if not resolved_config.is_file():
        raise FileNotFoundError(f"Packaging config not found: {resolved_config}")

    project_root = find_project_root(resolved_config)
    values = _read_static_config(resolved_config)
    project_name = str(values.get("PROJECT_NAME") or project_root.name)
    destination_path = _resolve_destination(project_root, values, destination)
    paths = _read_path_list(values.get("PATHS", []), "PATHS")
    if not paths:
        raise ValueError("PATHS must list at least one project path to package.")

    settings_overrides = _read_overrides(values.get("SETTINGS_OVERRIDES", {}), "SETTINGS_OVERRIDES")
    launchers = _read_launchers(values.get("LAUNCHERS"), settings_overrides)

    all_paths = [
        *paths,
        resolved_config.relative_to(project_root),
        *(launcher.settings_path for launcher in launchers),
        *(launcher.entry_script for launcher in launchers),
    ]
    for rel_path in all_paths:
        _validate_relative_project_path(rel_path, "package path")

    return PackageConfig(
        project_name=project_name,
        config_path=resolved_config,
        project_root=project_root,
        destination=destination_path,
        paths=tuple(paths),
        settings_overrides=settings_overrides,
        launchers=tuple(launchers),
    )


def package_project(
    *,
    config_path: Union[Path, str] = DEFAULT_CONFIG_NAME,
    destination: Optional[Union[Path, str]] = None,
    dry_run: bool = False,
) -> PackageSummary:
    """Copy one configured project and vendor ``trackflow`` into the result."""
    config = load_package_config(config_path=config_path, destination=destination)
    _validate_destination(config.project_root, config.destination)
    rel_paths = select_package_files(config)

    copied_count = 0
    skipped_count = 0
    removed_temp_count = 0

    if dry_run:
        return _make_summary(
            config,
            checked_files=len(rel_paths),
            copied_files=0,
            skipped_files=0,
            removed_temp_files=0,
            dry_run=True,
        )

    config.destination.mkdir(parents=True, exist_ok=True)
    for rel_path in rel_paths:
        src_file = config.project_root / rel_path
        dst_file = config.destination / rel_path
        if not src_file.is_file():
            continue
        if _same_enough(src_file, dst_file):
            skipped_count += 1
            continue
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        copied_count += 1

    apply_settings_overrides(config)
    vendor_trackflow(config.destination)
    for launcher in config.launchers:
        write_launcher(config, launcher)
    write_manifest(config)
    removed_temp_count = remove_macos_temp_files(config.destination)

    return _make_summary(
        config,
        checked_files=len(rel_paths),
        copied_files=copied_count,
        skipped_files=skipped_count,
        removed_temp_files=removed_temp_count,
        dry_run=False,
    )


def find_project_root(path: Path) -> Path:
    """Find the project root for a packaging config or experiment file."""
    for candidate in [path.parent, *path.parents]:
        if (candidate / ".git").exists():
            return candidate.resolve()
    for candidate in [path.parent, *path.parents]:
        if (candidate / "src").is_dir():
            return candidate.resolve()
    raise ValueError(
        f"Could not find a project root above {path}. "
        "Expected a git repository or a folder containing src/."
    )


def select_package_files(config: PackageConfig) -> List[Path]:
    """Select configured project files while respecting gitignore rules."""
    git_visible = set(list_files_respecting_gitignore(config.project_root))
    selected_roots = {
        *config.paths,
        config.config_path.relative_to(config.project_root),
        *(launcher.settings_path for launcher in config.launchers),
        *(launcher.entry_script for launcher in config.launchers),
    }

    rel_paths = [
        rel_path
        for rel_path in sorted(git_visible)
        if any(_path_matches_selection(rel_path, root) for root in selected_roots)
    ]
    missing = [
        path
        for path in selected_roots
        if not any(_path_matches_selection(rel_path, path) for rel_path in rel_paths)
    ]
    if missing:
        missing_text = ", ".join(path.as_posix() for path in missing)
        raise FileNotFoundError(
            "Configured package paths were not found among git-visible files: "
            f"{missing_text}"
        )
    return rel_paths


def list_files_respecting_gitignore(project_root: Path) -> List[Path]:
    """List tracked and untracked project files while respecting ``.gitignore``."""
    command = ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    result = subprocess.run(command, cwd=project_root, check=False, capture_output=True)
    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            "Failed to list project files with git. "
            f"Run packaging from a git project or initialize git first. {stderr_text}"
        )

    rel_paths: List[Path] = []
    for item in result.stdout.split(b"\x00"):
        if item:
            rel_paths.append(Path(item.decode("utf-8", errors="strict")))
    return rel_paths


def apply_settings_overrides(config: PackageConfig) -> None:
    """Apply deployment overrides to copied settings files, if configured."""
    for settings_path, overrides in _settings_overrides_by_path(config).items():
        if not overrides:
            continue
        copied_settings_path = config.destination / settings_path
        settings_text = copied_settings_path.read_text(encoding="utf-8")
        updated_text = rewrite_settings_text(
            settings_text,
            overrides,
            source_label=str(settings_path),
        )
        copied_settings_path.write_text(updated_text, encoding="utf-8")


def rewrite_settings_text(
    settings_text: str,
    overrides: Mapping[str, Any],
    *,
    source_label: str = "settings.py",
) -> str:
    """Rewrite literal values inside top-level settings dictionaries."""
    if not overrides:
        return settings_text

    module = ast.parse(settings_text, filename=source_label)
    replacements = []
    for dotted_key, value in overrides.items():
        block_name, setting_key = _split_override_key(dotted_key)
        block = _find_literal_dict_assignment(module, block_name, source_label)
        _, value_node = _find_literal_dict_item(block, block_name, setting_key, source_label)
        _ensure_literal(value_node, dotted_key, source_label)
        replacement_text = _format_literal_value(value, dotted_key)
        replacements.append((_node_range(settings_text, value_node), replacement_text))

    updated_text = settings_text
    for (start, end), replacement_text in sorted(replacements, reverse=True):
        updated_text = updated_text[:start] + replacement_text + updated_text[end:]

    ast.parse(updated_text, filename=source_label)
    _verify_rewritten_overrides(updated_text, overrides, source_label)
    return updated_text


def vendor_trackflow(destination: Path) -> None:
    """Copy this package's source tree into ``destination/trackflow``."""
    source = Path(__file__).resolve().parent
    target = destination / "trackflow"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=_ignore_python_cache)


def write_launcher(config: PackageConfig, launcher: LauncherConfig) -> Path:
    """Write one Windows launcher for the configured project."""
    launcher_path = config.destination / launcher.launcher_name
    launcher_path.write_text(_render_launcher(launcher), encoding="utf-8", newline="\r\n")
    return launcher_path


def write_manifest(config: PackageConfig) -> Path:
    """Write a JSON manifest describing the vendored package copy."""
    manifest_path = config.destination / MANIFEST_NAME
    payload = {
        "trackflow_version": __version__,
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "source_project": str(config.project_root),
        "destination": str(config.destination),
        "config_path": str(config.config_path.relative_to(config.project_root)),
        "project_name": config.project_name,
        "paths": [path.as_posix() for path in config.paths],
        "settings_overrides": dict(config.settings_overrides),
        "launchers": {
            launcher.launcher_name: {
                "settings": launcher.settings_path.as_posix(),
                "entry_script": launcher.entry_script.as_posix(),
                "python": launcher.python,
                "settings_overrides": dict(launcher.settings_overrides),
            }
            for launcher in config.launchers
        },
        "vendored_package": "trackflow",
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def remove_macos_temp_files(destination: Path) -> int:
    """Remove macOS metadata files from a copied deployment folder."""
    removed_count = 0
    for pattern in MACOS_TEMP_FILE_PATTERNS:
        for temp_file in destination.rglob(pattern):
            if temp_file.is_file():
                temp_file.unlink(missing_ok=True)
                removed_count += 1
    return removed_count


def _read_static_config(config_path: Path) -> Dict[str, Any]:
    """Read literal top-level package config values without executing the file."""
    module = ast.parse(config_path.read_text(encoding="utf-8"), filename=str(config_path))
    values: Dict[str, Any] = {}
    allowed_names = {
        "PROJECT_NAME",
        "DESTINATION",
        "PATHS",
        "SETTINGS_OVERRIDES",
        "LAUNCHERS",
    }
    for node in module.body:
        target_name = _single_assignment_name(node)
        if target_name not in allowed_names:
            continue
        try:
            values[target_name] = ast.literal_eval(node.value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{target_name} in {config_path} must be a literal value for packaging."
            ) from exc
    return values


def _single_assignment_name(node: ast.AST) -> Optional[str]:
    """Return the simple name assigned by ``node`` when it has one."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _resolve_destination(
    project_root: Path,
    values: Mapping[str, Any],
    destination: Optional[Union[Path, str]],
) -> Path:
    """Resolve the destination path from CLI override or project config."""
    configured_destination = destination if destination is not None else values.get("DESTINATION")
    if not configured_destination:
        raise ValueError("Define DESTINATION or pass --destination.")

    destination_path = Path(str(configured_destination)).expanduser()
    if not destination_path.is_absolute():
        destination_path = (project_root / destination_path).resolve()
    else:
        destination_path = destination_path.resolve()
    return destination_path


def _read_launchers(value: Any, project_overrides: Mapping[str, Any]) -> List[LauncherConfig]:
    """Read launcher definitions from project config."""
    if not isinstance(value, dict) or not value:
        raise ValueError("LAUNCHERS must be a non-empty dictionary.")
    launchers = []
    for launcher_name, launcher_config in value.items():
        launcher_name = str(launcher_name)
        if Path(launcher_name).name != launcher_name or not launcher_name.lower().endswith(".bat"):
            raise ValueError(f'Launcher "{launcher_name}" must be a .bat filename.')
        if not isinstance(launcher_config, dict):
            raise ValueError(f'LAUNCHERS["{launcher_name}"] must be a dictionary.')
        settings_path = _required_relative_path(launcher_config, "settings", launcher_name)
        entry_script = _required_relative_path(launcher_config, "entry_script", launcher_name)
        python_path = launcher_config.get("python")
        if python_path is not None:
            python_path = str(python_path)
        launcher_overrides = _read_overrides(
            launcher_config.get("settings_overrides", {}),
            f'LAUNCHERS["{launcher_name}"]["settings_overrides"]',
        )
        launchers.append(
            LauncherConfig(
                launcher_name=launcher_name,
                settings_path=settings_path,
                entry_script=entry_script,
                python=python_path,
                settings_overrides=launcher_overrides,
            )
        )
    return launchers


def _required_relative_path(config: Mapping[str, Any], field: str, label: str) -> Path:
    """Read one required project-relative path field."""
    value = config.get(field)
    if not value:
        raise ValueError(f'{label} must define "{field}".')
    path = Path(str(value))
    _validate_relative_project_path(path, field)
    return path


def _read_path_list(value: Any, label: str) -> List[Path]:
    """Normalize a package path list from static config."""
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list of relative project paths.")
    paths = []
    for item in value:
        path = Path(str(item))
        _validate_relative_project_path(path, label)
        paths.append(path)
    return paths


def _read_overrides(value: Any, label: str) -> Dict[str, Any]:
    """Read settings overrides from static config."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a dictionary when provided.")
    overrides = {str(key): override_value for key, override_value in value.items()}
    for dotted_key, override_value in overrides.items():
        _split_override_key(dotted_key)
        _format_literal_value(override_value, dotted_key)
    return overrides


def _settings_overrides_by_path(config: PackageConfig) -> Dict[Path, Dict[str, Any]]:
    """Return effective settings overrides grouped by copied settings file."""
    grouped: Dict[Path, Dict[str, Any]] = {}
    for launcher in config.launchers:
        effective = dict(config.settings_overrides)
        effective.update(launcher.settings_overrides)
        current = grouped.setdefault(launcher.settings_path, {})
        for key, value in effective.items():
            if key in current and current[key] != value:
                raise ValueError(
                    f'Conflicting settings override for "{key}" in {launcher.settings_path}.'
                )
            current[key] = value
    return grouped


def _validate_relative_project_path(path: Path, label: str) -> None:
    """Reject absolute paths and parent traversal in project-relative config paths."""
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError(f"{label} must be relative to the project root: {path}")


def _validate_destination(project_root: Path, destination: Path) -> None:
    """Reject destinations that would recursively copy the project into itself."""
    if destination == project_root:
        raise ValueError("Package destination cannot be the project root.")
    if _is_relative_to(destination, project_root):
        raise ValueError("Package destination cannot be inside the source project.")


def _path_matches_selection(rel_path: Path, selected_path: Path) -> bool:
    """Return whether a git-visible path is selected by one configured root."""
    return rel_path == selected_path or _is_relative_to(rel_path, selected_path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether ``path`` is inside ``parent`` across supported Python versions."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _same_enough(src_file: Path, dst_file: Path) -> bool:
    """Return whether the destination file is close enough to skip copying."""
    if not dst_file.exists() or not dst_file.is_file():
        return False
    src_stat = src_file.stat()
    dst_stat = dst_file.stat()
    same_size = src_stat.st_size == dst_stat.st_size
    mtime_diff = abs(src_stat.st_mtime - dst_stat.st_mtime)
    return same_size and mtime_diff <= MTIME_TOLERANCE_SECONDS


def _split_override_key(dotted_key: str) -> tuple[str, str]:
    """Split an override key of the form ``BLOCK.key``."""
    parts = dotted_key.split(".")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f'Settings override "{dotted_key}" must use BLOCK.key format.')
    block_name, setting_key = parts
    if not block_name.isidentifier():
        raise ValueError(f'Settings override block "{block_name}" is not a valid name.')
    return block_name, setting_key


def _find_literal_dict_assignment(
    module: ast.Module,
    block_name: str,
    source_label: str,
) -> ast.Dict:
    """Find a top-level literal dict assignment by name."""
    for node in module.body:
        if _single_assignment_name(node) != block_name:
            continue
        value = node.value
        if not isinstance(value, ast.Dict):
            raise ValueError(f"{block_name} in {source_label} must be a literal dictionary.")
        _ensure_literal(value, block_name, source_label)
        return value
    raise ValueError(f"{source_label} does not define a {block_name} settings block.")


def _find_literal_dict_item(
    block: ast.Dict,
    block_name: str,
    setting_key: str,
    source_label: str,
) -> tuple[ast.AST, ast.AST]:
    """Find one literal string key inside a settings dictionary."""
    for key_node, value_node in zip(block.keys, block.values):
        if key_node is None:
            raise ValueError(f"{block_name} in {source_label} cannot use dictionary unpacking.")
        try:
            key_value = ast.literal_eval(key_node)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{block_name} in {source_label} must use literal string keys."
            ) from exc
        if key_value == setting_key:
            return key_node, value_node
    raise ValueError(f'{block_name} in {source_label} does not define key "{setting_key}".')


def _ensure_literal(node: ast.AST, label: str, source_label: str) -> None:
    """Require a node to be safely readable as a Python literal."""
    try:
        ast.literal_eval(node)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} in {source_label} must be a literal value.") from exc


def _format_literal_value(value: Any, dotted_key: str) -> str:
    """Format one override value as a Python literal."""
    try:
        text = repr(value)
        parsed = ast.parse(text, mode="eval")
        ast.literal_eval(parsed.body)
    except (SyntaxError, TypeError, ValueError) as exc:
        raise ValueError(f'Override "{dotted_key}" must be a literal value.') from exc
    return text


def _node_range(source_text: str, node: ast.AST) -> tuple[int, int]:
    """Return absolute character offsets for one AST node."""
    if (
        getattr(node, "lineno", None) is None
        or getattr(node, "col_offset", None) is None
        or getattr(node, "end_lineno", None) is None
        or getattr(node, "end_col_offset", None) is None
    ):
        raise ValueError("Could not locate settings value for replacement.")
    line_starts = [0]
    for line in source_text.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))
    start = line_starts[node.lineno - 1] + node.col_offset
    end = line_starts[node.end_lineno - 1] + node.end_col_offset
    return start, end


def _verify_rewritten_overrides(
    settings_text: str,
    overrides: Mapping[str, Any],
    source_label: str,
) -> None:
    """Verify that rewritten settings contain the requested literal values."""
    module = ast.parse(settings_text, filename=source_label)
    for dotted_key, expected in overrides.items():
        block_name, setting_key = _split_override_key(dotted_key)
        block = _find_literal_dict_assignment(module, block_name, source_label)
        _, value_node = _find_literal_dict_item(block, block_name, setting_key, source_label)
        actual = ast.literal_eval(value_node)
        if actual != expected:
            raise RuntimeError(f'Failed to apply settings override "{dotted_key}".')


def _ignore_python_cache(directory: str, names: Iterable[str]) -> Set[str]:
    """Ignore generated Python cache files while vendoring ``trackflow``."""
    ignored = set()
    for name in names:
        if name == "__pycache__" or fnmatch.fnmatch(name, "*.pyc"):
            ignored.add(name)
    return ignored


def _windows_path(path: Path) -> str:
    """Render a relative path with Windows separators for batch files."""
    return str(path).replace("/", "\\")


def _make_summary(
    config: PackageConfig,
    *,
    checked_files: int,
    copied_files: int,
    skipped_files: int,
    removed_temp_files: int,
    dry_run: bool,
) -> PackageSummary:
    """Create the public summary object for a package run."""
    return PackageSummary(
        project_name=config.project_name,
        project_root=config.project_root,
        destination=config.destination,
        config_path=config.config_path,
        launcher_paths=tuple(config.destination / launcher.launcher_name for launcher in config.launchers),
        manifest_path=config.destination / MANIFEST_NAME,
        checked_files=checked_files,
        copied_files=copied_files,
        skipped_files=skipped_files,
        removed_temp_files=removed_temp_files,
        dry_run=dry_run,
    )


def _render_launcher(launcher: LauncherConfig) -> str:
    """Render the Windows launcher body."""
    configured_python = launcher.python or ""
    experiment_label = Path(launcher.launcher_name).stem
    entry_script = _windows_path(launcher.entry_script)
    entry_dir = _windows_path(launcher.entry_script.parent)
    return f"""@echo off
setlocal

REM Run {experiment_label} from this project folder on offline Windows PCs.
REM Generated by trackflow package.

cd /d "%~dp0"
set "ENTRY_SCRIPT=%~dp0{entry_script}"
set "ENTRY_DIR=%~dp0{entry_dir}"
set "PSYCHOPY_USER_DIR=%~dp0.psychopy"
set "CONFIGURED_PY={configured_python}"
set "SYSTEM_PY_PROGRAMFILES=%ProgramFiles%\\PsychoPy\\python.exe"
set "SYSTEM_PY_PROGRAMFILES3=%ProgramFiles%\\PsychoPy3\\python.exe"
set "SYSTEM_PY_LOCALAPPDATA=%LocalAppData%\\Programs\\PsychoPy\\python.exe"
set "SYSTEM_PY_LOCALAPPDATA3=%LocalAppData%\\Programs\\PsychoPy3\\python.exe"
set "PORTABLE_PY_2026_PARENT=%~dp0..\\Psychopy2026\\python.exe"
set "PORTABLE_PY_2024_PARENT=%~dp0..\\Psychopy2024\\python.exe"
set "SELECTED_PY="
set "LAST_FAILED_PY="

if not exist "%ENTRY_SCRIPT%" (
    echo [ERROR] Experiment entry script not found: "%ENTRY_SCRIPT%"
    pause
    exit /b 1
)

if exist "%PSYCHOPY_USER_DIR%" (
    echo Resetting local PsychoPy user folder: "%PSYCHOPY_USER_DIR%"
    rd /s /q "%PSYCHOPY_USER_DIR%"
)

echo Running {experiment_label}...

if defined CONFIGURED_PY (
    if not exist "%CONFIGURED_PY%" (
        echo [ERROR] Configured python path was not found:
        echo        "%CONFIGURED_PY%"
        pause
        exit /b 1
    )
    call :check_candidate "%CONFIGURED_PY%"
    if errorlevel 1 (
        echo [ERROR] Configured python path failed the PsychoPy/Qt check:
        echo        "%CONFIGURED_PY%"
        pause
        exit /b 1
    )
    set "SELECTED_PY=%CONFIGURED_PY%"
    goto :launch
)

for %%P in (
    "%SYSTEM_PY_PROGRAMFILES%"
    "%SYSTEM_PY_PROGRAMFILES3%"
    "%SYSTEM_PY_LOCALAPPDATA%"
    "%SYSTEM_PY_LOCALAPPDATA3%"
    "%PORTABLE_PY_2026_PARENT%"
    "%PORTABLE_PY_2024_PARENT%"
) do (
    if exist "%%~P" (
        call :check_candidate "%%~P"
        if not errorlevel 1 (
            set "SELECTED_PY=%%~P"
            goto :launch
        )
        set "LAST_FAILED_PY=%%~P"
    )
)

echo [ERROR] No usable PsychoPy interpreter was found.
echo.
echo Expected a system PsychoPy Standalone interpreter at one of:
echo   %SYSTEM_PY_PROGRAMFILES%
echo   %SYSTEM_PY_PROGRAMFILES3%
echo   %SYSTEM_PY_LOCALAPPDATA%
echo   %SYSTEM_PY_LOCALAPPDATA3%
echo.
echo Or a portable fallback interpreter at one of:
echo   %PORTABLE_PY_2026_PARENT%
echo   %PORTABLE_PY_2024_PARENT%
echo.
if defined LAST_FAILED_PY (
    echo [INFO] Last interpreter found but failed the PsychoPy/Qt check:
    echo        "%LAST_FAILED_PY%"
    echo.
    echo [INFO] Running verbose PsychoPy diagnostic:
    "%LAST_FAILED_PY%" -c "import sys; print('python=', sys.executable); print('version=', sys.version); print('trying: import psychopy'); import psychopy; print('psychopy=', psychopy.__version__)"
    if errorlevel 1 (
        echo.
        echo [INFO] PsychoPy import traceback:
        "%LAST_FAILED_PY%" -c "import traceback; exec('import psychopy')" 2>&1
    )
    echo.
)
pause
exit /b 1

:check_candidate
setlocal
set "CHECK_PY=%~1"
set "CHECK_PY_DIR=%~dp1"
set "PYTHONHOME="
set "PYTHONPATH="
set "QT_PLUGIN_PATH="
set "QT_QPA_PLATFORM_PLUGIN_PATH="
set "CONDA_PREFIX="
set "CONDA_DEFAULT_ENV="
set "CHECK_DLLS=%CHECK_PY_DIR%DLLs"
set "CHECK_LIB_BIN=%CHECK_PY_DIR%Library\\bin"
set "CHECK_QT_MODULE="
set "CHECK_QT_ROOT="
if exist "%CHECK_PY_DIR%Lib\\site-packages\\PyQt5\\Qt5" (
    set "CHECK_QT_MODULE=PyQt5"
    set "CHECK_QT_ROOT=%CHECK_PY_DIR%Lib\\site-packages\\PyQt5\\Qt5"
) else if exist "%CHECK_PY_DIR%Lib\\site-packages\\PyQt6\\Qt6" (
    set "CHECK_QT_MODULE=PyQt6"
    set "CHECK_QT_ROOT=%CHECK_PY_DIR%Lib\\site-packages\\PyQt6\\Qt6"
)
if not defined CHECK_QT_MODULE (
    endlocal
    exit /b 1
)
set "CHECK_QT_BIN=%CHECK_QT_ROOT%\\bin"
set "CHECK_QT_PLUGINS=%CHECK_QT_ROOT%\\plugins"
set "CHECK_QT_PLATFORMS=%CHECK_QT_PLUGINS%\\platforms"
set "PATH=%CHECK_PY_DIR%;%CHECK_DLLS%;%CHECK_LIB_BIN%;%CHECK_QT_BIN%;%PATH%"
if exist "%CHECK_QT_PLUGINS%" set "QT_PLUGIN_PATH=%CHECK_QT_PLUGINS%"
if exist "%CHECK_QT_PLATFORMS%" set "QT_QPA_PLATFORM_PLUGIN_PATH=%CHECK_QT_PLATFORMS%"
"%CHECK_PY%" -c "import importlib,os,psychopy; module=os.environ['CHECK_QT_MODULE'] + '.QtCore'; importlib.import_module(module)" >nul 2>&1
if errorlevel 1 (
    endlocal
    exit /b 1
)
endlocal
exit /b 0

:launch
echo Using interpreter: "%SELECTED_PY%"
call :run_with_isolated_env "%SELECTED_PY%" %*
goto :after_run

:after_run
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Experiment exited with code %EXIT_CODE%.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo Experiment finished.
pause
exit /b 0

:run_with_isolated_env
set "SELECTED_PY=%~1"
set "SELECTED_PY_DIR=%~dp1"
shift
REM Prevent conflicting Qt/Python settings from other software.
set "PYTHONHOME="
set "PYTHONPATH="
set "PROJECT_ROOT=%~dp0"
set "PROJECT_SRC=%~dp0src"
set "PYTHONPATH=%ENTRY_DIR%;%PROJECT_ROOT%;%PROJECT_SRC%"
set "QT_PLUGIN_PATH="
set "QT_QPA_PLATFORM_PLUGIN_PATH="
set "CONDA_PREFIX="
set "CONDA_DEFAULT_ENV="
set "PSY_DLLS=%SELECTED_PY_DIR%DLLs"
set "PSY_LIB_BIN=%SELECTED_PY_DIR%Library\\bin"
set "PSY_QT_MODULE="
set "PSY_QT_ROOT="
if exist "%SELECTED_PY_DIR%Lib\\site-packages\\PyQt5\\Qt5" (
    set "PSY_QT_MODULE=PyQt5"
    set "PSY_QT_ROOT=%SELECTED_PY_DIR%Lib\\site-packages\\PyQt5\\Qt5"
) else if exist "%SELECTED_PY_DIR%Lib\\site-packages\\PyQt6\\Qt6" (
    set "PSY_QT_MODULE=PyQt6"
    set "PSY_QT_ROOT=%SELECTED_PY_DIR%Lib\\site-packages\\PyQt6\\Qt6"
)
set "PSY_QT_BIN=%PSY_QT_ROOT%\\bin"
set "PSY_QT_PLUGINS=%PSY_QT_ROOT%\\plugins"
set "PSY_QT_PLATFORMS=%PSY_QT_PLUGINS%\\platforms"
set "PATH=%SELECTED_PY_DIR%;%PSY_DLLS%;%PSY_LIB_BIN%;%PSY_QT_BIN%;%PATH%"
if exist "%PSY_QT_PLUGINS%" set "QT_PLUGIN_PATH=%PSY_QT_PLUGINS%"
if exist "%PSY_QT_PLATFORMS%" set "QT_QPA_PLATFORM_PLUGIN_PATH=%PSY_QT_PLATFORMS%"

if not defined PSY_QT_MODULE (
    echo [ERROR] No PyQt5 or PyQt6 folder was found for selected interpreter:
    echo         "%SELECTED_PY%"
    exit /b 1
)
echo Using Qt package: %PSY_QT_MODULE%
"%SELECTED_PY%" -c "import importlib,os; module=os.environ['PSY_QT_MODULE'] + '.QtCore'; importlib.import_module(module)" >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo [ERROR] Failed to import %PSY_QT_MODULE%.QtCore with selected interpreter:
    echo         "%SELECTED_PY%"
    echo.
    echo [INFO] Running verbose Qt diagnostic:
    "%SELECTED_PY%" -c "import importlib,sys,os; print('python=', sys.executable); print('version=', sys.version); print('qt_module=', os.environ.get('PSY_QT_MODULE')); print('QT_PLUGIN_PATH=', os.environ.get('QT_PLUGIN_PATH')); print('QT_QPA_PLATFORM_PLUGIN_PATH=', os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH')); QC=importlib.import_module(os.environ['PSY_QT_MODULE'] + '.QtCore'); print('QtCore loaded from:', QC.__file__)"
    exit /b 1
)

"%SELECTED_PY%" -c "import os,runpy,sys; entry=os.environ['ENTRY_SCRIPT']; sys.path[:0]=[os.environ['ENTRY_DIR'], os.environ['PROJECT_ROOT'], os.environ['PROJECT_SRC']]; sys.argv=[entry]+sys.argv[1:]; runpy.run_path(entry, run_name='__main__')" %*
exit /b %ERRORLEVEL%
"""

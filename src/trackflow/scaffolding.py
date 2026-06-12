"""Project and experiment scaffolding helpers for ``trackflow``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Union

from .packaging import DEFAULT_CONFIG_NAME


PROJECT_DIRS = (
    Path("assets/images"),
    Path("assets/instructions"),
    Path("data"),
    Path("src/utils"),
)
PROJECT_FILES = (
    Path("src/__init__.py"),
    Path("src/utils/__init__.py"),
)
GITIGNORE_ENTRIES = (
    "__pycache__/",
    "*.py[cod]",
    "*.egg-info/",
    "dist/",
    "build/",
    ".venv/",
    "venv/",
    ".psychopy/",
    ".DS_Store",
    "._*",
    "Thumbs.db",
    "data/",
    ".python-version",
    ".claude/",
    "AGENTS.md",
    "plan.md",
)


@dataclass(frozen=True)
class ScaffoldSummary:
    """Summary of files and directories changed by one scaffold command."""

    project_root: Path
    created_paths: Sequence[Path]
    updated_paths: Sequence[Path]
    skipped_paths: Sequence[Path]


def init_project(project_root: Union[Path, str] = ".") -> ScaffoldSummary:
    """Initialize project-level folders for a trackflow experiment project."""
    root = Path(project_root).expanduser().resolve()
    created: List[Path] = []
    updated: List[Path] = []
    skipped: List[Path] = []

    for rel_path in PROJECT_DIRS:
        path = root / rel_path
        if path.exists():
            skipped.append(rel_path)
            continue
        path.mkdir(parents=True)
        created.append(rel_path)

    for rel_path in PROJECT_FILES:
        path = root / rel_path
        if path.exists():
            skipped.append(rel_path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        created.append(rel_path)

    readme = root / "README.md"
    if readme.exists():
        skipped.append(Path("README.md"))
    else:
        readme.write_text(_readme_template(root.name), encoding="utf-8")
        created.append(Path("README.md"))

    gitignore = root / ".gitignore"
    action = _ensure_gitignore_entries(gitignore)
    if action == "created":
        created.append(Path(".gitignore"))
    elif action == "updated":
        updated.append(Path(".gitignore"))
    else:
        skipped.append(Path(".gitignore"))

    return ScaffoldSummary(root, tuple(created), tuple(updated), tuple(skipped))


def add_experiment(
    experiment_name: Optional[str] = None,
    project_root: Union[Path, str] = ".",
) -> ScaffoldSummary:
    """Add a runnable experiment scaffold to a trackflow project."""
    root = Path(project_root).expanduser().resolve()
    name = _normalize_experiment_name(experiment_name)
    _check_layout(root, name)

    target_dir = root / "src" if name is None else root / "src" / name
    rel_dir = Path("src") if name is None else Path("src") / name
    target_dir.mkdir(parents=True, exist_ok=True)

    experiment_label = name or root.name
    templates = _experiment_templates(experiment_label)
    if name is not None:
        templates["__init__.py"] = ""

    existing_files = [rel_dir / filename for filename in templates if (root / rel_dir / filename).exists()]
    if existing_files:
        paths = ", ".join(path.as_posix() for path in existing_files)
        raise FileExistsError(f"Experiment scaffold file already exists: {paths}")

    created: List[Path] = []
    skipped: List[Path] = []
    for filename, content in templates.items():
        rel_path = rel_dir / filename
        path = root / rel_path
        path.write_text(content, encoding="utf-8")
        created.append(rel_path)

    config_path = root / DEFAULT_CONFIG_NAME
    updated: List[Path] = []
    if config_path.exists():
        skipped.append(Path(DEFAULT_CONFIG_NAME))
    else:
        config_path.write_text(
            _packaging_config_template(
                project_name=root.name,
                launcher_name=_launcher_name(name),
                settings_path=rel_dir / "settings.py",
                entry_script=rel_dir / "main.py",
            ),
            encoding="utf-8",
        )
        created.append(Path(DEFAULT_CONFIG_NAME))

    return ScaffoldSummary(root, tuple(created), tuple(updated), tuple(skipped))


def _ensure_gitignore_entries(path: Path) -> str:
    """Create or append the standard trackflow project ignore entries."""
    if path.exists():
        original = path.read_text(encoding="utf-8")
    else:
        original = ""

    existing = {line.strip() for line in original.splitlines() if line.strip()}
    missing = [entry for entry in GITIGNORE_ENTRIES if entry not in existing]
    if not missing:
        return "skipped"

    lines = original.splitlines()
    if lines and lines[-1].strip():
        lines.append("")
    if missing:
        lines.append("# trackflow")
        lines.extend(missing)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return "updated" if original else "created"


def _normalize_experiment_name(name: Optional[str]) -> Optional[str]:
    """Return a validated experiment folder name or ``None`` for flat layout."""
    if name is None:
        return None
    normalized = str(name).strip()
    if not normalized:
        return None
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", normalized):
        raise ValueError("Experiment name must be a Python-friendly name such as exp1.")
    return normalized


def _check_layout(root: Path, name: Optional[str]) -> None:
    """Reject ambiguous mixes of flat and named experiment layouts."""
    src = root / "src"
    flat_files = [src / filename for filename in _experiment_filenames()]
    named_dirs = _named_experiment_dirs(src)

    if name is None:
        if named_dirs:
            names = ", ".join(path.name for path in named_dirs)
            raise ValueError(
                "This project already uses named experiment folders "
                f"({names}); run trackflow add-experiment <name>."
            )
        return

    existing_flat = [path for path in flat_files if path.exists()]
    if existing_flat:
        paths = ", ".join(str(path.relative_to(root)) for path in existing_flat)
        raise ValueError(
            "This project already uses flat experiment files "
            f"({paths}); named experiments would mix layouts."
        )


def _named_experiment_dirs(src: Path) -> List[Path]:
    """Return src child folders that look like existing experiment folders."""
    if not src.is_dir():
        return []
    candidates = []
    for child in src.iterdir():
        if not child.is_dir() or child.name == "utils" or child.name.startswith("."):
            continue
        if (child / "main.py").exists() or (child / "settings.py").exists():
            candidates.append(child)
    return sorted(candidates)


def _experiment_filenames() -> Sequence[str]:
    """Return generated experiment scaffold filenames."""
    return ("main.py", "runtime.py", "settings.py", "screens.py", "stimuli.py", "trial.py")


def _experiment_templates(experiment_name: str) -> dict:
    """Return text templates for one generated experiment scaffold."""
    return {
        "main.py": _main_template(),
        "runtime.py": _runtime_template(),
        "settings.py": _settings_template(experiment_name),
        "screens.py": _screens_template(),
        "stimuli.py": _stimuli_template(),
        "trial.py": _trial_template(),
    }


def _readme_template(project_name: str) -> str:
    """Return a short README for a new trackflow project."""
    return f"""# {project_name}

PsychoPy experiment project scaffolded with trackflow.

## Quick Start

Add an experiment scaffold:

```bash
uv run trackflow add-experiment exp1
```

Run a generated experiment:

```bash
uv run python src/exp1/main.py
```
"""


def _main_template() -> str:
    """Return the generated experiment entrypoint."""
    return '''"""Run this trackflow experiment."""

from __future__ import annotations

from runtime import close_runtime, setup_runtime
from screens import show_end, show_welcome
from settings import RUNTIME
from trial import run_example_trial


def main() -> None:
    """Run the scaffolded experiment flow."""
    timeline = setup_runtime()
    try:
        show_welcome(timeline)
        if bool(RUNTIME.get("run_example_trial", True)):
            run_example_trial(timeline)
        show_end(timeline)
    finally:
        close_runtime(timeline)


if __name__ == "__main__":
    main()
'''


def _runtime_template() -> str:
    """Return runtime setup code for a generated experiment."""
    return '''"""Runtime setup for this experiment."""

from __future__ import annotations

from psychopy import monitors, visual
from trackflow import beh

from settings import EXPERIMENT_NAME, GLOBAL_KEYS, MONITOR


def setup_runtime():
    """Create the PsychoPy window and trackflow timeline."""
    monitor = monitors.Monitor(
        MONITOR["name"],
        width=MONITOR["width"],
        distance=MONITOR["distance"],
    )
    monitor.setSizePix(MONITOR["resolution"])
    win = visual.Window(
        size=MONITOR["resolution"],
        fullscr=MONITOR["fullscr"],
        monitor=monitor,
        units="deg",
        color="#7F7F7F",
        colorSpace="hex",
        screen=MONITOR.get("screen_id", 0),
    )
    return beh.timeline.setup_timeline(
        win=win,
        params={"experiment_name": EXPERIMENT_NAME},
        global_key_requests=GLOBAL_KEYS,
    )


def close_runtime(timeline) -> None:
    """Close the PsychoPy window owned by the timeline."""
    if timeline is not None and timeline.win is not None:
        timeline.win.close()
'''


def _settings_template(experiment_name: str) -> str:
    """Return minimal settings for a generated experiment."""
    return f'''"""Runtime settings for this experiment."""

EXPERIMENT_NAME = "{experiment_name}"

MONITOR = {{
    "name": "Monitor01",
    "distance": 60,
    "width": 53,
    "resolution": [1024, 768],
    "fullscr": False,
}}

GLOBAL_KEYS = {{
    "pause_experiment": ["command + p", "ctrl + p", "F10"],
}}

RUNTIME = {{
    "debug": True,
    "run_example_trial": True,
}}
'''


def _screens_template() -> str:
    """Return common screen helpers for a generated experiment."""
    return '''"""Common screens for this experiment."""

from __future__ import annotations


def show_welcome(timeline) -> None:
    """Show the experiment welcome screen."""
    screen = timeline.make_text_screen(
        "Welcome.",
        choices=["space"],
        prompt_text="Press Space to continue",
        data={"screen_name": "welcome"},
    )
    timeline.run(screen, record=False)


def show_end(timeline) -> None:
    """Show the experiment end screen."""
    screen = timeline.make_text_screen(
        "The experiment is complete.",
        choices=["space"],
        prompt_text="Press Space to exit",
        data={"screen_name": "end"},
    )
    timeline.run(screen, record=False)


def show_break(timeline, message=None) -> None:
    """Show a participant-controlled break screen."""
    screen = timeline.make_text_screen(
        message or "Take a short break.",
        choices=["space"],
        prompt_text="Press Space to continue",
        data={"screen_name": "break"},
    )
    timeline.run(screen, record=False)


def show_researcher_pause(timeline, message=None) -> None:
    """Show a researcher-controlled pause screen."""
    screen = timeline.make_text_screen(
        message or "Researcher pause.",
        choices=["space"],
        prompt_text="Press Space to continue",
        data={"screen_name": "researcher_pause"},
    )
    timeline.run(screen, record=False)
'''


def _stimuli_template() -> str:
    """Return the generated stimuli module placeholder."""
    return '''"""Stimulus builders for this experiment.

Put experiment-specific PsychoPy stimulus constructors here, such as sample
displays, probes, feedback text, image loading, or layout helpers.

Keep timing, trial order, response rules, and EEG/eye-tracking marker decisions
in the experiment flow code where they are easy to inspect.
"""
'''


def _trial_template() -> str:
    """Return a minimal example trial module."""
    return '''"""Example trial structure for this experiment."""

from __future__ import annotations

from trackflow import beh


def run_example_trial(timeline) -> None:
    """Create and run one minimal example trial."""
    fixation = make_fixation_screen(timeline)
    continue_screen = make_continue_screen(timeline)

    trial = timeline.make_trial(screens=[fixation, continue_screen])
    timeline.run(trial, trial_data={"trial_type": "example"})


def make_fixation_screen(timeline):
    """Create the fixation screen for the example trial."""
    fixation = beh.stimuli.make_fixation(
        timeline.win,
        size=0.5,
        color="#000000",
    )
    return timeline.make_screen(
        stimuli=[fixation],
        duration=0.5,
        response=None,
        data={"screen_name": "fixation"},
    )


def make_continue_screen(timeline):
    """Create the continue screen for the example trial."""
    return timeline.make_text_screen(
        "Ready.",
        choices=["space"],
        prompt_text="Press Space to continue",
        data={"screen_name": "continue"},
    )
'''


def _packaging_config_template(
    *,
    project_name: str,
    launcher_name: str,
    settings_path: Path,
    entry_script: Path,
) -> str:
    """Return the project-level packaging config for the first experiment."""
    return f'''"""Trackflow deployment packaging configuration for {project_name}."""

PROJECT_NAME = "{project_name}"
DESTINATION = "../packaged/{project_name}"

SETTINGS_OVERRIDES = {{}}

LAUNCHERS = {{
    "{launcher_name}": {{
        "settings": "{settings_path.as_posix()}",
        "entry_script": "{entry_script.as_posix()}",
        "python": None,
        "settings_overrides": {{}},
    }},
}}

if __name__ == "__main__":
    from pathlib import Path
    from trackflow.packaging import package_project

    package_project(config_path=Path(__file__))
'''


def _launcher_name(name: Optional[str]) -> str:
    """Return the Windows launcher filename for one scaffolded experiment."""
    if name is None:
        return "run_experiment.bat"
    return f"run_{name}.bat"

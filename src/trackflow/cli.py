"""Command-line interface for ``trackflow`` project utilities."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .packaging import DEFAULT_CONFIG_NAME, package_project
from .scaffolding import add_experiment, init_project


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the ``trackflow`` command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return int(args.func(args))
    except Exception as exc:  # pragma: no cover - exercised by CLI behavior
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="trackflow",
        description="PsychoPy experiment helpers and deployment tools.",
    )
    subparsers = parser.add_subparsers(dest="command")

    package_parser = subparsers.add_parser(
        "package",
        help="copy a project for deployment and vendor trackflow",
    )
    package_parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        help=f"path to project packaging config (default: {DEFAULT_CONFIG_NAME})",
    )
    package_parser.add_argument(
        "--destination",
        help="temporary destination override for this package run",
    )
    package_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be packaged without writing files",
    )
    package_parser.set_defaults(func=_run_package)

    init_parser = subparsers.add_parser(
        "init",
        help="initialize trackflow project folders",
    )
    init_parser.set_defaults(func=_run_init)

    add_parser = subparsers.add_parser(
        "add-experiment",
        help="add a runnable experiment scaffold",
    )
    add_parser.add_argument(
        "name",
        nargs="?",
        help="optional experiment folder name such as exp1",
    )
    add_parser.set_defaults(func=_run_add_experiment)
    return parser


def _run_package(args: argparse.Namespace) -> int:
    """Run ``trackflow package`` and print a concise summary."""
    summary = package_project(
        config_path=Path(args.config),
        destination=args.destination,
        dry_run=bool(args.dry_run),
    )
    prefix = "[dry-run] " if summary.dry_run else ""
    print(f"{prefix}Project: {summary.project_name}")
    print(f"{prefix}Project root: {summary.project_root}")
    print(f"{prefix}Packaging config: {summary.config_path}")
    print(f"{prefix}Destination: {summary.destination}")
    print(f"{prefix}Launchers: {len(summary.launcher_paths)}")
    print(f"{prefix}Checked files: {summary.checked_files}")
    if summary.dry_run:
        print(f"{prefix}Would vendor trackflow into: {summary.destination / 'trackflow'}")
        for launcher_path in summary.launcher_paths:
            print(f"{prefix}Would write launcher: {launcher_path}")
        print(f"{prefix}Would write manifest: {summary.manifest_path}")
        return 0

    print(f"Updated files copied: {summary.copied_files}")
    print(f"Unchanged files skipped: {summary.skipped_files}")
    print(f"Removed macOS temp files: {summary.removed_temp_files}")
    print(f"Vendored trackflow into: {summary.destination / 'trackflow'}")
    for launcher_path in summary.launcher_paths:
        print(f"Wrote launcher: {launcher_path}")
    print(f"Wrote manifest: {summary.manifest_path}")
    return 0


def _run_init(args: argparse.Namespace) -> int:
    """Run ``trackflow init`` and print changed project paths."""
    summary = init_project()
    _print_scaffold_summary("Initialized trackflow project", summary)
    return 0


def _run_add_experiment(args: argparse.Namespace) -> int:
    """Run ``trackflow add-experiment`` and print changed project paths."""
    summary = add_experiment(args.name)
    label = args.name or "flat experiment"
    _print_scaffold_summary(f"Added {label}", summary)
    return 0


def _print_scaffold_summary(title: str, summary) -> None:
    """Print a concise scaffold command summary."""
    print(title)
    print(f"Project root: {summary.project_root}")
    for path in summary.created_paths:
        print(f"Created: {path}")
    for path in summary.updated_paths:
        print(f"Updated: {path}")
    for path in summary.skipped_paths:
        print(f"Skipped existing: {path}")


if __name__ == "__main__":
    raise SystemExit(main())

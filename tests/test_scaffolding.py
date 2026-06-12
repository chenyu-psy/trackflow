"""Tests for project and experiment scaffolding commands."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from trackflow import cli as trackflow_cli
from trackflow import packaging as trackflow_packaging
from trackflow import scaffolding as trackflow_scaffolding


class ScaffoldTests(unittest.TestCase):
    """Check trackflow project and experiment scaffolds."""

    def test_init_creates_project_structure_and_preserves_readme(self):
        """Project init should not overwrite existing researcher documentation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            (project / "README.md").write_text("Existing README\n", encoding="utf-8")

            summary = trackflow_scaffolding.init_project(project)

            self.assertTrue((project / "assets" / "images").is_dir())
            self.assertTrue((project / "assets" / "instructions").is_dir())
            self.assertTrue((project / "data").is_dir())
            self.assertTrue((project / "src" / "__init__.py").is_file())
            self.assertTrue((project / "src" / "utils" / "__init__.py").is_file())
            self.assertEqual(
                (project / "README.md").read_text(encoding="utf-8"),
                "Existing README\n",
            )
            self.assertNotIn(Path("README.md"), summary.created_paths)
            self.assertIn(Path("README.md"), summary.skipped_paths)
            self.assertFalse((project / "src" / "main.py").exists())
            self.assertFalse((project / "packaging_config.py").exists())

    def test_init_appends_missing_gitignore_entries_without_duplicates(self):
        """Project init should preserve existing ignore rules and add missing ones."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            (project / ".gitignore").write_text(".venv/\ndata/\n", encoding="utf-8")

            trackflow_scaffolding.init_project(project)
            trackflow_scaffolding.init_project(project)

            lines = (project / ".gitignore").read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines.count(".venv/"), 1)
            self.assertEqual(lines.count("data/"), 1)
            self.assertEqual(lines.count(".psychopy/"), 1)
            self.assertEqual(lines.count("__pycache__/"), 1)
            self.assertEqual(lines.count("AGENTS.md"), 1)

    def test_add_experiment_creates_flat_layout_and_packaging_config(self):
        """An unnamed experiment should create runnable files directly in src."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            trackflow_scaffolding.init_project(project)

            summary = trackflow_scaffolding.add_experiment(project_root=project)

            for filename in ("main.py", "runtime.py", "settings.py", "screens.py", "stimuli.py", "trial.py"):
                self.assertTrue((project / "src" / filename).is_file())
                self.assertIn(Path("src") / filename, summary.created_paths)
            self.assertTrue((project / "packaging_config.py").is_file())
            config = trackflow_packaging.load_package_config(
                config_path=project / "packaging_config.py"
            )
            self.assertEqual(
                config.destination,
                (project.parent / "packaged" / "project").resolve(),
            )
            self.assertEqual(config.launchers[0].launcher_name, "run_experiment.bat")
            self.assertEqual(config.launchers[0].settings_path, Path("src/settings.py"))
            self.assertEqual(config.launchers[0].entry_script, Path("src/main.py"))

    def test_add_experiment_creates_named_layout(self):
        """A named experiment should create files under src/<name>."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            trackflow_scaffolding.init_project(project)

            trackflow_scaffolding.add_experiment("exp1", project_root=project)

            for filename in (
                "__init__.py",
                "main.py",
                "runtime.py",
                "settings.py",
                "screens.py",
                "stimuli.py",
                "trial.py",
            ):
                self.assertTrue((project / "src" / "exp1" / filename).is_file())
            config = trackflow_packaging.load_package_config(
                config_path=project / "packaging_config.py"
            )
            runtime_text = (project / "src" / "exp1" / "runtime.py").read_text(
                encoding="utf-8"
            )
            self.assertIn('monitor.setSizePix(MONITOR["resolution"])', runtime_text)
            self.assertEqual(config.launchers[0].launcher_name, "run_exp1.bat")
            self.assertEqual(config.launchers[0].settings_path, Path("src/exp1/settings.py"))
            self.assertEqual(config.launchers[0].entry_script, Path("src/exp1/main.py"))

    def test_add_experiment_does_not_overwrite_existing_files(self):
        """Existing experiment files should stop scaffold generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            (project / "src").mkdir()
            (project / "src" / "screens.py").write_text(
                "print('mine')\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(FileExistsError, "src/screens.py"):
                trackflow_scaffolding.add_experiment(project_root=project)

            self.assertEqual(
                (project / "src" / "screens.py").read_text(encoding="utf-8"),
                "print('mine')\n",
            )
            self.assertFalse((project / "src" / "main.py").exists())

    def test_add_experiment_rejects_mixed_layouts(self):
        """Flat and named experiment layouts should not be mixed implicitly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            flat_project = Path(tmp_dir) / "flat"
            named_project = Path(tmp_dir) / "named"
            flat_project.mkdir()
            named_project.mkdir()

            trackflow_scaffolding.add_experiment(project_root=flat_project)
            with self.assertRaisesRegex(ValueError, "flat experiment files"):
                trackflow_scaffolding.add_experiment("exp2", project_root=flat_project)

            trackflow_scaffolding.add_experiment("exp1", project_root=named_project)
            with self.assertRaisesRegex(ValueError, "named experiment folders"):
                trackflow_scaffolding.add_experiment(project_root=named_project)

    def test_existing_packaging_config_is_preserved_for_later_experiments(self):
        """Project-level packaging config should not be rewritten once present."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            trackflow_scaffolding.add_experiment("exp1", project_root=project)
            original = (project / "packaging_config.py").read_text(encoding="utf-8")

            summary = trackflow_scaffolding.add_experiment("exp2", project_root=project)

            self.assertEqual(
                (project / "packaging_config.py").read_text(encoding="utf-8"),
                original,
            )
            self.assertIn(Path("packaging_config.py"), summary.skipped_paths)

    def test_cli_init_and_add_experiment_print_summaries(self):
        """CLI commands should call scaffold helpers and report changed paths."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            project.mkdir()
            stdout = io.StringIO()
            cwd = Path.cwd()
            try:
                import os

                os.chdir(project)
                with redirect_stdout(stdout):
                    init_result = trackflow_cli.main(["init"])
                    add_result = trackflow_cli.main(["add-experiment", "exp1"])
            finally:
                os.chdir(cwd)

            self.assertEqual(init_result, 0)
            self.assertEqual(add_result, 0)
            output = stdout.getvalue()
            self.assertIn("Initialized trackflow project", output)
            self.assertIn("Added exp1", output)
            self.assertTrue((project / "src" / "exp1" / "main.py").is_file())


if __name__ == "__main__":
    unittest.main()

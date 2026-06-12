"""Tests for project packaging and deployment-time vendoring."""

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from trackflow import __version__
from trackflow import cli as trackflow_cli
from trackflow import packaging as trackflow_packaging


class PackagingTests(unittest.TestCase):
    """Check project packaging without requiring PsychoPy."""

    def test_load_package_config_reads_project_config_without_importing_settings(self):
        """Config loading should not execute experiment settings imports."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            destination = Path(tmp_dir) / "lab_copy"
            config_path = _make_fake_project(project, destination)

            config = trackflow_packaging.load_package_config(config_path=config_path)

            self.assertEqual(config.project_name, "catload")
            self.assertEqual(config.project_root, project.resolve())
            self.assertEqual(config.destination, destination.resolve())
            self.assertEqual(config.paths, (Path("assets"), Path("src/common"), Path("src/exp1b"), Path("src/exp2")))
            self.assertEqual(config.settings_overrides["RUNTIME.run_warmup"], True)
            self.assertEqual(config.settings_overrides["MONITOR.resolution"], [1920, 1080])
            self.assertEqual([launcher.launcher_name for launcher in config.launchers], ["run_exp1b.bat", "run_exp2.bat"])
            self.assertEqual(config.launchers[0].settings_path, Path("src/exp1b/settings.py"))
            self.assertEqual(config.launchers[0].entry_script, Path("src/exp1b/main.py"))
            self.assertEqual(config.launchers[0].python, r"C:\PsychoPy\python.exe")
            self.assertEqual(config.launchers[0].settings_overrides["DESIGN.N_trials"], 200)

    def test_missing_launchers_is_a_clear_error(self):
        """A project config must declare at least one launcher."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            (project / "src").mkdir(parents=True)
            config_path = project / "packaging_config.py"
            config_path.write_text(
                "PROJECT_NAME = 'catload'\n"
                "DESTINATION = 'packaged'\n"
                "PATHS = ['src']\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "LAUNCHERS"):
                trackflow_packaging.load_package_config(config_path=config_path)

    def test_missing_required_launcher_fields_are_clear_errors(self):
        """Each launcher must define settings and entry_script."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            (project / "src").mkdir(parents=True)
            config_path = project / "packaging_config.py"
            config_path.write_text(
                "PROJECT_NAME = 'catload'\n"
                "DESTINATION = 'packaged'\n"
                "PATHS = ['src']\n"
                "LAUNCHERS = {'run_exp1b.bat': {'settings': 'src/exp1b/settings.py'}}\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "entry_script"):
                trackflow_packaging.load_package_config(config_path=config_path)

    def test_destination_override_replaces_config_destination(self):
        """The CLI destination override should not require editing config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            destination = Path(tmp_dir) / "lab_copy"
            override = Path(tmp_dir) / "override_copy"
            config_path = _make_fake_project(project, destination)

            config = trackflow_packaging.load_package_config(
                config_path=config_path,
                destination=override,
            )

            self.assertEqual(config.destination, override.resolve())

    def test_package_project_copies_project_paths_and_writes_launchers(self):
        """Packaging should copy selected project paths, vendor trackflow, and write metadata."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            destination = Path(tmp_dir) / "lab_copy"
            config_path = _make_fake_project(project, destination)
            _stage_fake_project(project)

            summary = trackflow_packaging.package_project(config_path=config_path)

            self.assertFalse(summary.dry_run)
            self.assertEqual(summary.project_name, "catload")
            self.assertTrue((destination / "src" / "exp1b" / "main.py").is_file())
            self.assertTrue((destination / "src" / "exp2" / "main.py").is_file())
            self.assertTrue((destination / "src" / "common" / "helper.py").is_file())
            self.assertTrue((destination / "assets" / "fixation.png").is_file())
            self.assertFalse((destination / "ignored.txt").exists())
            self.assertTrue((destination / "trackflow" / "__init__.py").is_file())
            self.assertFalse(any((destination / "trackflow").rglob("*.pyc")))
            self.assertTrue((destination / "run_exp1b.bat").is_file())
            self.assertTrue((destination / "run_exp2.bat").is_file())

            exp1_settings = (destination / "src" / "exp1b" / "settings.py").read_text(
                encoding="utf-8"
            )
            self.assertIn('"run_warmup": True', exp1_settings)
            self.assertIn('"realtime_tracker": True', exp1_settings)
            self.assertIn('"realtime_eeg": True', exp1_settings)
            self.assertIn('"fullscr": True', exp1_settings)
            self.assertIn('"resolution": [1920, 1080]', exp1_settings)
            self.assertIn('"N_trials": 200', exp1_settings)
            self.assertIn('"N_trials": 5', exp1_settings)

            source_settings = (project / "src" / "exp1b" / "settings.py").read_text(
                encoding="utf-8"
            )
            self.assertIn('"run_warmup": False', source_settings)
            self.assertIn('"fullscr": False', source_settings)
            self.assertIn('"N_trials": 20', source_settings)

            manifest = json.loads(
                (destination / "trackflow_vendored.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["trackflow_version"], __version__)
            self.assertEqual(manifest["project_name"], "catload")
            self.assertEqual(manifest["paths"], ["assets", "src/common", "src/exp1b", "src/exp2"])
            self.assertEqual(manifest["settings_overrides"]["MONITOR.fullscr"], True)
            self.assertEqual(manifest["launchers"]["run_exp1b.bat"]["entry_script"], "src/exp1b/main.py")
            self.assertEqual(manifest["launchers"]["run_exp2.bat"]["settings"], "src/exp2/settings.py")

    def test_launcher_overrides_take_precedence_over_project_overrides(self):
        """Launcher settings_overrides should win over project settings."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            destination = Path(tmp_dir) / "lab_copy"
            config_path = _make_fake_project(project, destination)
            _stage_fake_project(project)

            trackflow_packaging.package_project(config_path=config_path)

            exp2_settings = (destination / "src" / "exp2" / "settings.py").read_text(
                encoding="utf-8"
            )
            self.assertIn('"distance": 120', exp2_settings)

    def test_dry_run_does_not_write_destination(self):
        """Dry runs should inspect selected files without creating output."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            destination = Path(tmp_dir) / "lab_copy"
            config_path = _make_fake_project(project, destination)
            _stage_fake_project(project)

            summary = trackflow_packaging.package_project(
                config_path=config_path,
                dry_run=True,
            )

            self.assertTrue(summary.dry_run)
            self.assertEqual(summary.checked_files, 7)
            self.assertFalse(destination.exists())

    def test_cli_package_runs_without_experiment_argument(self):
        """The package CLI should package the project named by the config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            destination = Path(tmp_dir) / "lab_copy"
            config_path = _make_fake_project(project, destination)
            _stage_fake_project(project)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                result = trackflow_cli.main(["package", "--config", str(config_path)])

            self.assertEqual(result, 0)
            self.assertIn("Project: catload", stdout.getvalue())
            self.assertTrue((destination / "run_exp1b.bat").is_file())

    def test_rewrite_settings_text_fails_on_missing_block(self):
        """Overrides should fail when the standard settings block is absent."""
        settings_text = 'MONITOR = {"fullscr": False}\n'

        with self.assertRaisesRegex(ValueError, "RUNTIME"):
            trackflow_packaging.rewrite_settings_text(
                settings_text,
                {"RUNTIME.run_warmup": True},
            )

    def test_rewrite_settings_text_fails_on_missing_key(self):
        """Overrides should fail when a standard settings key is absent."""
        settings_text = 'RUNTIME = {"run_warmup": False}\n'

        with self.assertRaisesRegex(ValueError, "realtime_eeg"):
            trackflow_packaging.rewrite_settings_text(
                settings_text,
                {"RUNTIME.realtime_eeg": True},
            )

    def test_rewrite_settings_text_fails_on_nonliteral_block(self):
        """Settings blocks must stay literal dictionaries for safe rewriting."""
        settings_text = 'RUNTIME = make_runtime_settings()\n'

        with self.assertRaisesRegex(ValueError, "literal dictionary"):
            trackflow_packaging.rewrite_settings_text(
                settings_text,
                {"RUNTIME.run_warmup": True},
            )

    def test_rewrite_settings_text_preserves_valid_python(self):
        """Rewritten settings should parse and contain the requested values."""
        settings_text = (
            "RUNTIME = {\n"
            '    "run_warmup": False,\n'
            '    "realtime_tracker": False,\n'
            "}\n"
            "\n"
            "MONITOR = {\n"
            '    "resolution": [1024, 768],\n'
            '    "fullscr": False,\n'
            "}\n"
        )

        updated = trackflow_packaging.rewrite_settings_text(
            settings_text,
            {
                "RUNTIME.run_warmup": True,
                "MONITOR.resolution": [1920, 1080],
            },
        )

        compile(updated, "settings.py", "exec")
        self.assertIn('"run_warmup": True', updated)
        self.assertIn('"resolution": [1920, 1080]', updated)

    def test_launcher_adds_copied_project_to_pythonpath(self):
        """The launcher should expose vendored trackflow and project src imports."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir) / "project"
            destination = Path(tmp_dir) / "lab_copy"
            config_path = _make_fake_project(project, destination)
            config = trackflow_packaging.load_package_config(config_path=config_path)

            launcher = trackflow_packaging._render_launcher(config.launchers[0])

            self.assertIn('set "PROJECT_ROOT=%~dp0"', launcher)
            self.assertIn('set "PROJECT_SRC=%~dp0src"', launcher)
            self.assertIn('set "PYTHONPATH=%ENTRY_DIR%;%PROJECT_ROOT%;%PROJECT_SRC%"', launcher)
            self.assertIn("entry=os.environ['ENTRY_SCRIPT']", launcher)
            self.assertIn(
                "sys.path[:0]=[os.environ['ENTRY_DIR'], "
                "os.environ['PROJECT_ROOT'], os.environ['PROJECT_SRC']]",
                launcher,
            )
            self.assertIn("runpy.run_path(entry, run_name='__main__')", launcher)


def _make_fake_project(project: Path, destination: Path) -> Path:
    """Create a small experiment project for packaging tests."""
    (project / "assets").mkdir(parents=True)
    (project / "src" / "common").mkdir(parents=True)
    (project / "src" / "exp1b").mkdir(parents=True)
    (project / "src" / "exp2").mkdir(parents=True)
    (project / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (project / "ignored.txt").write_text("skip me\n", encoding="utf-8")
    (project / "assets" / "fixation.png").write_text("fake image\n", encoding="utf-8")
    (project / "src" / "common" / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "src" / "exp1b" / "main.py").write_text(
        "import settings\nprint(settings.RUNTIME)\n",
        encoding="utf-8",
    )
    (project / "src" / "exp2" / "main.py").write_text("print('other')\n", encoding="utf-8")
    _write_settings(project / "src" / "exp1b" / "settings.py")
    _write_settings(project / "src" / "exp2" / "settings.py")
    config_path = project / "packaging_config.py"
    config_path.write_text(
        "PROJECT_NAME = 'catload'\n"
        f"DESTINATION = r'{destination}'\n"
        "PATHS = ['assets', 'src/common', 'src/exp1b', 'src/exp2']\n"
        "SETTINGS_OVERRIDES = {\n"
        "    'RUNTIME.run_warmup': True,\n"
        "    'RUNTIME.realtime_tracker': True,\n"
        "    'RUNTIME.realtime_eeg': True,\n"
        "    'MONITOR.fullscr': True,\n"
        "    'MONITOR.resolution': [1920, 1080],\n"
        "    'MONITOR.distance': 90,\n"
        "}\n"
        "LAUNCHERS = {\n"
        "    'run_exp1b.bat': {\n"
        "        'settings': 'src/exp1b/settings.py',\n"
        "        'entry_script': 'src/exp1b/main.py',\n"
        "        'python': r'C:\\PsychoPy\\python.exe',\n"
        "        'settings_overrides': {\n"
        "            'DESIGN.N_trials': 200,\n"
        "            'PRACTICE.N_trials': 5,\n"
        "        },\n"
        "    },\n"
        "    'run_exp2.bat': {\n"
        "        'settings': 'src/exp2/settings.py',\n"
        "        'entry_script': 'src/exp2/main.py',\n"
        "        'python': None,\n"
        "        'settings_overrides': {\n"
        "            'MONITOR.distance': 120,\n"
        "        },\n"
        "    },\n"
        "}\n",
        encoding="utf-8",
    )
    return config_path


def _write_settings(path: Path) -> None:
    """Write one literal settings file for packaging tests."""
    path.write_text(
        "raise RuntimeError('settings was imported')\n"
        "RUNTIME = {\n"
        '    "run_warmup": False,\n'
        '    "realtime_tracker": False,\n'
        '    "realtime_eeg": False,\n'
        "}\n"
        "MONITOR = {\n"
        '    "resolution": [1024, 768],\n'
        '    "fullscr": False,\n'
        '    "distance": 60,\n'
        '    "width": 53,\n'
        "}\n"
        "DESIGN = {\n"
        '    "N_trials": 20,\n'
        "}\n"
        "PRACTICE = {\n"
        '    "N_trials": 2,\n'
        "}\n",
        encoding="utf-8",
    )


def _stage_fake_project(project: Path) -> None:
    """Initialize git and stage fake project files."""
    _git(project, "init")
    _git(project, "add", ".gitignore", "packaging_config.py", "assets")
    _git(project, "add", "src/common", "src/exp1b", "src/exp2")


def _git(cwd: Path, *args: str) -> None:
    """Run a git command for a temporary test repository."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()

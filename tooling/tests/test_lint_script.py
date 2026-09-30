from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class LintScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repository = Path(self.temporary_directory.name)
        (self.repository / "tooling").mkdir()
        shutil.copy2(ROOT / "tooling/lint.sh", self.repository / "tooling/lint.sh")

        tool_directory = self.repository / "fake-bin"
        tool_directory.mkdir()
        for name in ("pylint", "ruff", "yamllint"):
            executable = tool_directory / name
            executable.write_text("#!/usr/bin/env sh\nexit 0\n")
            executable.chmod(0o755)
        self.pylint_arguments = self.repository / "pylint-arguments.txt"
        (tool_directory / "pylint").write_text(
            f'#!/usr/bin/env sh\nprintf "%s\\n" "$@" > "{self.pylint_arguments.as_posix()}"\n'
        )

        self.environment = os.environ.copy()
        self.environment["PATH"] = f"{tool_directory}:{self.environment['PATH']}"

        self.git("init", "-b", "main")
        self.git("config", "user.name", "Guardrails Test")
        self.git("config", "user.email", "guardrails-test@example.invalid")
        (self.repository / "example.txt").write_text("clean\n")
        self.git("add", ".")
        self.git("commit", "-m", "test: create clean repository")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.repository,
            text=True,
            capture_output=True,
            check=True,
        )

    def run_lint(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["tooling/lint.sh"],
            cwd=self.repository,
            env=self.environment,
            text=True,
            capture_output=True,
        )

    def test_rejects_staged_trailing_whitespace(self) -> None:
        (self.repository / "example.txt").write_text("staged trailing whitespace  \n")
        self.git("add", "example.txt")

        completed = self.run_lint()

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("trailing whitespace", completed.stdout + completed.stderr)

    def test_rejects_unstaged_trailing_whitespace(self) -> None:
        (self.repository / "example.txt").write_text("unstaged trailing whitespace  \n")

        completed = self.run_lint()

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("trailing whitespace", completed.stdout + completed.stderr)

    def test_runs_pylint_on_tracked_python_files(self) -> None:
        (self.repository / "tracked.py").write_text("VALUE = 1\n")
        (self.repository / "untracked.py").write_text("VALUE = 2\n")
        self.git("add", "tracked.py")
        self.git("commit", "-m", "test: add python module")

        completed = self.run_lint()

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(self.pylint_arguments.read_text().splitlines(), ["tracked.py"])

    def test_skips_pylint_without_tracked_python_files(self) -> None:
        completed = self.run_lint()

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertFalse(self.pylint_arguments.exists())


if __name__ == "__main__":
    unittest.main()

"""Tests for the usability features: color, quick start, typo hints, skill search,
the HTML dashboard, saved check results, shell completion, and the launcher."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tooling"))

from ai_toolkit import cli, completion, dashboard, skills, style  # noqa: E402

CARD = {
    "version": 2,
    "status": "ORANGE",
    "decision": "allow",
    "policy": "baseline",
    "operation": "change",
    "subject": {"type": "git-commit", "revision": "a" * 40},
    "enforced": {"passed": 0, "total": 0, "percent": None},
    "advisory": {"passed": 1, "total": 3, "percent": 33.3},
    "readiness": {"GREEN": 1, "ORANGE": 2, "GRAY": 0, "RED": 0},
    "controls": [
        {"id": "unit-tests", "name": "Unit Tests", "effective_mode": "advisory", "readiness": "GREEN",
         "authoritative_provider": {"display_name": "Repository Unit Test Command"},
         "authoritative_evidence_status": "passed", "authoritative_result": {"status": "passed"}},
        {"id": "change-scope", "name": "PR Change Scope", "effective_mode": "advisory", "readiness": "ORANGE",
         "authoritative_provider": {"display_name": "PR Change Scope"},
         "authoritative_evidence_status": "failed", "authoritative_result": {"status": "failed"}},
        {"id": "format-and-lint", "name": "Format <and> Lint", "effective_mode": "advisory", "readiness": "ORANGE",
         "authoritative_provider": {"display_name": "Lint \"cmd\""},
         "authoritative_evidence_status": "no_result",
         "authoritative_result": {"status": "no_result", "reason": "GUARDRAILS_FORMAT_LINT_COMMAND is not configured; <script>x</script>"}},
    ],
    "findings": [],
    "artifacts": {"evidence": "e.json", "report": "r.md"},
}


def run_cli(*arguments: str) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(list(arguments))
    return code, stdout.getvalue(), stderr.getvalue()


class StyleTests(unittest.TestCase):
    def tearDown(self) -> None:
        style.set_enabled(None)

    def test_color_is_off_for_pipes_and_respects_no_color_and_force(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "", "FORCE_COLOR": "", "TERM": "xterm"}):
            self.assertFalse(style.enabled(io.StringIO()))
        with patch.dict(os.environ, {"NO_COLOR": "1", "FORCE_COLOR": "1"}):
            self.assertFalse(style.enabled())
        with patch.dict(os.environ, {"NO_COLOR": "", "FORCE_COLOR": "1"}):
            self.assertTrue(style.enabled(io.StringIO()))
        style.set_enabled(False)
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}):
            self.assertFalse(style.enabled())

    def test_colorize_never_changes_words(self) -> None:
        text = ("Toolkit check: ORANGE / allow\nSummary: 1 passed\n\n  PASS  unit-tests — x\n  FAIL  scope [advisory]\n"
                "        Next: fix it\n  NO_RESULT lint\n  installed  guardrails: runtime is not installed.\n  [ACTION_NEEDED] x")
        colored = style.colorize(text)
        self.assertNotEqual(colored, text)
        self.assertEqual(style.strip(colored), text)
        # A state word inside a sentence is left alone; only the state column is colored.
        line = [row for row in colored.split("\n") if "guardrails:" in row][0]
        self.assertTrue(line.endswith("runtime is not installed."))
        # Tokens embedded in identifiers are not colored.
        self.assertEqual(style.colorize("  PASSING-tests FAILURE"), "  PASSING-tests FAILURE")


class EntryPointUsabilityTests(unittest.TestCase):
    def test_bare_command_prints_quick_start(self) -> None:
        code, out, err = run_cli()
        self.assertEqual(code, 0, err)
        self.assertIn("Quick start", out)
        self.assertIn("skrillx init --preview", out)

    def test_typo_suggests_the_closest_command(self) -> None:
        code, _, err = run_cli("doctr")
        self.assertEqual(code, 2)
        self.assertIn("Did you mean `skrillx doctor`?", err)
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                cli.main(["zzzzzz"])

    def test_no_color_flag_is_accepted_anywhere(self) -> None:
        code, out, _ = run_cli("--no-color", "skills", "list")
        self.assertEqual(code, 0)
        self.assertNotIn("\033[", out)
        style.set_enabled(None)


class SkillSearchTests(unittest.TestCase):
    def test_catalog_has_descriptions_for_every_skill(self) -> None:
        catalog = skills.skill_catalog()
        self.assertEqual([row["name"] for row in catalog], skills.canonical_skills())
        self.assertTrue(all(row["description"] for row in catalog))
        self.assertTrue(any(row["starter"] for row in catalog))

    def test_search_matches_word_starts_and_ranks_name_matches_first(self) -> None:
        names = [row["name"] for row in skills.search_skills("security")]
        self.assertEqual(names[0], "security-audit-lite")
        self.assertEqual(skills.search_skills("zzqq-nothing"), [])
        self.assertTrue(all("github" in (row["name"] + row["description"]).lower() for row in skills.search_skills("github actions")))

    def test_skills_cli_list_search_show(self) -> None:
        code, out, _ = run_cli("skills", "list", "--json")
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertIn("code-review", payload["skills"])
        self.assertEqual(len(payload["details"]), len(payload["skills"]))
        code, out, _ = run_cli("skills", "list")
        self.assertIn("code-review", out.splitlines())
        code, out, _ = run_cli("skills", "list", "--long")
        self.assertIn("(* = starter set)", out)
        self.assertIn("* code-review", out)
        code, out, _ = run_cli("skills", "search", "security")
        self.assertEqual(code, 0)
        self.assertIn("security-audit-lite", out)
        code, _, err = run_cli("skills", "search")
        self.assertEqual(code, 2)
        self.assertIn("needs a query", err)
        code, out, _ = run_cli("skills", "show", "code-review", "--json")
        self.assertEqual(code, 0)
        self.assertIn("SKILL.md", json.loads(out)["files"])
        code, _, err = run_cli("skills", "show", "code-reveiw")
        self.assertEqual(code, 2)
        self.assertIn("did you mean code-review", err)


class DashboardTests(unittest.TestCase):
    def test_render_escapes_values_and_groups_controls(self) -> None:
        page = dashboard.render_html(CARD, generated_at="2026-01-01T00:00:00Z")
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)
        self.assertIn("Format &lt;and&gt; Lint", page)
        self.assertIn('data-filter="failed"', page)
        self.assertIn("33.3%", page)
        # Failed controls are listed before passed ones.
        self.assertLess(page.index("change-scope"), page.index("unit-tests</code>"))
        # Nothing is loaded from the network.
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)

    def test_render_tolerates_a_sparse_card(self) -> None:
        page = dashboard.render_html({"controls": [], "status": "GRAY"})
        self.assertIn("No controls in this card.", page)


class SavedCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.target = Path(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_report_without_a_saved_check_explains_what_to_do(self) -> None:
        code, _, err = run_cli("report", "--target", str(self.target))
        self.assertEqual(code, 2)
        self.assertIn("run `skrillx check` first", err)

    def test_check_saves_the_card_and_report_renders_text_and_html(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(CARD), stderr="")
        with patch.object(cli, "installed_runtime", return_value=self.target), \
                patch.object(cli, "script_path", return_value=self.target / "scan.py"), \
                patch.object(cli, "run_python", return_value=completed):
            code, out, _ = run_cli("check", "--target", str(self.target), "--html")
        self.assertEqual(code, 0)
        self.assertIn("Summary: 1 passed · 1 failed · 1 unverified · 0 not activated", out)
        self.assertIn("Dashboard:", out)
        self.assertTrue((self.target / cli.LAST_CHECK).is_file())
        self.assertTrue((self.target / cli.DEFAULT_DASHBOARD).is_file())

        code, out, _ = run_cli("report", "--target", str(self.target))
        self.assertEqual(code, 0)
        self.assertIn("Last check:", out)
        self.assertIn("FAIL  change-scope", out)

        custom = self.target / "out" / "card.html"
        code, out, _ = run_cli("report", "--target", str(self.target), "--html", str(custom), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["dashboard"], str(custom))
        self.assertIn("Guardrails Scorecard", custom.read_text(encoding="utf-8"))

        with patch("webbrowser.open") as opened:
            code, _, _ = run_cli("report", "--target", str(self.target), "--open")
        self.assertEqual(code, 0)
        opened.assert_called_once()

    def test_corrupt_saved_check_is_a_usage_error(self) -> None:
        path = self.target / cli.LAST_CHECK
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        code, _, err = run_cli("report", "--target", str(self.target))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)


class CompletionTests(unittest.TestCase):
    def test_scripts_cover_every_command(self) -> None:
        parser = cli.build_parser()
        commands = completion.describe(parser)
        for expected in ("init", "doctor", "check", "report", "skills", "completion"):
            self.assertIn(expected, commands)
        self.assertIn("search", commands["skills"]["choices"])
        for shell in completion.SHELLS:
            text = completion.script(shell, parser)
            for name in commands:
                self.assertIn(name, text)
        with self.assertRaises(ValueError):
            completion.script("powershell", parser)

    @unittest.skipUnless(shutil.which("bash"), "bash is not installed")
    def test_bash_completion_completes_commands_and_choices(self) -> None:
        code, script, _ = run_cli("completion", "bash")
        self.assertEqual(code, 0)
        probe = script + (
            'COMP_WORDS=(skrillx rep); COMP_CWORD=1; _skrillx; echo "${COMPREPLY[*]}"\n'
            'COMP_WORDS=(skrillx check --operation ""); COMP_CWORD=3; _skrillx; echo "${COMPREPLY[*]}"\n'
        )
        completed = subprocess.run(["bash", "-c", probe], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        first, second = completed.stdout.strip().splitlines()
        self.assertEqual(first, "report")
        self.assertEqual(second.split(), ["change", "release"])


class LauncherTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bash"), "bash is not installed")
    def test_launcher_wrapper_runs_from_any_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "bin"
            completed = subprocess.run(["bash", str(ROOT / "tooling" / "install-cli.sh"), "--prefix", str(prefix)],
                                       text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            link = prefix / "skrillx"
            self.assertTrue(link.is_file())
            self.assertIn("written by tooling/install-cli.sh", link.read_text(encoding="utf-8"))
            # Installing again replaces the managed wrapper instead of refusing.
            completed = subprocess.run(["bash", str(ROOT / "tooling" / "install-cli.sh"), "--prefix", str(prefix)],
                                       text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            completed = subprocess.run([str(link), "--version"], cwd=directory, text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("skrillx", completed.stdout)
            completed = subprocess.run(["bash", str(ROOT / "tooling" / "install-cli.sh"), "--prefix", str(prefix), "--uninstall"],
                                       text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(link.exists())

    @unittest.skipUnless(shutil.which("bash"), "bash is not installed")
    def test_installer_refuses_to_replace_a_real_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "skrillx").write_text("mine", encoding="utf-8")
            completed = subprocess.run(["bash", str(ROOT / "tooling" / "install-cli.sh"), "--prefix", directory],
                                       text=True, capture_output=True)
            self.assertEqual(completed.returncode, 1)
            self.assertEqual((Path(directory) / "skrillx").read_text(encoding="utf-8"), "mine")


if __name__ == "__main__":
    unittest.main()

"""Terminal styling for human-readable CLI output.

Color is applied only when stdout is an interactive terminal, ``NO_COLOR`` is
unset (https://no-color.org), ``TERM`` is not ``dumb``, and ``--no-color`` was
not passed. ``FORCE_COLOR`` turns it on for pipes and CI logs. JSON output is
never styled, and styling never changes the words: stripping the escape codes
gives back exactly the plain-text report.
"""

from __future__ import annotations

import os
import re
import sys
from typing import TextIO

RESET = "\033[0m"
CODES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "gray": "90",
}
ANSI = re.compile(r"\033\[[0-9;]*m")

_forced: bool | None = None


def set_enabled(value: bool | None) -> None:
    """Force color on (True) or off (False); None restores auto-detection."""
    global _forced
    _forced = value


def enabled(stream: TextIO | None = None) -> bool:
    if _forced is not None:
        return _forced
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    stream = stream or sys.stdout
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def paint(text: str, *styles: str) -> str:
    codes = ";".join(CODES[style] for style in styles if style in CODES)
    return f"\033[{codes}m{text}{RESET}" if codes else text


def strip(text: str) -> str:
    return ANSI.sub("", text)


# Whole-word status tokens and the style each one gets. Order matters: longer
# tokens are matched first so NO_RESULT is not split into NO + RESULT.
TOKENS = {
    "PASS": ("green", "bold"),
    "PASSED": ("green", "bold"),
    "GREEN": ("green", "bold"),
    "[CONFIGURED]": ("green",),
    "FAIL": ("red", "bold"),
    "FAILED": ("red", "bold"),
    "RED": ("red", "bold"),
    "ERROR": ("red", "bold"),
    "[ACTION_NEEDED]": ("red",),
    "ORANGE": ("yellow", "bold"),
    "NO_RESULT": ("yellow",),
    "NOT_RUN": ("yellow",),
    "BLOCKED": ("yellow", "bold"),
    "MISSING": ("yellow",),
    "[UNVERIFIED]": ("yellow",),
    "GRAY": ("gray",),
}
_TOKEN_PATTERN = re.compile(
    r"(?<![\w\[-])(" + "|".join(re.escape(token) for token in sorted(TOKENS, key=len, reverse=True)) + r")(?![\w\]-])"
)
_HEADING = re.compile(r"^(What ran and passed|What failed|What remains unverified|Not activated|Components|Capabilities|"
                      r"Guardrails diagnostics|Planned changes|Toolkit check|Toolkit doctor|Summary|Quick start)\b.*$")
_NEXT = re.compile(r"^(\s+)(Next:)")
# Lower-case states are colored only in the state column at the start of a row.
STATES = {"verified": ("green",), "configured": ("cyan",), "installed": ("cyan",), "missing": ("red",)}
_STATE = re.compile(r"^(\s+)(verified|configured|installed|missing)(\s)")


def colorize(text: str) -> str:
    """Add color to a rendered plain-text report. Words are never changed."""
    lines = []
    for line in text.split("\n"):
        if _HEADING.match(line):
            lines.append(paint(line, "bold"))
            continue
        line = _STATE.sub(lambda match: match.group(1) + paint(match.group(2), *STATES[match.group(2)]) + match.group(3), line)
        line = _NEXT.sub(lambda match: match.group(1) + paint(match.group(2), "cyan", "bold"), line)
        line = _TOKEN_PATTERN.sub(lambda match: paint(match.group(1), *TOKENS[match.group(1)]), line)
        lines.append(line)
    return "\n".join(lines)

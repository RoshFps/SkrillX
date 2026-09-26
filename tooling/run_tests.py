#!/usr/bin/env python3
"""Run the repository's unit-test suites, one module per worker process.

Each test module runs in its own ``python3 -m unittest`` process, so modules
never share interpreter state and can run concurrently. Output is buffered per
module and printed in a stable order; the exit code is non-zero if any module
fails or no tests were collected.

    python3 tooling/run_tests.py            # all suites, one worker per CPU
    python3 tooling/run_tests.py -j 1       # sequential (same as before)
    python3 tooling/run_tests.py -k doctor  # only modules whose name contains "doctor"
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUITES = (
    "guardrails/tests",
    "tooling/tests",
    "tooling/validators/tests",
    "examples/python-demo",
)
# Modules that dominate wall time (measured); scheduled first.
HEAVY = ("test_consumer_lifecycle", "test_doctor", "test_ai_toolkit_cli", "test_python_demo")
RAN = re.compile(r"^Ran (\d+) tests? in", re.MULTILINE)


@dataclass
class Result:
    suite: str
    module: str
    code: int
    tests: int
    seconds: float
    output: str


def modules(suite: str, keyword: str | None) -> list[str]:
    directory = ROOT / suite
    names = sorted(path.stem for path in directory.glob("test_*.py"))
    return [name for name in names if not keyword or keyword in name]


def run_module(suite: str, module: str) -> Result:
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", suite, "-p", f"{module}.py"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    output = completed.stdout + completed.stderr
    match = RAN.search(output)
    return Result(suite, module, completed.returncode, int(match.group(1)) if match else 0,
                  time.perf_counter() - started, output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-j", "--jobs", type=int, default=int(os.environ.get("TEST_JOBS", "0")) or os.cpu_count() or 1,
                        help="parallel workers (default: CPU count, or $TEST_JOBS)")
    parser.add_argument("-k", "--keyword", help="only run modules whose file name contains this text")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every module's output, not only failures")
    args = parser.parse_args(argv)

    work = [(suite, module) for suite in SUITES for module in modules(suite, args.keyword)]
    # Start the modules that spawn many git/python subprocesses first so they do not
    # become the tail of the run; the report below is still printed in suite order.
    order = sorted(work, key=lambda item: (item[1] not in HEAVY, work.index(item)))
    if not work:
        print("No test modules matched.", file=sys.stderr)
        return 1
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {item: pool.submit(run_module, *item) for item in order}
        results = [futures[item].result() for item in work]
    elapsed = time.perf_counter() - started

    failed = [result for result in results if result.code != 0]
    for result in results:
        if args.verbose or result.code != 0:
            print(f"==== {result.suite}/{result.module}.py ====")
            print(result.output.rstrip())
    total = sum(result.tests for result in results)
    slowest = sorted(results, key=lambda result: result.seconds, reverse=True)[:3]
    print(f"Ran {total} tests from {len(results)} modules in {elapsed:.1f}s with {max(1, args.jobs)} workers.")
    print("Slowest: " + ", ".join(f"{result.module} {result.seconds:.1f}s" for result in slowest))
    if failed:
        print("FAILED: " + ", ".join(f"{result.suite}/{result.module}.py" for result in failed))
        return 1
    if total == 0:
        print("FAILED: no tests were collected.")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

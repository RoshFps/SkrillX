#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "${repo_root}"

# Runs guardrails/tests, tooling/tests, tooling/validators/tests, and the
# python-demo tests, one module per process in parallel. Pass -j 1 to run
# sequentially, or -k NAME to select modules.
exec python3 tooling/run_tests.py "$@"

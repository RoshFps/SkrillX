# SkrillX

**Move fast. Prove it works.** Shared skills, QA workflows, and guardrails for
planning, building, testing, securing, and releasing software with AI.

[![License](https://img.shields.io/github/license/RoshFps/ai-software-toolkit?label=license)](LICENSE)
[![Scorecard Workflow](https://github.com/RoshFps/ai-software-toolkit/actions/workflows/guardrails-scorecard.yml/badge.svg?event=pull_request_target)](https://github.com/RoshFps/ai-software-toolkit/actions/workflows/guardrails-scorecard.yml)

SkrillX supports development, QA, security, and release teams.
Skills guide repeatable work, functional QA exercises application behavior,
and Guardrails connects verification results to policy through revision-bound
checks and readable scorecards. Your repository owns its architecture,
acceptance criteria, and commands.

Maintained by [Roshan Immanuel](https://github.com/RoshFps). See
[NOTICE](NOTICE) and [LICENSE](LICENSE) for attribution.

## Get going in one minute

```sh
git clone https://github.com/RoshFps/ai-software-toolkit.git
bash ai-software-toolkit/tooling/install-cli.sh   # puts `skrillx` on your PATH
cd /path/to/your/repo
skrillx                                           # prints the quick start
```

| Step | Command | What happens |
| --- | --- | --- |
| 1 | `skrillx discover` | Detects languages, build/test/lint commands, workflows, and agent clients. Read-only. |
| 2 | `skrillx init --preview` | Shows every file it would add. Nothing is written. |
| 3 | `skrillx init --yes` | Installs Guardrails, the starter skills, and QA bootstrap. |
| 4 | `skrillx doctor` | Reports what is installed, configured, and verified, and the next step for each gap. |
| 5 | `skrillx check --html` | Runs the scan and writes an HTML scorecard dashboard. |

What's new in this version:

- **HTML scorecard dashboard.** `skrillx check --html` or
  `skrillx report --open` renders the latest result as a single offline page
  with status filters, search, and light/dark themes.
- **Clearer terminal output.** Colored PASS / FAIL / NO_RESULT, a one-line
  summary, a quick start when run bare, and "did you mean" hints for typos.
  Plain output in pipes and CI, or with `--no-color` / `NO_COLOR=1`.
- **Find skills fast.** `skrillx skills list` shows what each skill does;
  `skills search security` and `skills show code-review` find and explain one.
- **Tab completion.** `skrillx completion bash|zsh|fish`.
- **Faster test runs.** `tooling/test.sh` runs test modules in parallel.
- **Up-to-date pins.** The workflow templates pin every GitHub Action to its latest release.

See the [changelog](CHANGELOG.md#unreleased) for details.

## What the toolkit brings together

| Component | Purpose | Start here |
| --- | --- | --- |
| Standards | Define expectations for quality, security, and accountable AI use | [AI development policy](policies/ai-development.md) |
| Skills | Guide agents through repeatable development, QA, security, and release work | [Install shared skills](skills/README.md#install-locally) |
| Verification | Produce evidence from tests, functional QA, and scanners | [Set up functional QA](skills/qa-bootstrap/SKILL.md) |
| Guardrails | Evaluate evidence against policy and expose missing results | [Install and configure Guardrails](docs/quickstart.md) |
| Measurement — aspiration | Learn whether delivery is improving across the lifecycle | [Vision and maturity](docs/vision.md) |

QA helps shape acceptance criteria and risk coverage, explores behavior, and
feeds failures back into future validation. Quality is shared across the
lifecycle; QA expertise is part of planning and improvement as well as testing.

See [the toolkit vision](docs/vision.md) for the Plan → Build → Validate →
Release → Improve direction and the distinction between available components,
optional integrations, and future work.

## Start here

Try the embedded Python demo in an isolated directory with Git, Python 3.11+
and a POSIX shell. “Guardrails v2” names the runtime and evidence contract,
not the repository release version. No account, token, Docker, or paid
service is required to get a scorecard.

```sh
demo_workspace="$(mktemp -d)"
git clone https://github.com/RoshFps/ai-software-toolkit.git "$demo_workspace/ai-software-toolkit"
standards_root="$demo_workspace/ai-software-toolkit"
cp -R "$standards_root/examples/python-demo" "$demo_workspace/python-demo"
cd "$demo_workspace/python-demo"

# The embedded demo already has an installation; refresh its shipped runtime.
python3 "$standards_root/tooling/install.py" --target . --refresh-existing --dry-run
python3 "$standards_root/tooling/install.py" --target . --refresh-existing
python3 .guardrails/configure.py --set unit-tests=advisory
export GUARDRAILS_BUILD_COMMAND='python3 -m compileall -q app.py test_app.py tools .guardrails'
export GUARDRAILS_UNIT_TEST_COMMAND="python3 -m unittest discover -s . -p 'test_*.py'"
export GUARDRAILS_WORKING_DIRECTORY='.'

# Local evidence requires a committed, clean HEAD. Identity is demo-only.
git init -q
git add .
git -c user.name='Guardrails Demo' -c user.email='demo@example.invalid' commit -qm 'chore: initialize Guardrails demo'
python3 .guardrails/scan.py
```

The scanner executes the configured demo commands and writes JSON evidence and
a timestamped Markdown report under `.artifacts/guardrails/`. It does not push
anything. Build and unit tests can pass locally; unconfigured commands,
unavailable scanner tools, and GitHub-only checks do **not** become passes.
Expect advisory gaps, not an all-green promise.

A small **illustrative** scorecard (not a live scan or badge):

| Readiness | Capability | Evidence |
| --- | --- | --- |
| 🟢 GREEN | Unit tests | Passed for the exact subject |
| 🟠 ORANGE | Changed-code coverage | No result; advisory |
| 🔴 RED | Build, if enforced | No result; blocks |
| ⚪ GRAY | Artifact provenance in a PR | Not activated |

See the [full illustrative report](docs/examples/sample-scorecard.md),
[status meanings](docs/guardrails/control-status.md), and
[onboarding guide](docs/quickstart.md) for real-repository setup and troubleshooting.

## Guardrails model

```text
profile -> capability -> authoritative provider -> exact-subject evidence
                  \---- supplemental providers ----> advisory evidence
```

A capability is an engineering outcome; its authoritative provider produces
the evidence. Supplemental providers stay advisory and cannot satisfy or block
it. Configuration expresses intent, not proof of execution. A missing check is
not a pass.

## Install

The shared [`skrillx` CLI](docs/install.md) is the front door for Guardrails,
skills, and QA bootstrap: `discover` and `init --preview` are read-only,
`init --yes` installs the selected components and records `toolkit.toml` and
`toolkit.lock.json`, `doctor` reports installed / configured / verified state
without executing anything, `check` explains what ran, failed, and remains
unverified, and `update` refreshes managed files while preserving your edits.
The same code serves the CLI, the `toolkit-setup` skill, and the
`SkrillX Setup` starter workflow.

For the underlying installer, [preview and install Core](docs/quickstart.md#1-preview-and-install-core),
then [configure real commands](docs/quickstart.md#3-configure-repository-commands)
and [declare ground truth](docs/quickstart.md#4-declare-repository-ground-truth).
Do not substitute demo commands or no-ops for your application's validation.
The installer copies runtime/configuration and workflow files, not credentials.

## Configure and run

Follow [inspect policy and run](docs/quickstart.md#5-inspect-policy-and-run).
Commit installation and configuration before scanning. Dirty worktrees produce
no-result evidence rather than a passing claim about `HEAD`.
[Setup diagnostics](docs/quickstart.md#diagnose-installation)
inspect setup without executing your commands. Their `configured`,
`action_needed`, and `unverified` states describe
setup, not scan results. Exit zero is not a pass.

## Profiles

Core is the default advisory profile: repository/documentation/ground-truth
validation, scope, PR metadata, lint, migration validation, build, unit tests,
changed-code coverage, Semgrep CE, and Gitleaks CLI. The optional additive
[GitHub profile](docs/quickstart.md#2-add-the-optional-github-profile) includes
CodeQL, Dependency Review, Secret Protection, and Dependabot verification.
Its release-attestation workflow is not PR scorecard evidence.

## Modes and providers

Keep capabilities advisory until their producer, stable check name,
exact-subject evidence, and remediation owner are verified.
[Promote one proven capability](docs/quickstart.md#8-promote-one-proven-capability);
policy mode and GitHub rulesets are separate settings. AI review remains
advisory-only. Agent-driven functional QA is an opt-in capability whose
workflow the [`qa-bootstrap` skill](skills/qa-bootstrap/SKILL.md) generates. See
[provider and control setup](docs/guardrails/control-setup.md).

## Status vocabulary

🟢 **GREEN**: authoritative pass. 🟠 **ORANGE**: advisory gap.
🔴 **RED**: enforced gap or wrong-subject evidence; blocked.
⚪ **GRAY**: inactive for this operation/subject.
Raw `not_run` or absent evidence is displayed as `no_result`, never a pass.
The default report omits inactive catalog rows; use `--all-catalog-controls`
to include them. See the [status guide](docs/guardrails/control-status.md).

## What runs on GitHub

Installed workflows make producers available; files alone do not prove
activation. Configure supported providers and real command variables, then
[verify a pull request](docs/quickstart.md#7-open-a-pull-request).
The collector checks the exact PR head and trusted provider provenance.
Do not make a check required until you have observed reliable results.

## Two useful badges

**Scorecard Workflow** reports workflow execution. **Latest PR Scorecard**
reports the newest accepted PR evaluation, not current `main`; workflow
success can still mean `ORANGE / ALLOW`.
[Badge setup, URLs, Pages ownership, and privacy](docs/quickstart.md#publish-the-optional-scorecard-badge)
live in the onboarding guide. Publication never changes enforcement.

## Local and pull-request flow

```text
local scan -> fix findings -> PR -> independent producers -> exact-head scorecard
```

Local results are machine feedback, not authoritative merge evidence. Follow
[workflow guidance](workflows/README.md) and [ruleset guidance](rulesets/README.md)
before requiring checks.

## Ground truth and future capabilities

Repositories own their architecture, testing, security, deployment, and
contribution docs; map existing paths in `.guardrails/ground-truth-ai.yaml`.
Artifact, deployment, and runtime capabilities without implemented producers
remain evidence contracts, not runnable assurances. See the
[architecture](docs/guardrails/architecture.md) and [producer contract](docs/guardrails/producer-contract.md).

## Repository map

Browse the [documentation index](docs/README.md) for adoption, operating guides,
standards, and retained design history. To run the toolkit against this repository,
use the [self-check guide](docs/self-check.md).

| Path | Purpose |
| --- | --- |
| `policies/` | Capabilities, profiles, providers, and engineering policy |
| `guardrails/`, `tooling/` | Evaluator, installer, producers, and validators |
| `workflows/`, `rulesets/` | GitHub workflow and enforcement templates |
| `skills/` | Reusable agent instructions |
| `pr-review/`, `prompts/`, `templates/` | Review contracts and reusable guidance |
| `security/` | Tested scanner rules and fixtures |
| `examples/` | Runnable consumers |
| `docs/guardrails/`, `docs/standards/` | Runtime guides and software delivery standards |
| `docs/archive/` | Historical designs and plans; current behavior is documented elsewhere |
| `.guardrails/`, `.github/workflows/`, `.agents/` | This repository's installed toolkit and CI |

The source and installed directories are intentional: the toolkit is also its
own consumer. See [source ownership and installed copies](docs/README.md#source-ownership-and-installed-copies)
before changing or refreshing them.

## License and validation

MIT licensed; third-party tools keep their own terms. See
[licensing](docs/licensing.md), [contributing](CONTRIBUTING.md), and the
[complete validation commands](AGENTS.md#verification).
Run `tooling/test.sh` for the repository's four unit-test suites (in parallel; `-j 1` runs them one at a time).
Read the [changelog](CHANGELOG.md) and [v1.0.0 release notes](docs/releases/v1.0.0.md)
for supported contracts, upgrade instructions, and limitations.

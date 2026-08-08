# SwingMachine

SwingMachine is a deterministic daily-bar swing-trading research system. The
repository contains research, replay, paper-adapter, shadow, audit, and reporting
capabilities, but capability is not operational authority.

## Current authority

The current phase is controlled offline research and qualification only.

- No revised baseline candidate is selected.
- PULLBACK is `PARKED_INCONCLUSIVE`.
- H1 and H2 are parked after `NO_FAMILY_PASSES_DISCOVERY`.
- TIGHT_BASE remains isolated unless separately redesigned and requalified.
- Gate 2 and the frozen holdout remain unopened.
- Paper trading is blocked.
- Live trading is prohibited.
- Broker, provider, API, runtime, acquisition, and state-changing actions require
  separate exact human approval.
- No further strategy-screen implementation ticket is currently authorised.

Read the current source of truth in this order:

1. `docs/project-control/*.md`
2. Current code, tests, and config for the bounded task
3. Other documents and generated reports as historical evidence only

Start with:

- `docs/project-control/02_CURRENT_STATE.md`
- `docs/project-control/04_DECISION_LOG.md`
- `docs/project-control/05_BACKLOG_AND_ROADMAP.md`
- `docs/project-control/07_CODEX_WORKFLOW_AND_GUARDRAILS.md`
- `docs/project-control/08_OPEN_RISKS_AND_QUESTIONS.md`

Older paper-readiness, paper-run, serious-run, acquisition, and implementation
documents do not authorise those actions. Generated reports are evidence, not
proof, and do not override the project-control gates.

## Repository layout

- `src/swingmachine/`: application and offline research package
- `tests/`: unit, contract, replay, research, and adapter tests
- `config/`: explicit strategy and offline research configuration
- `scripts/`: historical acquisition/build/screen tooling; see
  `scripts/README.md` before use
- `docs/project-control/`: current authority and decision records
- `docs/`: historical design, qualification, and implementation evidence
- `reports/` and `data/`: ignored local evidence/data, not durable source of truth

## Local setup

Python 3.11 is required.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Do not install packages or run operational commands in a controlled task unless
the task explicitly permits them.

## Offline quality checks

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy --config-file mypy_core.ini
.venv/bin/python -m pytest -q
```

The CLI exposes runtime and paper-adapter commands for mechanical testing. Their
presence is not permission to run them. Refer to
`docs/project-control/06_RUN_TEST_DEPLOY_GUIDE.md` and obtain exact human
approval before any broker, provider, API, runtime, paper, live, deployment, or
state-changing action.

## Configuration policy

Strategy behavior must live in explicit reviewed config/profile files, never in
hidden environment settings. `.env.example` is infrastructure-only and defaults
to shadow/offline-safe values. Machine-local provider paths belong in ignored
local config, using the tracked `.example.yaml` file as a template.

No profitability or readiness guarantee is made. Backtests and diagnostics are
bounded evidence only.

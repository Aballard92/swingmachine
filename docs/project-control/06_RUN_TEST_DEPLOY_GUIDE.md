# 06 Run, Test, Deploy Guide - swingmachine

## Safety status

Current status:

- Paper trading: blocked.
- Live trading: prohibited.
- Serious full run: blocked until a revised candidate is selected for offline qualification.

This guide records known commands, but commands that can touch paper/live/broker paths require explicit human approval before use.

## Setup commands

Typical local setup from repo root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Known environment note:

- If `.venv` Python exists but `pip` is missing, prior recovery used `get-pip.py` successfully.
- Do not install packages unless explicitly asked.

## Main CLI

Package entrypoint:

```bash
.venv/bin/swingmachine --help
```

Python module entrypoint:

```bash
.venv/bin/python -m swingmachine --help
```

## Common offline/research commands

Examples seen in repo docs and logs:

```bash
.venv/bin/swingmachine run-historical-scanner-replay --manifest <manifest.yaml> --output-dir <reports/output_dir>
.venv/bin/swingmachine run-historical-portfolio-lifecycle-replay --manifest <manifest.yaml> --output-dir <reports/output_dir>
.venv/bin/swingmachine build-prepared-feature-panel --manifest <manifest.yaml> --output <features.parquet> --provenance-output <provenance.json> --no-update-manifest
```

Use only with offline manifests and report outputs unless explicitly authorised.

## Test commands

Focused tests are preferred for bounded Codex tasks.

Examples:

```bash
.venv/bin/python -m pytest tests/test_feature_outcomes.py
.venv/bin/python -m pytest tests/test_config.py tests/test_contracts.py
.venv/bin/python -m pytest tests/test_replay_workflow.py::test_historical_scanner_replay_writes_density_artifacts -q
```

Full test suite can be slow. Use only when explicitly requested or when the task warrants broad verification.

```bash
.venv/bin/python -m pytest
```

## Lint/typecheck/build commands

Ruff is configured in `pyproject.toml`.

```bash
.venv/bin/python -m ruff check <paths>
```

No separate typecheck command was identified as a current source-of-truth command.

Build/install source of truth is `pyproject.toml`.

## Environment variables and config requirements

Config source-of-truth:

- `swing_trading_bot_config_template_v2.yaml`
- `config/swing_machine_v0_1_profile.yaml`
- selected-period configs under `config/`
- Trading212 source config at `config/swing_machine_v0_1_trading212_sources.yaml`

Rules:

- `.env` may contain credentials, API keys, infrastructure paths, environment names, and safe operational switches.
- `.env` must not secretly control strategy behavior.
- Strategy behavior must be explicit, reviewable, and serialisable in config/profile files.
- Do not expose secrets in docs or reports.

## Known failure points

- Full pytest collection can be slow if import-time behavior regresses.
- Older memory notes say import-time issues were previously caused by eager exports and Pydantic model build cost.
- Long scanner/lifecycle replays can run for many minutes.
- Historical provider coverage differs between Alpaca and Hugging Face.
- Hugging Face current data cannot support like-for-like broad validation.
- Some older runbooks imply paper readiness, but current gate blocks paper trading.
- Generated reports may be superseded; prefer current project-control and next-candidate docs.

## Deployment status

No production deployment flow is currently approved from this repo.

Do not run:

- Live broker execution.
- Paper trading execution.
- Production deployment.
- Destructive migrations.
- Full serious qualification without a selected candidate and explicit approval.

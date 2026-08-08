# Swing Machine v0.1 guarded serious full-run plan

> **Historical and superseded.** Serious full qualification is currently
> blocked because no revised candidate is selected. This plan grants no current
> execution authority.

Date: 2026-05-06
Baseline: `swing_machine_v0_1`
Readiness artifact: `reports/swing_machine_v0_1/historical_freeze_readiness.json`
Operator approval: `reports/swing_machine_v0_1/historical_operator_freeze_approval.json`

## Current authorization state

The historical freeze readiness decision is now `ALLOW` with zero blockers after operator approval was recorded.

This authorizes preparation of a guarded serious full-run package. It does not authorize live trading, real broker orders, production deployment, destructive database changes, or unattended execution beyond the explicitly approved run command.

## Preconditions before execution

Before any serious full run is executed, confirm all of the following:

- `reports/swing_machine_v0_1/historical_freeze_readiness.json` still reports `decision: ALLOW` and `serious_full_run_allowed: true`.
- The config hash in readiness still matches the reviewed profile: `6f207c4ca6edd7240cb0646cd7bb1354d9f1cd0895d12e4b835b2d78ea27fbe1`.
- The run is dry-run, replay, research, or paper-safe only unless a separate live-trading approval is explicitly granted.
- No broker credentials or `.env` strategy overrides are used to alter strategy behaviour.
- Output is written to a new timestamped folder under `reports/swing_machine_v0_1/`.
- The command is run with a bounded timeout and does not trigger production deployment.

## Recommended first serious full-run shape

Use a guarded historical serious run before considering any live or paper-runtime action:

- Source: historical selected-period/manifests already qualified from Alpaca historical panels.
- Mode: replay/backtest/reporting only.
- Scope: full reviewed historical baseline package, not live broker execution.
- Output: timestamped report directory.
- Safety: no order submission outside the existing dry-run/shadow/replay paths.

## Execution command placeholder

Do not run this until the operator explicitly says to execute it.

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
timeout 3600 .venv/bin/python -c "from swingmachine.runtime import main; main()" run-historical-replay \
  --manifest data/qualification_manifests/trading212/alpaca_historical/historical_contract_stability_window_v0_1/manifest.yaml \
  --output-dir "reports/swing_machine_v0_1/serious_full_run_${RUN_ID}" \
  --config swing_trading_bot_config_template_v2.yaml
```

This placeholder uses the already qualified historical replay command family. If the intended serious full run should cover a broader panel than the selected-period manifest, create that broader manifest first, preflight it, and review the new manifest before execution.

## Post-run checks

After execution, collect:

- Replay summary
- Baseline report package
- Reconciliation status
- Validation warnings/errors
- Paper/shadow audit alignment counts
- Parity report if a paired runtime-compatible lane is run
- Any unexpected missing data, rejected orders, lifecycle divergences, or safety violations

## Stop conditions

Stop immediately if any of the following occur:

- Readiness no longer reports `ALLOW`.
- Command path indicates live trading, real broker order submission, production deployment, or destructive database mutation.
- Validation status is `FAIL`.
- Reconciliation status is `FAIL`.
- Unexpected `.env` strategy behaviour is detected.
- Output is not written to the intended report folder.

## Recommendation

The next safe action is to decide whether the serious full run should be:

1. A replay of the existing contract-stability window, which is safest but adds limited new information.
2. A broader historical manifest built from the same Alpaca source, which is more useful and still safe if preflighted first.
3. A paired research/runtime-compatible run over a broader historical manifest, which gives stronger parity evidence but takes longer.

Recommendation: build and preflight a broader historical manifest first, then run paired research/runtime-compatible serious replay if the manifest passes.

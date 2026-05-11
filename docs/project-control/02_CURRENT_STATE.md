# 02 Current State - swingmachine

## Current operational status

Current state is research/offline qualification only.

- Paper trading: blocked.
- Live trading: prohibited.
- Serious full run: blocked until a revised candidate is selected for offline qualification.
- Current candidate: no revised baseline candidate selected.
- Next best work: design deeper PULLBACK fill/lifecycle replay research.

## What currently works

The repo has substantial mechanical infrastructure:

- Python package with CLI entrypoint through `pyproject.toml`.
- Explicit strategy config via `swing_trading_bot_config_template_v2.yaml`.
- Baseline profile alias in `config/swing_machine_v0_1_profile.yaml`.
- Historical data contracts and manifest handling.
- Canonical price and feature generation.
- Regime, scoring, setup detection, entry planning, exit evaluation.
- Typed swing contracts and adapters.
- Historical scanner replay and portfolio/lifecycle replay.
- Baseline report packaging and parity checks.
- Historical performance and provider comparison reports.
- Trading212 Alpaca/Hugging Face source tooling.
- Feature/outcome attribution diagnostics.
- Paper/shadow/audit runtime components, but not approved for current use.
- Broad test coverage across contracts, config, data, replay, runtime, broker, shadow, performance, feature outcomes, and Trading212 source tooling.

## What is incomplete, broken, or unclear

Incomplete or blocked:

- No revised baseline candidate has been selected.
- PULLBACK has an interesting traded subset, but evidence is not strong enough for a profile build.
- TIGHT_BASE currently appears damaging and should be isolated unless redesigned.
- Provider-positive edge is not confirmed across both Alpaca and Hugging Face.
- Broad Hugging Face validation is unavailable with current data coverage.
- Paper-readiness remains blocked by research-edge and sample-size issues.

Unclear / needs confirmation:

- Whether future work should pursue PULLBACK fill/lifecycle behaviour or a broader new hypothesis.
- Whether broader Hugging Face data should be acquired later, and from where.
- What minimum trade/sample threshold the sponsor wants before paper readiness can be reconsidered.
- Whether ChatGPT Project should include source code files or only source-of-truth docs.

## Main repo structure

- `src/swingmachine/`: application package, runtime, replay, contracts, strategy, data, reporting, broker/paper/shadow components.
- `tests/`: broad pytest suite for unit, contract, runtime, replay, data, and report behavior.
- `docs/`: design, delivery, qualification, runbook, and decision documentation.
- `docs/project-control/`: ChatGPT Project source-control pack and repo control docs.
- `config/`: baseline profiles, selected-period plans, provider source config.
- `reports/swing_machine_v0_1/`: generated historical/research/qualification evidence. Do not bulk upload.
- `data/`: local/generated data, manifests, and qualification sources. Do not upload wholesale.
- `examples/`: example runtime and manifest inputs.

## Known limitations

- Many older docs remain in the repo and some are superseded.
- The backlog and implementation log are too large to serve as compact source-of-truth inputs.
- Generated reports are timestamped and often superseded by newer packets.
- Some paper/serious-run runbooks can be misleading if read without the current blocked gate docs.
- Broad provider validation is Alpaca-only until broader Hugging Face coverage exists.
- The current evidence does not prove profitability or benchmark-relative edge.

## Current evidence summary

Current latest decision chain:

- PULLBACK traded subset is positive, but accepted PULLBACK candidates are not positive as a group on 20-session SPY excess.
- TIGHT_BASE is negative in lifecycle and cost-stress evidence.
- Feature null filtering does not rescue accepted-edge evidence.
- Provider contract-window comparison is stable enough for research but not positive across both providers.
- Therefore no revised candidate should be built yet.

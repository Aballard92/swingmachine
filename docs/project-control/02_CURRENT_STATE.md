# 02 Current State - swingmachine

## Current operational status

Current state is research/offline qualification only.

- Paper trading: blocked.
- Live trading: prohibited.
- Serious full run: blocked until a revised candidate is selected for offline qualification.
- Current candidate: no revised baseline candidate selected.
- Historical-data posture: remaining unknowns accepted as a research limitation;
  indefinite acquisition stopped.
- PULLBACK lane: `PARKED_INCONCLUSIVE` by accepted `SWING-PC-003` Option A.
- Broader research design: `SWING-PC-005` is accepted.
- Search implementation: the single authorized `SWING-PC-005A` execution stopped
  at Gate 0 with `STOP_SOURCE_OR_TEMPORALITY_INVALID`.
- Limitation-tolerant fallback: `SWING-PC-006` completed with
  `NO_FAMILY_PASSES_DISCOVERY`.
- H1: positive mean PnL/R but failed median-R and concentration gates.
- H2: negative, concentrated, and failed multiple discovery gates.
- Frozen holdout: unopened.

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
- PULLBACK has an interesting traded subset, but the refreshed lifecycle diagnostic
  remains `INCONCLUSIVE` and is not strong enough for a profile build.
- TIGHT_BASE currently appears damaging and should be isolated unless redesigned.
- Provider-positive edge is not confirmed across both Alpaca and Hugging Face.
- Broad Hugging Face validation is unavailable with current data coverage and is
  accepted as a research limitation rather than an open-ended acquisition task.
- Paper-readiness remains blocked by research-edge and sample-size issues.
- Neither preregistered broader family passed discovery, so no candidate profile
  or later validation lane exists.

Unclear / needs confirmation:

- Whether any future decision-critical need justifies a new separately authorized
  source-remediation design; the current ticket does not.
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
- The MPS historical panel remains `PARTIAL_RESEARCH_ONLY`: classification,
  point-in-time reference, sector, shares, and halt-state gates are not all closed.
- The current evidence does not prove profitability or benchmark-relative edge.

## Current evidence summary

Current latest decision chain:

- PULLBACK traded subset is positive, but accepted PULLBACK candidates are not positive as a group on 20-session SPY excess.
- The 27 accepted rows contain only 10 submitted lifecycles: 4 filled, 6 cancelled,
  and 17 repeated same-symbol observations suppressed while another lifecycle was
  pending or open. No no-order row remains unexplained.
- TIGHT_BASE is negative in lifecycle and cost-stress evidence.
- Feature null filtering does not rescue accepted-edge evidence.
- Provider contract-window comparison is stable enough for research but not positive across both providers.
- The refreshed PULLBACK verdict is `INCONCLUSIVE`; therefore no revised candidate
  should be built yet.
- The accepted historical-data limitation and acquisition stop condition are
  controlled by `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`.
- Alex accepted `SWING-PC-003` Option A. PULLBACK is
  `PARKED_INCONCLUSIVE`; Option B and the robustness appendix are not authorized.
- `SWING-PC-005_broader_offline_hypothesis_search_design.md` preregisters only
  momentum-trend and momentum-breakout families on existing data.
- Alex accepted the design and authorized one bounded `SWING-PC-005A` screen.
- Gate 0 passed frozen hashes, config, schema/uniqueness, decision-time
  availability, fail-closed masks, and temporal boundaries.
- Gate 0 failed because there is no frozen SPY benchmark, all 974 dividend events
  lack payment dates, and 81 terminal delisted rows lack outcome semantics.
- The resulting `STOP_SOURCE_OR_TEMPORALITY_INVALID` opened no strategy outcome,
  walk-forward window, or holdout and authorizes no profile or trading work.
- Alex then authorized `SWING-PC-006`, a lower-grade absolute-return exploratory
  screen using the same H1/H2 entry masks, common lifecycle, conservative
  ex-date dividend accrual, and dual delisting scenarios.
- Stooq returned a JavaScript verification document and the sole Yahoo fallback
  returned HTTP 429. No benchmark dataset was acquired and no further network
  request was made.
- In discovery, H1 produced +3,510.02 net PnL and +0.1746 mean realised R across
  68 trades, but its median R was -0.2530 and one security supplied 61.76% of
  trades. H2 lost 509.92 across 29 trades, used only three securities, and was
  79.31% concentrated in one security.
- Outcome: `NO_FAMILY_PASSES_DISCOVERY`. Gate 2 and the holdout remained
  unopened; no revised candidate is selected.

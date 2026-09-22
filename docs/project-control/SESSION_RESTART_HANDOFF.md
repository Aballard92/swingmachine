# Session Restart Handoff - swingmachine

## Latest resumption — 8 September 2026

The sponsor requested a fresh research reset and placed Codex in charge of the
offline review, research implementation and tests. Read
`SWING-RF-001_RESEARCH_RESET.md` and `SWING-RF-001_FINDINGS.md` first.
The sponsor accepted the direction and asked for an elaborated backlog and work
to begin. Read [SWING_RF_BACKLOG.md](SWING_RF_BACKLOG.md) for the active queue and
[RF-002 delivery](SWING-RF-002_INPUT_CONTRACT_AND_READINESS.md) for the completed
input-preflight task. The shared `preflight`/`simulate` admission now checks all
rows and benchmark coverage before strategy construction. Local corpus gaps are
specific, recorded dependencies; no real daily source is qualified. RF-003 adapter
mechanics, RF-004 executable fills and RF-005 numerical design are implemented.

Latest goal checkpoint: RF-003 adapter/reference mechanics and Trading212
calendar/reader adoption are delivered, with real reference qualification open.
RF-004 is now implemented in `research_execution.py` and `research_replay.py`.
The active `simulate` command requires minutes and an explicit settlement calendar;
`simulate-daily-fixture` retains the old idealized engine only for regression work.
Read [RF-004 implementation/evidence](SWING-RF-004_EXECUTION_DESIGN.md): 30 final
execution/replay tests plus 133 existing focused regressions pass. The retained
nine-trial, 60-session synthetic replay completes with 158 intents and 727 fills.
Use `execution_v1/replay_final/`; the first `replay/` was explicitly terminated
and superseded after a partial-entry/stop sequencing correction.

RF-005 now has a byte-pinned numerical spec, nine-trial ledger, funded SPY and
lagged-exposure comparisons, plus joint stationary-block inference over 18 series.
All 186 focused research tests pass. Read
[RF-005 freeze and evidence](SWING-RF-005_EVALUATION_FREEZE.md); its config pins
the updated plan with a common 10 bps signal-planning cost across scenarios.
Earlier RF-004 result geometry is preserved as historical implementation evidence.

Next concrete work is a bounded real-source/reference qualification increment and
independent date coverage. Calendar-only coverage is 483 sessions through November
2020, or 283 after warmup, starting 17 October 2019. Validation and final dates
remain unassigned. Do not relabel limited/touched history as independent
validation. The full goal remains active. See
[Trading212 adoption](SWING-RF-003_TRADING212_ADOPTION.md) for source identity
`eddd6d8`, calendar, reader and remaining reference dependencies. Do not repeat
completed source discovery or synthetic campaigns as evidence of strategy edge.
Work is local and uncommitted. The pre-existing XR-001 audit remains untouched.
Databento raw files were located in the September import; the old Vault mount is
absent. No historical strategy returns or protected holdout outcomes have been
calculated under the reset. New research mechanics are tested on explicitly
synthetic fixtures. Paper/live/broker/runtime actions remain closed.

The August handoff below is preserved historical evidence, not a prohibition on
the newly authorised offline work. Do not confuse new mechanical tests with
profitability, forward validation, or deployment readiness.

Saved: 2026-08-08
Repository: `Aballard92/swingmachine`
Canonical branch: `main`
Merged alignment revision: `025cd92dec1dd15b2dd7177aea8963a16a184dcc`
Canonical revision: the latest `origin/main` commit containing this file.

## Current truth

- Current phase: offline research and qualification only.
- Revised baseline candidate: none selected.
- PULLBACK diagnostic: `INCONCLUSIVE`.
- PULLBACK lane: `PARKED_INCONCLUSIVE` under accepted `SWING-PC-003`
  Option A.
- Broader research design: `SWING-PC-005` is `ACCEPTED`.
- Broader screen implementation: the one authorized `SWING-PC-005A` execution is
  complete with `STOP_SOURCE_OR_TEMPORALITY_INVALID`.
- Limitation-tolerant fallback: `SWING-PC-006` completed with
  `NO_FAMILY_PASSES_DISCOVERY`.
- Gate 2 / holdout: `NOT_OPENED`.
- TIGHT_BASE: isolated unless separately redesigned and re-qualified.
- Historical-data unknowns: accepted as a fail-closed research limitation.
- Indefinite account/API/dataset/database/Vault acquisition: stopped.
- Paper trading: `BLOCKED`.
- Live trading: `PROHIBITED`.
- Broker/API/runtime actions: `NOT_AUTHORIZED`.
- Revised profile build: `NOT_AUTHORIZED`.

## Closing PULLBACK evidence

Primary report:
`reports/swing_machine_v0_1/pullback_fill_lifecycle_diagnostic_20260729T130830Z/`

- 27 raw accepted observations.
- 10 submitted lifecycles: 4 filled and 6 cancelled.
- 17 repeated same-symbol observations during an existing lifecycle: 6 pending
  and 11 open-position overlaps.
- Zero unexplained no-order rows remain.
- All-accepted 20-session SPY-excess mean: -2.4352%.
- Filled 20-session mean: +0.7578%; median: -1.8988%.
- All four fills are NFLX.

Report identities:

- JSON:
  `59cc627d6b73ca1137b7bc40b4043f957f1f92faaba564f8f18efc6917d2862f`
- Markdown:
  `c57e0eb632248430c8a982865e360457444d88f5b4d8c991154399a832435203`

## SWING-PC-005A result

Primary report:
`reports/swing_machine_v0_1/broader_offline_hypothesis_screen_20260729T171017Z/`

- Fixed hashes, parsed config, schema/uniqueness, decision-time availability,
  fail-closed masks, and frozen temporal boundaries passed.
- No frozen SPY benchmark was present.
- All 974 dividend events lacked payment dates.
- 81 terminal delisted rows had no delisting return or cash-terms fields.
- No H1, H2, or B0 strategy result was calculated.
- Discovery, both walk-forward gates, and the holdout remained unopened.

Report identities:

- JSON:
  `af4e682849d945b8d509ec2546f3e2c7d72c1602709d18794841fb4d528df102`
- Markdown:
  `8c9e952497acb2d188e130ef5d636102ede31ef4cc94bbbd06b61de1e9f2582a`

## SWING-PC-006 result

Primary report:
`reports/swing_machine_v0_1/limitation_tolerant_screen_20260729T194422Z/`

- The first attempt was invalidated by a Crostini restart before any report or
  result was written.
- The unchanged recovery execution completed.
- H1: 68 trades, seven securities, +3,510.02 net PnL, +0.1746 mean R,
  -0.2530 median R, and 61.76% maximum symbol share.
- H2: 29 trades, three securities, -509.92 net PnL, -0.0805 mean R,
  -0.2354 median R, and 79.31% maximum symbol share.
- Both families failed discovery under both delisting scenarios.
- Gate 2 and the holdout remained unopened.

Report identities:

- JSON:
  `e1ae5e0293d2ab50e630cfb9dc139fdfc61affdf6c7b470d13e2ca703f43a21a`
- Markdown:
  `751b1a9a08cd05ecb3f8d2a2ccda434070cf2223eb8b62774845dd60c4fdceca`

## Recorded decision

Read:

1. `SWING-PC-003_pullback_lane_decision_packet.md`
2. `SWING-PC-005_broader_offline_hypothesis_search_design.md`
3. `SWING-PC-006_limitation_tolerant_exploratory_screen_design.md`
4. `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`
5. `02_CURRENT_STATE.md`
6. `04_DECISION_LOG.md`
7. `05_BACKLOG_AND_ROADMAP.md`

Accepted exact decision:

`ACCEPT_SWING_PC_003_OPTION_A_PARK_PULLBACK_V1`

Option B and `SWING-PC-003A` are not authorized. No broader hypothesis-search task
was authorized by the PULLBACK decision.

The design was accepted with:

`ACCEPT_SWING_PC_005_DESIGN_V1`

The single implementation authorization was granted and consumed:

`AUTHORISE_SWING_PC_005A_ONE_BOUNDED_OFFLINE_SCREEN_V1`

## Alignment and preservation warning

The 2026-08-08 house-alignment work was merged through PR #14. The pre-alignment
local checkout and its uncommitted source/evidence state were checkpointed outside
the repository and preserved at
`/home/alexballard92/swingmachine-pre-alignment-20260808`.

Do not destructively reset or clean that preserved archive. The canonical checkout
at `/home/alexballard92/swingmachine` is the clean merged `main` starting point.

## Resume instructions

1. Confirm repository identity, branch, HEAD, staged state, dirty state, and
   untracked state.
2. Read the six current-decision files listed above.
3. Preserve PULLBACK as `PARKED_INCONCLUSIVE`.
4. Do not rerun `SWING-PC-005A` or open the frozen holdout without a new,
   separately accepted design and exact authority.
5. Do not rerun `SWING-PC-006` or repair its discovery result through thresholds,
   exclusions, or additional data.
6. Keep all profile, serious-qualification, paper, live, broker, API, runtime,
   acquisition, and deployment gates closed unless a later exact authorization
   changes a named gate.

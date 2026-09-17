# SWING-RF-003–005 implementation contract

Date: 7 September 2026. Repository: `Aballard92/swingmachine`, `main`, working
revision `23efab1` plus the existing uncommitted RF-001/002 work.

## Authority and scope

The sponsor explicitly requested continuation on all three objectives: build the
daily adapter/reference joins, make orders/fills executable, and freeze evaluation
criteria before historical strategy testing. This contract elaborates the already
accepted backlog. It does not narrow those objectives to a diagnostic-only task.

Edits and tests are authorised for isolated `src/swingmachine/research_*` modules,
the existing reset CLI, focused tests, explicit research configuration and schemas,
project-control documents, and new `reports/research_reset/SWING-RF-003_005/`
evidence. The narrow Databento audit/reader may be extended for the adapter without
altering its custody protections. Original data, prior evidence, other repositories,
secrets, runtime, databases and legacy strategy/broker code remain unchanged.
No package installation, provider/API acquisition, broker/account/runtime,
paper/live/deployment, GitHub, staging, commit, branch, push or PR action is included.

The initial worktree contains four modified project-control files and fifteen
untracked RF-001/002/XR-001 files. Preserve that work. No staged changes exist.

## Required implementation and acceptance

1. RF-003: stream declared, hashed input minutes; aggregate against an explicit
   session calendar; retain permanent identity through symbol changes; join
   historical security/population state, actions and earnings using availability
   timestamps. Produce raw daily bars, reference/price lineage, action payment
   facts and missingness diagnostics. Do not backfill missing prices or select on
   next-session presence. Fixture cases cover DST, shortened sessions, sparse bars,
   splits, distributions, future revisions, symbol changes and unresolved coverage.
   Qualify a non-holdout real sample only when an official decoder and the required
   references are available; report evidence limitations explicitly otherwise.
2. RF-004: replace the idealized open-contingent sizing path in the active research
   runner with an explicit executable order protocol. Freeze decisions before
   eligible fills; share reservations; model partial/expired/rejected orders,
   protective stops, conservative path ambiguity, gaps, costs, action entitlements
   and period-end accounting. Future prices/volume cannot change earlier orders.
   Minute fixtures and portfolio invariants must demonstrate the chosen semantics.
3. RF-005: freeze the family/cost trial ledger and numerical data/sample/risk/net
   performance gates before any historical outcomes; implement their calculation
   with calendar-block uncertainty and multiplicity controls. Specify benchmarks,
   exposure, cash, partition embargo and terminal-position treatment exactly.
   Record actual data exposure and the lack of usable independent dates where
   applicable. A missing final calendar remains an open acceptance item, not an
   invented validation period. No historical experiment runs before the freeze.

## Delivery evidence

Record source identity, changed/inspected files, commands and exact outcomes,
acceptance evidence, skipped checks, blockers/unknowns and final git state. Keep
the full three-objective goal active while any required component is incomplete.
Progress is judged against the accepted backlog, not just passing synthetic tests.

## Primary source conventions checked before implementation

- [Databento OHLCV schema](https://databento.com/docs/schemas-and-data-formats/ohlcv):
  timestamps mark interval starts; no-trade intervals have no record; daily vendor
  bars use UTC dates. Aggregate regular sessions explicitly and retain sparse-minute
  diagnostics instead of treating every absent minute as corrupt data.
- [FINRA order types](https://www.finra.org/investors/investing/investment-products/stocks/order-types)
  and [stop-order rule](https://www.finra.org/rules-guidance/rulebooks/finra-rules/5350):
  limit prices constrain fills but do not guarantee execution; a transaction-triggered
  stop becomes a market order. Bar-based replay needs explicit capacity/path
  assumptions and must allow gap losses beyond planned risk.

These references establish data/order semantics, not observed fill quality or
broker support. No provider or broker account access was used to read them.

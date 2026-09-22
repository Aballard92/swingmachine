# SWING-RF-003 — Daily adapter implementation checkpoint

Date: 7 September 2026. Status: adapter/reference mechanics implemented;
historical source qualification remains open. The full RF-003–005 goal is active.

## What is implemented

`research_daily.py` aggregates a timestamp-ordered minute stream against a retained
calendar with explicit open and closed days. Session bounds carry timezone-aware
timestamps and evidence identifiers. This handles DST and early closes through
inputs rather than a hard-coded clock or an inferred holiday list. Open is the
first observed regular-session trade-bar open; close is the last observed bar close.
High/low span the retained regular-session bars and volume is their sum. The close
boundary is exclusive. Missing minutes are counted, not price-filled.

`research_minute_source.py` reads bundle-relative JSONL or the existing narrow
XNAS.ITCH DBN-v1 minute layout. It checks every declared source date before opening
any source, rejects escaping paths, validates hashes, merges timestamp-ordered
shards, and retains source hashes and record indices. Hashing and reading use the
same open file, with a second integrity check after consumption. The DBN decoder
checks header scope, mappings, timestamps, record layout and invalid prices.

The CLI now exposes `build-daily`. Its output includes daily bars, reference states
even when prices are absent, per-bar lineage, action/payment facts, coverage/gap
diagnostics, a build receipt and a daily manifest consumable by RF-002 preflight.
All builds report zero strategy calculations. Historical `simulate` is explicitly
blocked pending source qualification and the RF-005 freeze.

## Retained reference tables

All tables are arrays in a single hashed JSON object. Refer to the dataclasses in
`src/swingmachine/research_daily.py` for the strict field contract. Unknown fields
or malformed types/timestamps fail typed construction.

| Table | Meaning and required timing |
| --- | --- |
| `calendar` | Every calendar date, including closed days; session date, opens/closes, known-at timestamp and evidence ID. Bounds must be known before the session. Include sufficient later calendar sessions to establish the maximum holding horizon. |
| `securities` | Permanent security ID, raw symbol/instrument ID, effective-from date, known-at timestamp, sector, listed/eligible flags and evidence ID. Latest effective state available at the decision close wins; a newer correction to an older state cannot override a newer effective state. |
| `population` | Permanent security ID, effective-from date, known-at timestamp, inclusion decision and evidence ID. Later universe revisions cannot retroactively change an earlier entry permission. |
| `action_coverage` | Security/date intervals for which the retained action feed is complete, with evidence IDs. This is source-quality evidence, not a predictive trading feature. Absence of an event implies no action only within this coverage. |
| `actions` | Event and permanent security IDs, ex date, known-at timestamp, split ratio, USD cash distribution per post-split share, payment date and evidence ID. Use the last event version available before the effective session open. Unavailable effective actions block accounting rather than generating a false no-action bar. |
| `earnings` | Versioned snapshots with known-at timestamp, covered interval and ordered event dates. The snapshot must cover the full holding horizon before no upcoming event can be asserted. Dates map to exposed trading sessions; an unknown horizon disables eligibility. |

The permanent security ID becomes `Bar.symbol`; use `SPY` for the canonical
benchmark identifier. Raw symbols and time-varying instrument IDs remain in lineage.
The engine receives **raw** daily OHLCV, with explicit split and distribution values.
Existing prefix feature logic adjusts history only for splits effective today;
cash distributions belong to portfolio accounting. No hindsight total-return
adjusted execution prices are generated.

Unknown action coverage or identity and missing expected listed-instrument prices
are blocking diagnostics. Unknown earnings, population or sector context retains
the raw price with eligibility disabled and an explicit context gap. A missing
later bar never changes an earlier bar's membership or eligibility. An unlisted
state is retained without inventing a delisting price or cash proceeds. Lifecycle
settlement for such positions remains an explicit accounting requirement.

## Reproduction and evidence

The reusable generator `tests/research_fixture_factory.py` creates an explicitly
artificial source bundle. Its calendar mirrors the earlier consecutive-day test
fixture; it is not an official exchange calendar. No generated fixture is market
evidence.

```bash
python3 scripts/run_research_reset.py build-daily \
  --manifest reports/research_reset/SWING-RF-003_005/mechanical_input/build_manifest.json \
  --output reports/research_reset/SWING-RF-003_005/new_daily_build

python3 scripts/run_research_reset.py preflight \
  --manifest reports/research_reset/SWING-RF-003_005/new_daily_build/daily_manifest.json \
  --plan config/research_reset_v1.json \
  --output reports/research_reset/SWING-RF-003_005/new_daily_admission
```

Use fresh output paths; evidence is never overwritten. The `--source-root` option
can point to the immutable raw root while manifest minute paths remain relative
to that root. Reference files remain inside the manifest bundle.

The delivered fixture has 3,120 minute rows, 1,560 daily rows, six permanent IDs
and 260 artificial input sessions. Preflight includes 200 warmup sessions and
60 evaluation sessions. No strategy calculation is needed to verify this chain.
Tests compare hand-calculated OHLCV and cover DST, shortened/closed sessions,
renames, future revisions, split/dividend/payment facts, unknown context, missing
instruments, duplicate records, source mutations, protected dates and deterministic
CLI replay.

## Trading212 adoption update

The September Trading212 checkout contains newer work than the August XR-001
review. [Adoption evidence](SWING-RF-003_TRADING212_ADOPTION.md) records the pinned
official calendar and three source captures now retained in SwingMachine, the
independent 1,258-session calendar verification, the adapted byte reader and the
bounded January 2019 conformance comparison. `build-calendar` supplies verified
calendar rows, including closed dates and calendar-only holding-horizon lookahead.
The other reference tables remain empty until independently supported.

## Remaining acceptance work

- No complete authoritative corporate-action, earnings or historical
  security/population bundle has yet been established for the real corpus.
  Official-source calendar metadata is available after the Trading212 adoption.
- An official Databento decoder was not found in the bounded local environment
  search. Trading212's tested reader has now been adapted and structurally compared
  on a fixed real source; this does not claim official vendor-decoder parity.
  No package was installed and no strategy conclusion is made from the adapter.
- Complete semantic source qualification, a non-holdout real sample and development
  interval admission remain open. The build deliberately leaves historical
  `supporting_evidence` empty and labels its receipt `NOT_QUALIFIED` rather than
  converting typed reference assertions into historical approval.
- The joins do not certify quotes, execution quality, delisting settlement,
  post-ex-date action corrections, or a sufficiently independent evaluation period.
  Those facts remain explicit qualifications for later use.

RF-003 is therefore **in progress**, with its mechanical implementation delivered.
RF-004 and RF-005 are not marked complete by this checkpoint. Exact commands,
results, source/file hashes and git state are recorded in the checkpoint receipt
under `reports/research_reset/SWING-RF-003_005/`.

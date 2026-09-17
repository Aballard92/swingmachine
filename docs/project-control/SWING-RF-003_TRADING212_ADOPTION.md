# SWING-RF-003 — Trading212 data-work adoption

Date: 7 September 2026. Status: bounded adoption complete; RF-003 qualification
and the full RF-003–005 goal remain in progress.

The sponsor explicitly requested review and adoption of the substantial Trading212
Databento work. This steers the active RF-003–005 goal; it does not replace that
goal or authorise either product's campaign/trading operations.

## Correct source identity

The earlier August XR-001 audit inspected `t212-ai-bot` at `8fe932e`. The relevant
September work is in `/home/alexballard92/Trading212/t212-ier-edge-003a`, branch
`codex/t212-databento-campaign-v3-001`, HEAD
`eddd6d892326c0a3b87290d18bf31c6518621429`. Its worktree is clean. Source-of-truth
snapshot 5 September records the newer custody, structural qualification, V3
source freeze and checkpoint-portability work. Local evidence is reviewed here;
no GitHub acceptance status is independently fetched or changed.

The previous statement that no qualified calendar had been established was too
broad: a pinned XNYS calendar, three official-source text captures and independent
calendar verification already exist. Correct that statement in current control
documents while preserving the earlier diagnostic evidence.

## Bounded adoption contract

Allowed: read relevant Trading212 tracked source/tests/control documents and local
calendar/custody/structural metadata; adapt the isolated byte reader and calendar
conversion in SwingMachine; add corresponding Swing tests/config and new evidence.
A fixed January 2019 non-holdout source may be used for decoder conformance.
Record exact upstream identities and local changes. No runtime imports from
Trading212, mutations in Trading212 or original data, package installation,
provider/account/broker/runtime/paper/live actions, strategy outcomes, protected
price/outcome reads, staging, commit, branch, push, PR or GitHub writes.

Acceptance: captured calendar bytes and semantic identity verify; independent
table/footnote reconstruction matches all frozen sessions; the Swing calendar
conversion handles DST/early closes and preserves publication/capture provenance;
byte-reader adaptation passes boundary/corruption tests and agrees with the prior
strict reader on the bounded sample; all impacted Swing regressions pass. Report
adopted components, rejected semantics, remaining inputs, exact checks and git state.

## Reuse decisions

| Component | Decision and justification |
| --- | --- |
| Pinned 2019–2023 XNYS calendar and official captures | Adopt source bytes with hashes; independently reparse holidays/early closes; convert the permitted research interval plus calendar-only holding-horizon lookahead. Retrospective capture is not an archived historical-version claim. |
| `databento_dbn_read.py` | Adapt the isolated Zstandard/framing mechanics locally, preserving stricter Swing metadata/date/price validation. No provider SDK or repo-to-repo runtime dependency. This is a tested project reader, not an official vendor decoder. |
| Fresh 242-object structural qualification | Reuse its scope, integrity defects and provenance as prior structural evidence; do not repeat the whole five-year raw audit or import admissions as swing eligibility. |
| V3 source constructibility and FB/META correction | Adopt the requirement that exact raw-source dependencies construct every selected input. Preserve the June 2022 `fb`→`meta` source-group correction in the catalogue; those price dates remain protected here. |
| Stable identity/segment contract | Reuse mapping evidence and BRK.B/FB_META handling where applicable; retain a Swing-owned permanent-ID adapter and availability semantics. Identity segments alone do not establish sector, earnings or an unbiased historical universe. |
| 20% discontinuity flags | Reuse as unresolved quality evidence. They are not authoritative split/dividend factors, action timing or payment facts. |
| Intraday session admission and five-year sparsity veto | Do not import. Opening 5/15-minute completeness and future-period sparsity differ from daily swing needs and can contaminate earlier eligibility. |
| Canonical lifecycle, outcome campaign and stopped checkpoints | Do not run or reuse as swing outcomes. Intraday force-flat, targetless policy and prior input fingerprints are not the swing execution/accounting contract. |
| Fee authority captures and frozen schedules | Retain as RF-004/005 reuse candidates for the covered dates; cost integration must avoid counting statutory fees twice within an all-in cost assumption. |

## Goal status

This adoption can close the calendar discovery gap and replace redundant low-level
reader work. It does not establish complete earnings, cash distributions, historical
sector/eligibility or independent evaluation data. RF-004 implementation and RF-005
numerical freeze remain part of the active goal.

## Implemented adoption

- `config/research/calendar_trading212_v1/` retains the exact calendar JSON and
  three hash-named official-page text captures. No Trading212 file was changed.
- `research_calendar.py` verifies both the byte hash and Trading212's distinct
  newline-terminated canonical hash, reparses the official tables/footnotes and
  independently expands the month grid. All **1,258 sessions, 45 closures and
  nine early closes** agree. Regular-session hours remain an explicit research
  assumption; holiday/early-close availability uses the day after the printed
  publication dates, not the 2026 capture date as an invented historical snapshot.
- `build-calendar` emits the six-table reference shape consumed by `build-daily`.
  Its calendar is populated and the remaining five tables are explicitly empty.
  The retained example spans 2 January 2019 to 30 November 2020, plus 20 later
  calendar sessions through 29 December 2020: **728 calendar-date rows**. No prices
  for that lookahead were accessed.
- `research_dbn.py` adapts upstream streaming decompression and byte framing.
  The adaptation fixes progress detection when input is consumed without output,
  drains pending decoded output, and retains unsupported record types for the
  strict caller to reject. `research_minute_source.py` now uses it, preserving
  hash checks before/after consumption and strict metadata/identity/OHLC checks.
- Encoded source-month checks run for all declared DBN sources before any path
  resolution. A protected month cannot be relabelled as 2019 in the manifest to
  bypass that boundary. This complements trusted custody hashes and header
  checks; filenames alone cannot prove arbitrary contents safe.

Run with a fresh output directory:

```bash
python3 scripts/run_research_reset.py build-calendar \
  --start 2019-01-02 --end 2020-11-30 \
  --output reports/research_reset/SWING-RF-003_005/new_calendar
```

## Evidence and limits

Trading212's retained structural summary (hash `0aa4a86d…`) records **59,532,877
bars and 128,426 definitions**, with 133 malformed OHLCV records, 42 unresolved
material discontinuities and 15 persistently sparse symbols. These are prior
Trading212 audit counts, not a new SwingMachine five-year raw scan. The summary's
`ADMIT_2020_2023_XNAS_PROXY` decision does not admit those prices here.

The V3 source freeze corrects the FB/META dependency: `fb` before 9 June 2022,
`meta` from that date. Its minimum source set increases from 79 to 86 objects,
adding seven META months for June–December 2022. The catalogue retains that
correction without accessing those protected raw prices. Previously stopped
campaign checkpoints are not portable merely because selected identities agree.

The new adoption suite adds **41 tests**. With 28 prior adapter/CLI tests and
64 prior source/reset/audit regressions, **133 focused tests pass**. They cover
retained-source tampering, calendar publication provenance, DST, early closes,
closed-day rows, horizon generation, tiny decompression/framing chunks,
concatenated compressed frames, corruption/truncation, unknown record types and
pre-I/O protected-month rejection. Ruff check/format and `git diff --check` pass.

The fixed January 2019 `core-101` sample comparison passes for **895,486 records**.
The adopted reader and prior zstd-CLI/fixed-record path produce identical complete
decompressed-byte digests and identical timestamp, instrument, mapped symbol,
OHLCV and lineage-field digests. Source SHA-256 remains
`bd30e8b0d695d255d8abf62326b4f7872bfd37ab106c7019564a053998907b6f`.

New evidence is retained in
`reports/research_reset/SWING-RF-003_005/trading212_adoption/`:

- `calendar_final/`: final calendar reference skeleton and source/code-bound receipt;
- `trading212_reuse_catalogue.json`: upstream file hashes, prior structural scope,
  V3 source correction, adoption decisions and remaining dependencies;
- `reader_conformance.py` / `reader_conformance.json`: fixed January 2019 streaming
  comparison against the prior zstd-CLI/fixed-record path; raw values are not
  retained in the receipt;
- `delivery_receipt.json`: exact checks, changed/inspected files, acceptance and
  final git state.

Official vendor-decoder parity remains unclaimed. Both comparison paths share
Swing's strict metadata interpretation, so agreement is narrower than an
independent vendor implementation. Historical strategy outcomes, the full corpus,
Trading212 campaign artifacts and protected price periods were not run/read.
No packages were installed, and no provider, broker, account or runtime action
was taken. No staging, commit, push, branch, PR or GitHub write was performed.

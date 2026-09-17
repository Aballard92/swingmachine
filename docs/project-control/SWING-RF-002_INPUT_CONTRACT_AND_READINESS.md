# SWING-RF-002 — Input contract and readiness delivery

Date: 7 September 2026. Repo: `Aballard92/swingmachine`.

## Outcome

The input-readiness task is delivered. A shared offline preflight now validates
the entire declared daily bundle and experiment configuration before any strategy
construction or outcome freeze. The real daily research inputs remain unqualified.
No historical strategy outcomes were calculated in this task.

The sponsor requested an elaborated backlog and immediate work. The active queue
is [SWING_RF_BACKLOG.md](SWING_RF_BACKLOG.md), which supplies RF-002's goal,
allowed surfaces, prohibitions, checks and acceptance criteria. Local code,
config, tests, documents and new diagnostic evidence are within that mandate.
No GitHub issue creation/comment, staging, commit, push, branch, PR, provider,
broker, runtime, package installation, paper/live or deployment action is included.

Repo identity was confirmed as `https://github.com/Aballard92/swingmachine.git`,
branch `main`, HEAD `23efab1`. The worktree already contained RF-001 changes and
an unrelated untracked XR-001 audit. They were preserved; the research CLI and
current-state/backlog/handoff documents were extended as intended. The XR-001
audit and legacy trading implementation were not edited.

## Source findings and next decisions

| Source | Reusable evidence | What it does not establish |
| --- | --- | --- |
| September Databento import: XNAS.ITCH minute bars and definitions, selected logical population of 102 instruments, 2019–2023 | Existing custody evidence; raw development-period bars for an offline adapter; instrument identity candidates | Consolidated prices/volume, a qualified daily calendar, full action/earnings ledger, historical eligibility or an independent evaluation period |
| Existing Databento intraday admission metadata | Structural dispositions, identity questions and prior partition exposure | Daily swing admission or permission to reuse protected outcomes |
| HF acquisition and static ticker catalogue | Provider schema and documented limitations | Historical point-in-time reference data; its own report is `FAIL_CLOSED_NOT_DECISION_GRADE` |
| HF tier1 candidate folders | File-name discovery of selected intraday fragments | Complete broad daily or reference coverage |

The prior full custody audit verified **92 unprotected objects / 379,902,473 bytes**
and deferred **150 objects**. That is inherited RF-001 evidence, not a fresh raw
file audit in RF-002. This task read zero new raw price files. Only qualification
declarations, catalogue field names and prior structural/custody evidence were
inspected; no prior strategy result was used to choose samples or rules.

The HF qualification explicitly records a static survivor universe, current-only
classification, adjusted prices without an independently retained action ledger,
filtered observations and absent quote/execution evidence. It therefore cannot
close the missing reference joins simply because its files are available.

The source catalogue records seven open requirements: daily/benchmark bundle,
official calendar, corporate actions, earnings knowledge, identity/population,
executable fills and unexposed evaluation dates. It covers the known local paths,
not an exhaustive search of all machines or remote accounts.

**Next work:** RF-003 defines and implements calendar/action/identity joins with
synthetic fixtures and the available unprotected raw inputs where admissible.
Real admission requires the reference evidence. RF-004's order-timing and portfolio
fixtures can proceed independently; unavailable references do not block that work.
RF-005 freezes the experiment and numerical decision gates before strategy results.
The surviving pre-holdout development interval is not a substitute for enough
unexposed market history to support qualification.

## Daily bundle contract, version 1

The manifest is a JSON object. It declares `source_class` as `SYNTHETIC_FIXTURE`
or `HISTORICAL`, inclusive `start`/`end`, an ordered unique `sessions` array,
`evaluation_start`, bundle-relative `bars_path` and lowercase `bars_sha256`.
The evaluation needs at least 200 earlier declared sessions. Synthetic calendars
may be artificial; historical calendars need official-calendar evidence.
`contract_version` is 1; omission retains compatibility with RF-001 fixtures.

The adjustment convention is
`raw_with_explicit_splits_and_dividend_accrual`. The three completeness declarations
are `corporate_actions_complete`, `event_calendar_complete` and
`session_calendar_complete`. They must be true to admit the structure. They are
assertions to substantiate through RF-003, not proof created by the preflight.

The bar file is a JSON array with one object per session/symbol. Required fields
are `session`, `symbol`, `open`, `high`, `low`, `close`, `volume`, `sector`,
`event_known` and `eligible`. Historical rows additionally require explicit
`split_ratio` and `dividend`, including 1 and 0 on no-action rows. Synthetic
fixtures retain those defaults. `sessions_to_earnings` is a nonnegative integer
or null. For eligible rows, null with `event_known: true` must mean the documented
earnings source covers the holding horizon and has no event in it; it cannot mean
unknown coverage. Eligible rows require known sector and event context.

Prices/actions must be finite and consistent; numeric booleans are rejected.
Duplicate session/symbol keys, undeclared dates, empty declared sessions and
missing evaluation SPY bars are rejected. Ineligible or missing symbols are not
automatically filled or carried forward. RF-003 must distinguish legitimate
listing coverage from missing bars. The simulator still stops on a missing held
instrument; this preflight does not certify full identity/lifecycle continuity.

Historical `supporting_evidence` maps these five roles to local references:
`session_calendar`, `corporate_actions`, `earnings_calendar`, `security_master`
and `population_selection`. Each reference contains:

```json
{
  "path": "evidence/role.json",
  "sha256": "<64 lowercase hexadecimal characters>",
  "coverage_start": "2019-01-02",
  "coverage_end": "2020-11-30",
  "scope": "Covered instruments, fields and limitations",
  "provenance": "Origin and reproducible derivation",
  "availability_policy": "When these facts were knowable to each decision"
}
```

Declared coverage must span warmup and evaluation without opening protected dates.
References must remain within the bundle, including after symlink resolution.
The preflight verifies scope fields, coverage and file hashes. **It does not
interpret evidence contents or certify their factual completeness.** The result
is always `historical_qualification: NOT_ESTABLISHED_BY_PREFLIGHT`; a structural
pass is not permission for discovery, promotion or trading. RF-003 and RF-005
retain their separate acceptance boundaries.

The trial plan must contain a nonempty unique family/cost matrix, valid explicit
parameters, the current protected windows and the offline/no-promotion purpose.
Malformed JSON objects and duplicate keys are rejected. Bars are hashed and parsed
from the same bytes; accepted input and code hashes are recorded in the freeze.

## Execution and failure behaviour

```bash
python3 scripts/run_research_reset.py preflight \
  --manifest config/research_source_example.json \
  --plan config/research_reset_v1.json \
  --output reports/research_reset/SWING-RF-002/example_new_run
```

The template deliberately returns exit 1: it records incomplete inputs instead of
fabricating a calendar, bars or evidence. Use a new output path for each run.
`readiness.json` contains stable issue codes, field locations and required actions.
On failure the CLI also writes `FAILED.json`; it creates neither a strategy object
nor an outcome freeze. The `simulate` command uses this same preflight. Successful
preflight-only runs produce no returns or trades.

Date guards run before reading the plan or referenced files. Invalid source or
plan declarations stop before the bar file. Row/benchmark checks inspect all rows
before simulation. Gaps are accumulated where safe; an unreadable manifest/date
boundary prevents dependent checks. It is not possible to infer every downstream
issue when upstream declarations are invalid.

## Verification and acceptance

All RF-002 acceptance criteria are met as a diagnostic delivery:

- Valid synthetic bundles pass; historical labels/URLs alone fail.
- Altered or escaping references, insufficient/protected evidence coverage,
  duplicates, non-finite rows, malformed context, missing sessions/benchmark,
  invalid trial matrices and protected dates stop before outcomes.
- Tests replace strategy construction with a forbidden stub for invalid late rows,
  proving the full input check happens before any strategy calculation.
- Deterministic nine-trial synthetic replay and accounting regression checks pass.
- Known local sources, gaps and explicit reuse limits are recorded without new
  raw-price reads or external actions.

Final focused verification: **64 tests passed in 28.61 seconds** (29 new
preflight tests and 35 inherited reset/audit/CLI checks). Ruff passed.
Exact commands, results, inspected/changed files and final git status are in
`reports/research_reset/SWING-RF-002/delivery_receipt.json`. The focused pytest
suite, Ruff and whitespace checks were used. Full application/runtime/broker tests
were skipped because no legacy application behaviour changed; no dependency
installation or unrelated environment repair was necessary. An initial test
collection error from the helper import and initial lint formatting failures were
corrected before the final checks.

Evidence bundle (local, ignored by Git):

- `source_catalogue.json`: inspected metadata hashes, source limits and gaps.
- `synthetic_preflight/readiness.json`: valid fixture, zero strategy calculations.
- `blocked_template/readiness.json`: nine specific template blockers, no price read.
- `delivery_receipt.json`: exact final checks and change inventory.

No candidate is selected. The open-contingent execution assumption, incomplete
daily/reference inputs and unestablished independent period remain material
blockers to historical strategy conclusions. No profitability or readiness claim
is made by this delivery.

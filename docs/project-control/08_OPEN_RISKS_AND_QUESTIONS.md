# 08 Open Risks and Questions - swingmachine

## Technical risks

- Research/runtime parity can regress if feature, scanner, lifecycle, or reporting paths diverge.
- Large modules such as `replay.py`, `runtime.py`, `contracts.py`, and `feature_outcomes.py` are complex and may be hard to modify safely without focused tests.
- Full scanner/lifecycle runs can be slow, increasing risk of partial evidence or long-running sessions.
- Generated report sprawl makes it easy to cite superseded evidence.
- Deprecated v1 spec/config files remain in repo and could confuse future work.

## Product risks

- The current system is mechanically stronger but has not proven a market edge.
- PULLBACK is `PARKED_INCONCLUSIVE`; it must not silently re-enter candidate or
  profile work without genuinely new independent evidence and separate authority.
- PULLBACK has a positive traded subset but negative all-accepted evidence and too few trades.
- TIGHT_BASE appears damaging and must not remain hidden in future candidates.
- Building another profile before the design gate passes would repeat the earlier ad hoc iteration risk.
- `SWING-PC-005A` stopped at Gate 0; treating that packet as an economic failure
  or rerunning it after an ad hoc repair would invalidate the preregistration.
- `SWING-PC-006` then tested the same families under accepted limitations and both
  failed discovery. H1's positive mean must not obscure its negative median and
  61.76% symbol concentration; H2 was negative and 79.31% concentrated.
- Uploading too much stale documentation into ChatGPT Project could confuse product direction.

## Operational risks

- Older paper/serious-run docs can be misread as current permission to execute.
- Paper trading remains blocked despite earlier engineering readiness language.
- Any broker/paper/live command must require explicit human approval.
- `.env` strategy behavior would undermine reproducibility and should remain prohibited.
- Absolute local paths in config may not be portable.

## Local Sync / Checkout Warning

- The pre-alignment checkout is preserved at
  `/home/alexballard92/swingmachine-pre-alignment-20260808`, with a separately
  verified checkpoint under `/home/alexballard92/swingmachine-checkpoints/`.
- The canonical checkout is `/home/alexballard92/swingmachine` on clean `main`.
- Do not destructively clean or reset the preserved archive. Retain it until its
  local evidence has been separately dispositioned and deletion is explicitly
  approved.

## Data/API risks

- Broad Hugging Face data does not currently support like-for-like validation against the broad Alpaca window.
- Alpaca and Hugging Face provider drift remains important context.
- Provider-positive accepted edge is not confirmed across both providers.
- Corporate action/adjustment assumptions may depend on upstream providers.
- Trading212 source DBs are local dependencies and may not exist in other environments.
- The MPS historical panel remains partial: BLOX classification is unresolved;
  34,267 common-stock rows lack point-in-time sector/reference evidence; 39,782
  rows lack shares evidence; and HLXB/STLE are fully shares-masked.
- These gaps are accepted fail closed for research. They must not be silently
  imputed or treated as qualification-grade coverage.
- The accepted broader screen additionally lacks a frozen SPY benchmark, dividend
  payment dates for all 974 dividend events, and delisting outcomes for 81
  terminal rows. These stopped `SWING-PC-005A` before strategy outcomes.
- Indefinite acquisition is stopped. A future acquisition task must meet the exact
  bounded exception in `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`.
- Stooq and Yahoo transport failures are recorded. Because the absolute-only
  screen still failed discovery, another benchmark source is not
  decision-critical and must not be pursued in this lane.

## Testing gaps

- Current tests are broad, but paper/live behavior is intentionally not exercised as real execution.
- CI's `mypy_core.ini` gate is intentionally bounded to seven typed-core modules.
  A cache-cold diagnostic with recursive imported-module reporting enabled found
  237 strict typing errors across 21 legacy modules; this debt is not a CI pass
  claim and should be reduced through separately bounded refactors.
- Full-suite runtime may be slow; focused tests are safer for small tasks.
- Need clearer current testing strategy doc for which gates to run by task type.
- Need active summary of latest passing checks, rather than relying on long implementation log.
- The PULLBACK lifecycle diagnostic now has focused repeatable tests; broader
  integration coverage remains a later task only if the lane continues.
- `SWING-PC-005A` source-mask and gate-lock tests pass. Common-exit, trade-count,
  and outcome tests were correctly not implemented because Gate 0 stopped before
  the backtest path.
- `SWING-PC-006` adds tested common-lifecycle behavior, non-spendable ex-date
  dividend accrual, terminal last-close handling, and total-loss sensitivity.
  The focused combined slice passed 28 tests.

## Open questions needing human decision

- What minimum sample size is required before any candidate can be considered paper-reviewable?
- Should TIGHT_BASE be permanently retired or allowed to re-enter through explicit redesign?
- What decision-critical future requirement, if any, would justify reopening
  provider acquisition under the documented stop condition?
- How much source code should be uploaded to ChatGPT Project, if any?
- Should ChatGPT Project maintain the active backlog directly, or should Codex generate snapshots on demand?
- What is the sponsor's threshold for benchmark-relative underperformance versus absolute profitability?

## Current risk posture

Risk posture is controlled if work remains documentation, offline research, and bounded diagnostics.

The current data posture is also controlled only while unresolved rows remain
masked/unknown and the acquisition stop condition is observed.

Risk posture becomes unacceptable if Codex:

- Starts paper/live execution.
- Builds a revised profile without design-gate approval.
- Uses stale paper runbooks as current authority.
- Ignores provider/data limitations.
- Makes strategy changes outside explicit config/profile review.

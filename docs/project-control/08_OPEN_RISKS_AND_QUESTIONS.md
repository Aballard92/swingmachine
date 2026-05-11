# 08 Open Risks and Questions - swingmachine

## Technical risks

- Research/runtime parity can regress if feature, scanner, lifecycle, or reporting paths diverge.
- Large modules such as `replay.py`, `runtime.py`, `contracts.py`, and `feature_outcomes.py` are complex and may be hard to modify safely without focused tests.
- Full scanner/lifecycle runs can be slow, increasing risk of partial evidence or long-running sessions.
- Generated report sprawl makes it easy to cite superseded evidence.
- Deprecated v1 spec/config files remain in repo and could confuse future work.

## Product risks

- The current system is mechanically stronger but has not proven a market edge.
- PULLBACK has a positive traded subset but negative all-accepted evidence and too few trades.
- TIGHT_BASE appears damaging and must not remain hidden in future candidates.
- Building another profile before the design gate passes would repeat the earlier ad hoc iteration risk.
- Uploading too much stale documentation into ChatGPT Project could confuse product direction.

## Operational risks

- Older paper/serious-run docs can be misread as current permission to execute.
- Paper trading remains blocked despite earlier engineering readiness language.
- Any broker/paper/live command must require explicit human approval.
- `.env` strategy behavior would undermine reproducibility and should remain prohibited.
- Absolute local paths in config may not be portable.

## Local Sync / Checkout Warning

- GitHub `main` has the accepted squash-merged governance/setup baseline from PR #1.
- Local `main` may still contain the pre-squash commits `5082e91`, `df27534`, and `e560a62`.
- `README.md` and broad untracked baseline files may remain local and must be preserved until separately reviewed.
- Do not run `reset`, `clean`, `pull`, `checkout`/`switch`, or sync commands unless a specific bounded sync task authorizes them.
- Treat local sync, README cleanup, dirty-worktree cleanup, and untracked baseline-file decisions as separate future tasks.

## Data/API risks

- Broad Hugging Face data does not currently support like-for-like validation against the broad Alpaca window.
- Alpaca and Hugging Face provider drift remains important context.
- Provider-positive accepted edge is not confirmed across both providers.
- Corporate action/adjustment assumptions may depend on upstream providers.
- Trading212 source DBs are local dependencies and may not exist in other environments.

## Testing gaps

- Current tests are broad, but paper/live behavior is intentionally not exercised as real execution.
- Full-suite runtime may be slow; focused tests are safer for small tasks.
- Need clearer current testing strategy doc for which gates to run by task type.
- Need active summary of latest passing checks, rather than relying on long implementation log.
- Need repeatable deeper PULLBACK replay tests if that research lane proceeds.

## Open questions needing human decision

- What minimum sample size is required before any candidate can be considered paper-reviewable?
- Should PULLBACK fill/lifecycle replay be the next research lane, or should ChatGPT design broader alternatives first?
- Should TIGHT_BASE be permanently retired or allowed to re-enter through explicit redesign?
- Should future provider validation require Hugging Face, another provider, or accepted Alpaca-only limitations?
- How much source code should be uploaded to ChatGPT Project, if any?
- Should ChatGPT Project maintain the active backlog directly, or should Codex generate snapshots on demand?
- What is the sponsor's threshold for benchmark-relative underperformance versus absolute profitability?

## Current risk posture

Risk posture is controlled if work remains documentation, offline research, and bounded diagnostics.

Risk posture becomes unacceptable if Codex:

- Starts paper/live execution.
- Builds a revised profile without design-gate approval.
- Uses stale paper runbooks as current authority.
- Ignores provider/data limitations.
- Makes strategy changes outside explicit config/profile review.

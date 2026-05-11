# Review Scenario Examples

These examples describe the local paper/shadow review scenarios exercised by
`tests/test_reporting.py`. They are not live trading scenarios and do not depend
on any broker-specific integration.

The fixture seeder in `tests/fixtures/review_scenarios.py` creates three
multi-symbol, multi-session histories through the existing runtime, shadow
comparison, paper broker, audit snapshot, run history, and review-report paths.

## PASS: all aligned

- Symbols: `AAA`, `BBB`, `CCC`
- Sessions: three consecutive signal sessions in April 2026
- Shadow outcome: all three proposals hypothetically fill
- Paper outcome: all three paper broker orders are marked filled
- Expected review status: `PASS`

## WARN: paper/shadow divergence

- Symbols: `AAA`, `BBB`, `CCC`
- Sessions: three consecutive signal sessions in April 2026
- Shadow outcome: all three proposals hypothetically fill
- Paper outcome: two paper broker orders are marked filled; one remains open
- Expected review status: `WARN`
- Expected warning categories:
  - `paper_shadow_alignment_rate`
  - `paper_shadow_divergent_count`

## FAIL: missing next-session market data

- Symbols: `AAA`, `BBB`, `CCC`
- Sessions: three consecutive signal sessions in April 2026
- Shadow outcome: two proposals hypothetically fill; one proposal has no matching
  next-session market-data row
- Paper outcome: two paper broker orders are marked filled; one remains open
- Expected review status: `FAIL`
- Expected failing category:
  - `shadow_missing_market_data_count`

## Why These Exist

The review report now has explicit thresholds and status checks. These scenarios
keep `PASS`, `WARN`, and `FAIL` behavior testable before any external historical
dataset or ingestion layer is wired into the build.

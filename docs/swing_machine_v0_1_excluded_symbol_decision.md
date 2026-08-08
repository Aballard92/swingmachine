# Swing Machine v0.1 Excluded Symbol Decision

Date: 2026-05-05

## Decision

Keep `ORCL`, `CRM`, `BAC`, and `CVX` excluded from the `swing_machine_v0_1` selected-period qualification panel.

This exclusion is data-driven. It is not a strategy or performance decision.

## Evidence

Both Trading212 local research databases were checked with read-only indexed probes for `1d` and `1m` bars:

- `/home/alexballard92/Trading212/t212-ai-bot/data/research_testing/sources/research_alpaca_local.db`
- `/home/alexballard92/Trading212/t212-ai-bot/data/research_testing/sources/research_hf_local.db`

Result:

| Symbol | Alpaca `1d` | Alpaca `1m` | Hugging Face `1d` | Hugging Face `1m` |
| --- | --- | --- | --- | --- |
| ORCL | absent | absent | absent | absent |
| CRM | absent | absent | absent | absent |
| BAC | absent | absent | absent | absent |
| CVX | absent | absent | absent | absent |

The selected-period coverage failure was therefore caused by complete source absence, not by a narrow date-window issue.

## Qualification panel impact

The v0.1 data-complete selected-period panel remains:

`SPY`, `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `TSLA`, `AMD`, `NFLX`, `AVGO`, `QCOM`, `INTC`, `JPM`, `XOM`, `QQQ`.

## Follow-up condition

The excluded symbols may be reconsidered only if a new explicit data source is added, preflighted, exported, manifested, and validated under the same data-contract and provenance controls.

Do not silently reintroduce these symbols through `.env`, implicit universe changes, or partial provider fallbacks.

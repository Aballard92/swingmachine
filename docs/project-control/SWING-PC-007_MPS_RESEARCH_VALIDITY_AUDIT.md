# SWING-PC-007 MPS Research Validity Recovery Audit

Status: `COMPLETE_INVALID_FOR_STRATEGY_SELECTION`

Execution base: `d399d96f5813f5a184fbb4854fb537a2010328a4`

Issue: `#17`

## Executive decision

`SWING-PC-006` evidence verdict: `INVALID_FOR_STRATEGY_SELECTION`

H1/H2 evidence status: `NOT_VALIDLY_TESTED`

The July report remains authentic evidence of what the preserved machinery
reported for its special cohort. It is not valid evidence for selecting or
rejecting a general US momentum, trend, or breakout family. The discovery
population was expressly built for machinery validation from recently delisted
securities missing from a prior price archive, not representative strategy
discovery. In addition, deterministic reproductions confirm that carried
positions can ignore an intraday stop. A synthetic boundary case also confirms
that open positions at a partition end affect equity-series metrics without
entering completed-trade metrics; that is a population/reconciliation-policy gap,
not evidence of an arithmetic accounting error or proof that the July run was
materially affected.

The price-series verdict is inconclusive. The implementation uses raw OHLC for
technical features even though the historical authority requires adjusted OHLCV
and, more specifically, total-return-adjusted feature history. A later mechanical
design reference instead specifies split-adjusted chart features. The implementation
therefore cannot be called contract-aligned, but the conflicting documented
conventions do not establish which adjusted convention should govern a future
repair. Provenance binds the report,
data, config, temporal plan, run identity, generation time, holdout status, and
network/provider status, but omits the Git commit, dirty state, and code/build
identity. The result is therefore bindable as a preserved run artifact but not to
an exact source revision.

No impact magnitude or direction is inferred. Gate 2 and the frozen holdout remain
unopened. No strategy is promoted.

## Scope and method

This was a read-only validity audit of current source/tests/config and exact
restored historical evidence. Two deterministic reproductions were created only
under `/tmp`; source, tests, config, data, reports, runtime state, and Trading212
were not modified.

Evidence authorities, in order:

1. Current `main` at the execution base above.
2. Exact `SWING-PC-006` JSON/Markdown restored under the preserved pre-alignment
   repository.
3. Hash-matched research inputs restored under
   `/home/alexballard92/.local/share/swingmachine-data-staging/`.
4. The accepted evidence hash index and current project-control record.

## Finding summary

| Finding ID | Audit area | Status | Severity | Evidence | Effect | Impact direction | Fix authorised |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POP-001` | population | `CONFIRMED` | `CRITICAL` | `build_mps_tiingo_queue.py:63-130`; queue SHA-256 `ff4bec9d57e2d1fbd19cdc0d32c9d4ded00e4bf30c343ff0adbdcdd2901caee0`; feature summary; report discovery block | Discovery ranks and outcomes describe a specially selected delisted/missing-price cohort, not a representative US strategy population. | `UNKNOWN` | `NO` |
| `STOP-001` | stop | `CONFIRMED` | `CRITICAL` | `mps_backtest.py:217-230`; `mps_execution.py:42-57`; Appendix A reproduction SHA-256 `6fea9c0282e63d942fb0740f057b301c3a23f2f8c36e2ad5fac4847e0d16978b` | Valid carried-position `STOP_INTRADAY` fills are ignored; holding period, exits, equity, capital availability, risk and all downstream metrics may be affected. | `UNKNOWN` | `NO` |
| `PRICE-001` | price series | `INCONCLUSIVE` | `HIGH` | `SWING-PC-005` sections 3-4; `SWING-PC-006` fixed input contract; design spec v2 sections 2.2-2.3; feature-ready builder; `mps_features.py:31-111,183-208` | Raw technical-feature inputs are inconsistent with the historical adjusted-feature authority. The exact intended adjusted convention is unresolved between the governing research contract and later mechanical reference. | `UNKNOWN` | `NO` |
| `PART-001` | partition | `INCONCLUSIVE` | `HIGH` | `SWING-PC-006` section 6; `mps_backtest.py:455-500`; `mps_limitation_screen.py:140-247`; Appendix A reproduction | A boundary-open position enters daily account-equity returns but not completed-trade metrics. Different populations are allowed, but terminal-position/censor/reconciliation policy is inadequate for gate interpretation. July occurrence and magnitude are unproven. | `UNKNOWN` | `NO` |
| `PROV-001` | provenance | `CONFIRMED` | `MEDIUM` | Exact report and evidence-index hashes; report `source_preflight`; runner metadata | Run artifact and inputs are bindable, but exact code/dirty/build identity is not. | `UNKNOWN` | `NO` |

## Audit 1 — discovery-population suitability

### Lineage

The source lineage is:

`source lifecycle inventory -> Tiingo queue -> raw/provider-adjusted Tiingo panel -> shares/classification/reference joins -> feature-ready panel -> MPS features -> eligible universe -> within-cohort momentum ranks -> SWING-PC-006 discovery report`

The queue builder requires a delisting date, eligible exchange, Stock asset type,
absence from the prior price archive, a delisting date in the target interval,
and a unique Tiingo ticker/end-date lifecycle match. Accepted rows receive
`DELISTED_MISSING_PRICE_EXACT_TICKER_AND_END_DATE`. The candidates are ordered by
`most_recent_delisting_then_ticker_descending`, limited to 500, and the queue
explicitly records `strategy_selection_use: false`.

This uses future lifecycle/delisting information to construct the cohort. It is a
delisted-security/missing-archive sample, not a point-in-time broad US population.
No separate representative population is merged before feature construction or
ranking.

The full feature panel contains 208,240 rows across 82 securities. Only 23,951
rows across 25 securities ever pass all eligibility gates. Inside the discovery
partition, the panel has 62,166 rows across 39 available securities but only
3,861 eligible rows across eight securities: BERY, BLUE, JWN, MRC, PDCO, SPR,
VRNT, and WBA. Momentum percentiles are calculated only among eligible rows in
this cohort on each session (`mps_features.py:163-179`). The report confirms eight
eligible discovery securities; H1 completed trades in seven and H2 in three.

### Suitability classification

| Use | Classification | Reason |
| --- | --- | --- |
| Machinery validation | `SUITABLE` | This is the panel's explicit purpose and it exercises lifecycle/data machinery. |
| Delisted-security stress testing | `SUITABLE_WITH_LIMITATIONS` | The selection intentionally emphasizes delisted securities, although unresolved outcome/reference limitations remain. |
| H1/H2 cohort diagnostic | `POPULATION_SUITABLE_ONLY` | It can describe these masks within this cohort, but the confirmed engine defects invalidate the resulting performance evidence. |
| General US swing-strategy discovery | `UNSUITABLE` | The cohort is future-selected, narrow, and non-representative. |
| Programme-level momentum/trend/breakout family rejection | `UNSUITABLE` | Within-cohort ranks and outcomes cannot support general family rejection. |

Conclusion: `POP-001 CONFIRMED`.

## Audit 2 — carried-position intraday stop

`simulate_sell_stop` correctly returns:

- `STOP_GAP` when open is at or below the stop;
- `STOP_INTRADAY` when open is above the stop and low reaches the stop; and
- `STOP_NOT_REACHED` otherwise.

For positions carried into a session, `run_mps_backtest` calls this function at
lines 221-227 but closes the position only when `reason_code == "STOP_GAP"` at
lines 228-230. A valid `STOP_INTRADAY` result is discarded. A later loop processes
all stop types only for positions whose `entry_session` equals the current session
(`mps_backtest.py:391-404`). Existing tests cover same-session intraday stops but
not the carried-position case.

Deterministic reproduction:

- prior-session position with active stop `95.0`;
- next open `100.0`, low `94.0`, with no competing exit;
- direct simulator result: filled `true`, `STOP_INTRADAY`, reference `95.0`;
- actual backtest result: zero completed trades, zero exit events, final position
  count one.

Required conclusion: `CONFIRMED_DEFECT`.

Potentially affected outputs include exit reason/date/price, completed trades,
realised R, trade returns, holding period, MFE/MAE, cash, exposure, equity,
drawdown, Sharpe, fill capacity, later entries, concentration, and gate outcomes.
Impact magnitude and direction are unknown without a separately authorised repair
and rerun.

## Audit 3 — price-series contract

The Tiingo panel builder stores source `open/high/low/close/volume` in
`tradable_prices.parquet` and provider `adjOpen/adjHigh/adjLow/adjClose/adjVolume`
in a separate provider-adjusted panel. The feature-ready builder carries the raw
fields forward unchanged and constructs a causal total-return index from raw
close, cash distributions, and split factors. Its provider-adjusted close is used
as a cross-check, not substituted into execution/chart OHLC.

| Calculation | Actual series |
| --- | --- |
| SMA20/50/200 and SMA200 slope | Raw close |
| ATR | Raw high, low, and prior raw close |
| Peak/recent high | Raw high |
| Pullback depth | Raw high, raw close, raw ATR |
| SMA touch | Raw low versus raw-close SMA20 |
| Trend qualification | Raw close and raw-close SMAs |
| Swing low and structure stop | Raw low and raw ATR |
| Momentum | Causal total-return-adjusted close |
| Entry, stop, and mark-to-market | Raw OHLC |
| Market regime SMA | Raw benchmark close |
| Market regime volatility | Total-return-adjusted benchmark close |

That table is an observed implementation trace, not proof of contract alignment.
`SWING-PC-005` section 3 says the fixed panel exposes adjusted OHLCV, and section 4
requires total-return-adjusted history for features and benchmark outcomes.
`SWING-PC-006` preserves that fixed panel and family contract and grants no exception
for split-discontinuous technical lookbacks. The implementation's raw SMA, ATR,
high, low, touch, and structure-stop inputs therefore conflict with the historical
research authority.

The later design specification v2 distinguishes split-adjusted chart/features,
raw execution prices, and total-return ranking. It is useful mechanical evidence,
but it does not silently replace the earlier MPS research contract. It also does
not support the current raw technical-feature implementation. The two documents
leave the precise intended adjusted feature convention—total-return-adjusted or
split-adjusted—unresolved for any future repair.

The feature summary's passing provider-close return cross-check (208,158 comparable
returns, no unexplained mismatches, and two rounding-explained SCPH mismatches)
validates the constructed total-return close returns only. It does not validate
split continuity of the raw technical OHLC lookbacks.

Required conclusion: `INCONCLUSIVE` — a documented raw-versus-adjusted policy
mismatch is present, but the exact governing adjusted convention requires Product
Owner resolution. No impact magnitude or direction is inferred.

## Audit 4 — partition-end open-position accounting

Each `run_stage` call slices one partition and starts a new backtest ledger. The
backtest has no partition-final liquidation. On the final session it marks open
positions to raw close and writes their unrealised value into the equity curve.
It returns only completed trades; open positions and pending exits are not carried
to the next independently reset partition.

`aggregate_metrics` derives compounded return, Sharpe, and drawdown from the
equity curve, while completed trades, net trade PnL, R, win rate, concentration,
and leave-one-out metrics use only `result.trades`.

`SWING-PC-006` section 6 explicitly defines trade return from completed trade
economics and daily portfolio return from consecutive reported account equity.
Those measures are allowed to use different populations. The issue is therefore
not that the arithmetic must match. It is that no adequate terminal-position,
censoring, or reconciliation policy explains how boundary-open exposure is treated
when trade-count, robustness, and account-equity gates are interpreted together.

Deterministic reproduction of current code:

- a position enters on the partition's final session and remains open;
- final position count: one;
- completed trade count: zero;
- initial cash: `100000.0`;
- final marked equity: `100287.1`;
- final equity minus initial cash: `287.1`;
- mark-to-fill unrealised P&L: `287.1` (entry fill `100.05`, final close `105.0`,
  quantity 58);
- raw-reference price move: `290.0` (reference `100.0`, before entry cost/slippage);
- trade metrics: zero completed trades and net PnL `0`, with R,
  concentration, and leave-one-security-out all null.

Required conclusion: `INCONCLUSIVE`. The synthetic behavior and missing
reconciliation policy are confirmed, but they do not establish an arithmetic
accounting defect, do not prove that a boundary-open position occurred in the July
executable, and do not establish occurrence count or economic magnitude in the
preserved July result. The historical executable is not source-identifiable under
`PROV-001`.

The gap can impair interpretation of return/drawdown/Sharpe versus completed-trade
and robustness gates. No forced partition liquidation is prescribed: an invented
boundary fill would be a separate economic assumption. Impact direction is unknown.

## Audit 5 — report/code/config/data provenance

The exact preserved report identities match the accepted evidence index:

- JSON SHA-256: `e1ae5e0293d2ab50e630cfb9dc139fdfc61affdf6c7b470d13e2ca703f43a21a`;
- Markdown SHA-256: `751b1a9a08cd05ecb3f8d2a2ccda434070cf2223eb8b62774845dd60c4fdceca`.

| Provenance field | Status |
| --- | --- |
| Run/task identity | Bound: `SWING-PC-006` and timestamped output path |
| Generation timestamp | Bound: `2026-07-29T20:24:02.530956+00:00` |
| Config file and parsed config | Bound by SHA-256 and parsed hash |
| Computed features, feature input, summary, corporate actions | Bound by expected/actual SHA-256 equality |
| Temporal partitions/date plan | Bound by accepted date-plan hash and exact-boundary check |
| Holdout status | Bound: `holdout_opened: false` |
| Network/provider status | Bound: Stooq verification HTML hash and Yahoo HTTP 429/no file |
| Report identity | Bound by accepted evidence-index hashes |
| Git commit | Missing |
| Dirty/staged/untracked state | Missing |
| Source-code/build identity | Missing |

The report is conclusively the accepted July artifact and binds its declared
inputs. Its fields align with the preserved runner. Because no code revision or
dirty-state identity is embedded, the exact executable source cannot be proven
cryptographically from the report alone.

Required conclusion: `PROVENANCE_INCOMPLETE_BUT_RESULT_BINDABLE`.

## Applicability to the September RF execution route

The historical MPS path is source-traceable as
`mps_limitation_screen.py -> run_mps_backtest`. The active September RF path is
separate: `scripts/run_research_reset.py::simulate` calls
`research_replay.load_replay_inputs` and `research_replay.run_replay`, which
constructs `research_execution.ExecutionSimulator` instances. Repository search
finds no import or call of `run_mps_backtest` in that active route. The earlier
daily simulator is explicitly retained only as `simulate-daily-fixture`, and it
uses `research_reset.ResearchSimulator`, not the MPS backtest.

Accordingly, `STOP-001` and `PART-001` are demonstrated against the current
preserved MPS implementation and are legacy-MPS findings. This audit does not show
that the active RF minute-execution route consumes either defective MPS function.
It also does not validate the July executable because that run's exact source
revision remains unbound. Repairing MPS would not repair or unblock RF-004, validate
the July evidence, or authorise any RF execution.

## Product consequences

| Proposed action | Decision | Reason |
| --- | --- | --- |
| Programme-level momentum-family rejection from `SWING-PC-006` | `REJECT` | Population is unsuitable and mechanics are invalid. |
| Open Gate 2 | `REJECT` | Discovery evidence is invalid for strategy selection. |
| Open frozen holdout | `REJECT` | Discovery did not validly pass and holdout remains protected. |
| Tune H1/H2 | `REJECT` | Tuning against invalid evidence would compound bias. |
| Select revised baseline | `REJECT` | No valid selection evidence exists. |
| Acquire new data | `REJECT` | This audit grants no acquisition and does not establish the five-part exception. |
| Paper trading | `REJECT` | Existing research and safety gates remain closed. |
| Live trading | `REJECT` | Live trading remains prohibited. |

## Appendix A — self-contained current-code reproductions

These two cases were executed against source revision
`d2d2188bbbb5c426b1f59f9b8c36a909e6e6246a`, with the repository's default
`config/mps_v1.yml`, `B1_MOMENTUM_TREND`, and
`common_lifecycle_policy=True`. The script was retained at
`/tmp/swing_pc_007_reproductions.py`; that path is convenience only. The exact
bytes needed to repeat it are below (SHA-256
`6fea9c0282e63d942fb0740f057b301c3a23f2f8c36e2ad5fac4847e0d16978b`).
This proves repeatability against that current revision; it does not identify or
reproduce the unknown July executable.

Invocation:

```text
PYTHONPATH=src .venv/bin/python /tmp/swing_pc_007_reproductions.py
```

Exact script, including literal inputs and expected assertions:

```python
from __future__ import annotations

import json

import pandas as pd

from swingmachine.mps_backtest import run_mps_backtest
from swingmachine.mps_config import load_mps_config
from swingmachine.mps_contracts import MpsVariant
from swingmachine.mps_execution import simulate_sell_stop
from swingmachine.mps_limitation_screen import aggregate_metrics


def panel(rows: list[dict[str, float]]) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-02", periods=len(rows))
    defaults = {
        "security_id": "SEC-AAA",
        "ticker": "AAA",
        "momentum_rank": 0.95,
        "sma50": 90.0,
        "atr20": 2.0,
        "eligible_universe": True,
        "trend_qualified": True,
        "pullback_depth_atr": 1.0,
        "recent_sma20_touch": True,
        "close_above_prior_high": True,
        "close_location_value": 0.8,
        "prior_high20": 99.0,
        "adv20_dollars": 100_000_000.0,
        "structure_stop": 95.0,
        "sector": "Technology",
    }
    return pd.DataFrame(
        [defaults | {"session_date": day} | row for day, row in zip(dates, rows)]
    )


def regime(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {"session_date": frame["session_date"], "regime_multiplier": [1.0] * len(frame)}
    )


config = load_mps_config()

carried = panel(
    [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        {"open": 100.0, "high": 101.0, "low": 94.0, "close": 100.0},
    ]
)
direct_stop = simulate_sell_stop(100.0, 94.0, 95.0, config)
carried_result = run_mps_backtest(
    carried,
    regime(carried),
    config,
    MpsVariant.B1_MOMENTUM_TREND,
    data_version_hash="swing-pc-007-carried-stop",
    common_lifecycle_policy=True,
)

partition = panel(
    [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        {"open": 100.0, "high": 106.0, "low": 99.0, "close": 105.0},
    ]
)
partition_result = run_mps_backtest(
    partition,
    regime(partition),
    config,
    MpsVariant.B1_MOMENTUM_TREND,
    data_version_hash="swing-pc-007-partition-end",
    common_lifecycle_policy=True,
)
partition_metrics = aggregate_metrics((partition_result,), "LAST_CLOSE")
partition_entry = next(
    event for event in partition_result.audit_events if event["event"] == "ENTRY_FILLED"
)
initial_cash = 100_000.0
final_close = 105.0
mark_to_fill_unrealised_pnl = (
    final_close - partition_entry["fill_price"]
) * partition_entry["quantity"]
raw_reference_move = (
    final_close - partition_entry["reference_price"]
) * partition_entry["quantity"]

assert direct_stop.filled is True
assert direct_stop.reason_code == "STOP_INTRADAY"
assert direct_stop.reference_price == 95.0
assert len(carried_result.trades) == 0
assert carried_result.equity_curve[-1].position_count == 1
assert not [
    event for event in carried_result.audit_events if event["event"] == "EXIT_FILLED"
]
assert partition_result.equity_curve[-1].position_count == 1
assert len(partition_result.trades) == 0
assert partition_metrics["completed_trades"] == 0
assert partition_metrics["net_pnl"] == 0
assert partition_metrics["mean_realised_r"] is None
assert partition_metrics["maximum_symbol_trade_share"] is None
assert partition_metrics["leave_one_security_out_min_net_pnl"] is None
assert abs(partition_result.equity_curve[-1].equity - 100_287.1) < 1e-9

output = {
    "carried_position_intraday_stop": {
        "input": {"raw_open": 100.0, "raw_low": 94.0, "active_stop": 95.0},
        "direct_simulator": {
            "filled": direct_stop.filled,
            "reason_code": direct_stop.reason_code,
            "reference_price": direct_stop.reference_price,
        },
        "backtest": {
            "completed_trade_count": len(carried_result.trades),
            "final_position_count": carried_result.equity_curve[-1].position_count,
            "exit_events": [
                event
                for event in carried_result.audit_events
                if event["event"] == "EXIT_FILLED"
            ],
        },
    },
    "partition_end_open_position": {
        "entry_session": partition_entry["session_date"],
        "entry_reference_price": partition_entry["reference_price"],
        "entry_fill_price": partition_entry["fill_price"],
        "entry_quantity": partition_entry["quantity"],
        "final_session": partition_result.equity_curve[-1].session_date.isoformat(),
        "final_position_count": partition_result.equity_curve[-1].position_count,
        "completed_trade_count": len(partition_result.trades),
        "final_equity": partition_result.equity_curve[-1].equity,
        "initial_cash": initial_cash,
        "final_equity_minus_initial_cash": (
            partition_result.equity_curve[-1].equity - initial_cash
        ),
        "mark_to_fill_unrealised_pnl": mark_to_fill_unrealised_pnl,
        "raw_reference_price_move": raw_reference_move,
        "trade_metrics": {
            key: partition_metrics[key]
            for key in (
                "completed_trades",
                "net_pnl",
                "mean_realised_r",
                "maximum_symbol_trade_share",
                "leave_one_security_out_min_net_pnl",
            )
        },
    },
}
print(json.dumps(output, indent=2, sort_keys=True))
```

Captured output (all assertions passed):

```json
{
  "carried_position_intraday_stop": {
    "backtest": {
      "completed_trade_count": 0,
      "exit_events": [],
      "final_position_count": 1
    },
    "direct_simulator": {
      "filled": true,
      "reason_code": "STOP_INTRADAY",
      "reference_price": 95.0
    },
    "input": {
      "active_stop": 95.0,
      "raw_low": 94.0,
      "raw_open": 100.0
    }
  },
  "partition_end_open_position": {
    "completed_trade_count": 0,
    "entry_fill_price": 100.05,
    "entry_quantity": 58,
    "entry_reference_price": 100.0,
    "entry_session": "2026-01-05",
    "final_equity": 100287.1,
    "final_equity_minus_initial_cash": 287.1000000000058,
    "final_position_count": 1,
    "final_session": "2026-01-05",
    "initial_cash": 100000.0,
    "mark_to_fill_unrealised_pnl": 287.10000000000014,
    "raw_reference_price_move": 290.0,
    "trade_metrics": {
      "completed_trades": 0,
      "leave_one_security_out_min_net_pnl": null,
      "maximum_symbol_trade_share": null,
      "mean_realised_r": null,
      "net_pnl": 0
    }
  }
}
```

## Checks and preserved boundaries

Required focused tests:

```text
.venv/bin/python -m pytest tests/test_mps_backtest.py tests/test_mps_limitation_screen.py tests/test_mps_strategy.py -q -p no:cacheprovider
19 passed in 0.80s
```

These passing tests do not reject `STOP-001` or resolve `PART-001`; those exact
cases are not covered by the committed suite. Appendix A is the retained,
self-contained current-code reproduction.

Only this audit Markdown was modified. No source/test/config/data/report,
DeliveryOS, Trading212, provider/API, Gate 2, holdout, broker, paper, live,
runtime, database, secret, or generated state surface was changed.

## Exactly one recommended next task

Product Owner to consider one separately contracted legacy-MPS lifecycle repair
task for `STOP-001`. The repair contract must preserve the existing opening-exit
and gap-stop ordering, keep a carried position's cash/capacity/risk reserved through
the opening-entry sizing and execution phase, and only then process a carried
intraday stop before close-derived stop updates. Intraday-stop proceeds or released
capacity must not influence earlier opening decisions.

Acceptance must prove both the missed carried-stop case and the causality invariant
that the later intraday stop cannot alter opening sizing/admission. A single exit
assertion is insufficient. That task must not rerun `SWING-PC-006`, change
thresholds, force partition liquidation, open another partition, change RF-004,
or infer an economic result. This recommendation does not assign priority and does
not itself authorise a repair.

from __future__ import annotations

from datetime import date

from swingmachine.mps_contracts import (
    CorporateActionRecord,
    MpsCorporateActionType,
    MpsDividendReceivable,
    MpsFill,
    MpsPosition,
)


class MpsPortfolioLedger:
    def __init__(self, initial_cash: float) -> None:
        if initial_cash <= 0:
            raise ValueError("initial cash must be positive")
        self.cash = float(initial_cash)
        self.positions: dict[str, MpsPosition] = {}
        self.dividend_receivables: list[MpsDividendReceivable] = []
        self.fills: list[MpsFill] = []

    def book_entry(self, fill: MpsFill, position: MpsPosition) -> None:
        if fill.side != "BUY" or fill.security_id != position.security_id:
            raise ValueError("entry fill and position disagree")
        if fill.security_id in self.positions:
            raise ValueError("pyramiding is prohibited")
        cost = fill.fill_price * fill.quantity
        if cost > self.cash:
            raise ValueError("entry would create negative cash")
        self.cash -= cost
        self.positions[fill.security_id] = position
        self.fills.append(fill)

    def book_exit(self, fill: MpsFill) -> None:
        if fill.side != "SELL":
            raise ValueError("exit fill must be SELL")
        position = self.positions.get(fill.security_id)
        if position is None or fill.quantity != position.quantity:
            raise ValueError("exit must close the full held quantity")
        self.cash += fill.fill_price * fill.quantity
        del self.positions[fill.security_id]
        self.fills.append(fill)

    def apply_corporate_action(self, action: CorporateActionRecord) -> None:
        position = self.positions.get(action.security_id)
        if position is None:
            return
        if action.action_type is MpsCorporateActionType.SPLIT:
            assert action.split_ratio is not None
            ratio = action.split_ratio
            quantity = int(round(position.quantity * ratio))
            self.positions[action.security_id] = position.model_copy(
                update={
                    "quantity": quantity,
                    "entry_price": position.entry_price / ratio,
                    "initial_stop": position.initial_stop / ratio,
                    "active_stop": position.active_stop / ratio,
                    "initial_risk_per_share": position.initial_risk_per_share / ratio,
                    "highest_close_since_entry": position.highest_close_since_entry / ratio,
                    "maximum_high_since_entry": position.maximum_high_since_entry / ratio,
                }
            )
        elif action.action_type is MpsCorporateActionType.CASH_DIVIDEND:
            assert action.cash_dividend_per_share is not None and action.payment_date is not None
            self.dividend_receivables.append(
                MpsDividendReceivable(
                    security_id=action.security_id,
                    payment_date=action.payment_date,
                    amount=position.quantity * action.cash_dividend_per_share,
                )
            )
        elif action.action_type is MpsCorporateActionType.DELISTING:
            if action.cash_terms_per_share is not None:
                self.cash += position.quantity * action.cash_terms_per_share
            elif action.delisting_return is not None:
                self.cash += (
                    position.quantity * position.entry_price * (1.0 + action.delisting_return)
                )
            else:
                raise ValueError("unresolved delisting terms")
            del self.positions[action.security_id]

    def settle_dividends(self, session_date: date) -> None:
        remaining = []
        for receivable in self.dividend_receivables:
            if receivable.payment_date <= session_date:
                self.cash += receivable.amount
            else:
                remaining.append(receivable)
        self.dividend_receivables = remaining

    def equity(self, current_prices: dict[str, float]) -> float:
        return self.cash + sum(
            position.quantity * current_prices[position.security_id]
            for position in self.positions.values()
        )

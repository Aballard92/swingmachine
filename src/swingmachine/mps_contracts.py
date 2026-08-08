from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from swingmachine.modeling import ImmutableModel, NonNegativeFloat, PositiveFloat, PositiveInt


class MpsDataError(ValueError):
    """Base error for fail-closed MPS point-in-time data access."""


class DataNotAvailableError(MpsDataError):
    """Requested data was not available at the decision timestamp."""


class MpsCorporateActionType(StrEnum):
    SPLIT = "SPLIT"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    MERGER = "MERGER"
    DELISTING = "DELISTING"


class MpsVariant(StrEnum):
    B0_RANK_ONLY = "B0_RANK_ONLY"
    B1_MOMENTUM_TREND = "B1_MOMENTUM_TREND"
    B2_MOMENTUM_PULLBACK = "B2_MOMENTUM_PULLBACK"
    B3_MOMENTUM_BREAKOUT = "B3_MOMENTUM_BREAKOUT"
    B4_FULL_MPS1 = "B4_FULL_MPS1"


class PointInTimeRecord(ImmutableModel):
    event_time: datetime
    available_at: datetime
    source_version: str
    source_record_id: str

    @field_validator("event_time", "available_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("point-in-time timestamps must be timezone-aware")
        return value

    def known_at(self, decision_timestamp: datetime) -> bool:
        if decision_timestamp.tzinfo is None or decision_timestamp.utcoffset() is None:
            raise ValueError("decision timestamp must be timezone-aware")
        return self.available_at <= decision_timestamp


class SecurityMasterRecord(PointInTimeRecord):
    security_id: str
    ticker: str
    effective_from: datetime
    effective_to: datetime | None = None
    security_type: str
    primary_exchange: str
    country_of_primary_listing: str
    sector: str
    is_tradable: bool
    is_halted: bool
    is_delisted: bool
    shares_outstanding: PositiveFloat

    @model_validator(mode="after")
    def validate_window(self) -> SecurityMasterRecord:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("security-master effective window is inverted")
        return self


class DailyPriceRecord(PointInTimeRecord):
    security_id: str
    session_date: date
    open: PositiveFloat
    high: PositiveFloat
    low: PositiveFloat
    close: PositiveFloat
    volume: NonNegativeFloat
    total_return_adjusted_close: PositiveFloat

    @model_validator(mode="after")
    def validate_ohlc(self) -> DailyPriceRecord:
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high is below another OHLC value")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low is above another OHLC value")
        return self


class CorporateActionRecord(PointInTimeRecord):
    security_id: str
    action_type: MpsCorporateActionType
    effective_date: date
    payment_date: date | None = None
    split_ratio: PositiveFloat | None = None
    cash_dividend_per_share: NonNegativeFloat | None = None
    cash_terms_per_share: NonNegativeFloat | None = None
    replacement_security_id: str | None = None
    delisting_return: float | None = None

    @model_validator(mode="after")
    def validate_action(self) -> CorporateActionRecord:
        if self.action_type is MpsCorporateActionType.SPLIT and self.split_ratio is None:
            raise ValueError("split action requires split_ratio")
        if self.action_type is MpsCorporateActionType.CASH_DIVIDEND:
            if self.cash_dividend_per_share is None or self.payment_date is None:
                raise ValueError("cash dividend requires amount and payment_date")
        if self.action_type is MpsCorporateActionType.DELISTING:
            if self.delisting_return is None and self.cash_terms_per_share is None:
                raise ValueError("delisting requires actual return or cash terms")
        return self


class EarningsAnnouncementRecord(PointInTimeRecord):
    security_id: str
    scheduled_event_time: datetime


class MpsDecisionContext(ImmutableModel):
    session_date: date
    decision_timestamp: datetime
    data_version_hash: str


class MpsCandidate(ImmutableModel):
    security_id: str
    ticker: str
    signal_session: date
    variant: MpsVariant
    momentum_rank: float
    adv20_dollars: NonNegativeFloat
    structure_stop: PositiveFloat | None = None
    signal_close: PositiveFloat
    signal_atr20: PositiveFloat | None = None
    sector: str


class MpsOrderRejection(ImmutableModel):
    security_id: str
    reason_code: str
    detail: str


class MpsPosition(ImmutableModel):
    security_id: str
    ticker: str
    quantity: PositiveInt
    entry_price: PositiveFloat
    initial_stop: PositiveFloat
    active_stop: PositiveFloat
    initial_risk_per_share: PositiveFloat
    sector: str
    entry_session: date
    holding_sessions: int = 0
    highest_close_since_entry: PositiveFloat
    maximum_high_since_entry: PositiveFloat


class MpsEntryPlan(ImmutableModel):
    candidate: MpsCandidate
    approved: bool
    reason_code: str
    entry_cap: PositiveFloat
    planned_stop: PositiveFloat
    risk_budget: NonNegativeFloat
    quantity: int
    regime_multiplier: NonNegativeFloat


class MpsFill(ImmutableModel):
    security_id: str
    session_date: date
    side: str
    quantity: PositiveInt
    reference_price: PositiveFloat
    fill_price: PositiveFloat
    cost_bps: NonNegativeFloat
    reason_code: str


class MpsDividendReceivable(ImmutableModel):
    security_id: str
    payment_date: date
    amount: NonNegativeFloat


class MpsTrade(ImmutableModel):
    security_id: str
    ticker: str
    variant: MpsVariant
    entry_session: date
    exit_session: date
    entry_reference_price: PositiveFloat
    entry_fill_price: PositiveFloat
    exit_reference_price: PositiveFloat
    exit_fill_price: PositiveFloat
    entry_quantity: PositiveInt
    exit_quantity: PositiveInt
    initial_stop: PositiveFloat
    exit_reason: str
    holding_sessions: int
    gross_pnl: float
    net_pnl: float
    realised_r: float
    mfe_r: float
    mae_r: float
    sector: str


class MpsEquityPoint(ImmutableModel):
    session_date: date
    equity: PositiveFloat
    cash: NonNegativeFloat
    gross_exposure: NonNegativeFloat
    position_count: int


class MpsBacktestResult(ImmutableModel):
    variant: MpsVariant
    config_hash: str
    data_version_hash: str
    cost_bps: NonNegativeFloat
    trades: tuple[MpsTrade, ...]
    equity_curve: tuple[MpsEquityPoint, ...]
    audit_events: tuple[dict[str, object], ...]
    rejected_orders: tuple[MpsOrderRejection, ...]

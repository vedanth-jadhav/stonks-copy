from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentID(StrEnum):
    DISCOVERY = "agent_00_discovery"
    UNIVERSE = "agent_01_universe"
    QUALITY = "agent_02_quality"
    MACRO = "agent_06_macro"
    EVENTS = "agent_10_events"
    SENTIMENT = "agent_09_sentiment"
    SECTOR = "agent_07_sector"
    OWNERSHIP = "agent_08_ownership"
    RISK = "agent_13_risk"
    MOMENTUM = "agent_03_momentum"
    REVERSION = "agent_04_reversion"
    PAIRS = "agent_05_pairs"
    LIQUIDITY = "agent_12_liquidity"
    BACKTESTER = "agent_11_backtester"


class PipelineSlot(StrEnum):
    MORNING = "morning-pipeline"
    MIDDAY = "midday-pipeline"
    AFTERNOON = "afternoon-pipeline"
    EVENING = "evening-pipeline"


class JobStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"
    MISSED = "missed"


class JobRequestStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class SessionState(StrEnum):
    PRE_MARKET = "pre_market"
    OPEN = "open"
    POST_MARKET = "post_market"
    CLOSED = "closed"


class AgentStatus(StrEnum):
    SUCCESS = "success"
    NEUTRAL = "neutral"
    FAILED = "failed"
    SKIPPED = "skipped"


class DecisionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"
    WATCHLIST = "WATCHLIST"


class PositionType(StrEnum):
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    PAIRS = "PAIRS"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    QUALITY = "QUALITY"


class UniverseItem(BaseModel):
    ticker: str
    company: str | None = None
    sector: str | None = None
    market_cap_cr: float | None = None
    adv_20d_cr: float | None = None
    ratios: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PortfolioSnapshot(BaseModel):
    cash_balance: float
    total_deployed: float
    total_market_value: float = 0.0
    portfolio_value: float
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_charges_paid: float = 0.0
    open_positions: int = 0
    priced_positions: int = 0
    unpriced_positions: int = 0


class PriceBar(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float
    as_of: datetime


class PriceData(BaseModel):
    ticker: str
    last_price: float | None = None
    prev_high: float | None = None
    prev_low: float | None = None
    prev_close: float | None = None
    as_of: datetime | None = None
    previous_bar: PriceBar | None = None
    history: list[PriceBar] = Field(default_factory=list)


class UniverseDiscoveryPlan(BaseModel):
    status: str = "idle"
    market_regime: str = "neutral"
    selected_profile: str = "standard"
    profile_ladder: list[str] = Field(default_factory=list)
    query_ladder: list[str] = Field(default_factory=list)
    target_min_count: int = 20
    target_max_count: int = 80
    fallback_level: int = 0
    final_query: str | None = None
    final_profile: str | None = None
    candidate_count: int = 0


class MarketContext(BaseModel):
    run_id: str
    timestamp_utc: datetime
    market: str
    date: date
    time_ist: time
    session_state: SessionState
    is_market_day: bool
    regime: str = "NEUTRAL"
    portfolio: PortfolioSnapshot
    universe: list[UniverseItem] = Field(default_factory=list)
    universe_discovery: UniverseDiscoveryPlan = Field(default_factory=UniverseDiscoveryPlan)
    price_bundle: dict[str, PriceData] = Field(default_factory=dict)
    memory_context: dict[str, str] = Field(default_factory=dict)
    operator_guidance: list[str] = Field(default_factory=list)
    runtime_overrides: dict[str, Any] = Field(default_factory=dict)
    upstream_results: dict[str, "AgentResult"] = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent_id: str
    run_id: str
    status: AgentStatus
    scores_by_ticker: dict[str, float] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime


class EntryPolicy(BaseModel):
    fill_model: str
    valid_until: time | None = None


class StopPolicy(BaseModel):
    hard_stop_price: float | None = None
    trailing_stop_price: float | None = None


class TradeDecision(BaseModel):
    decision: DecisionType
    ticker: str
    position_type: PositionType = PositionType.QUALITY
    target_weight: float = 0.0
    shares: int = 0
    entry_policy: EntryPolicy
    stop_policy: StopPolicy
    confidence: float = 0.0
    reason_code: str = ""
    origin: str = "AUTONOMOUS"
    active_agent_weights: dict[str, float] = Field(default_factory=dict)


class ReflectionLesson(BaseModel):
    agent_id: str
    headline: str
    lesson: str
    confidence: float = 0.5


class JobRunInput(BaseModel):
    run_id: str
    job_name: str
    status: JobStatus
    started_at: datetime

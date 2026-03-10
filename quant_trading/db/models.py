from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, Date, DateTime, Float, Integer, String, Text, UniqueConstraint

from .base import Base


def default_uuid() -> str:
    return str(uuid4())


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(String(36), primary_key=True, default=default_uuid)
    run_date = Column(Date, index=True, nullable=False)
    job_name = Column(String(128), index=True, nullable=False)
    status = Column(String(32), index=True, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    payload = Column(JSON, default=dict, nullable=False)
    error = Column(Text, nullable=True)


class JobRequest(Base):
    __tablename__ = "job_requests"

    id = Column(String(36), primary_key=True, default=default_uuid)
    job_name = Column(String(128), index=True, nullable=False)
    dedupe_key = Column(String(128), index=True, nullable=False)
    requested_by = Column(String(64), index=True, nullable=False)
    status = Column(String(32), index=True, nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    result = Column(JSON, default=dict, nullable=False)
    error = Column(Text, nullable=True)
    run_id = Column(String(36), index=True, nullable=True)
    lease_owner = Column(String(128), index=True, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    requested_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class TradingSlot(Base):
    __tablename__ = "trading_slots"
    __table_args__ = (UniqueConstraint("slot_date", "slot_name", name="uq_trading_slot_date_name"),)

    id = Column(String(36), primary_key=True, default=default_uuid)
    slot_date = Column(Date, index=True, nullable=False)
    slot_name = Column(String(64), index=True, nullable=False)
    trigger = Column(String(128), nullable=False)
    run_id = Column(String(36), index=True, nullable=False)
    status = Column(String(32), index=True, nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    claimed_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    finished_at = Column(DateTime, nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (UniqueConstraint("run_id", "agent_id", name="uq_agent_run"),)

    id = Column(String(36), primary_key=True, default=default_uuid)
    run_id = Column(String(36), index=True, nullable=False)
    agent_id = Column(String(64), index=True, nullable=False)
    status = Column(String(32), index=True, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    warnings = Column(JSON, default=list, nullable=False)
    artifacts = Column(JSON, default=dict, nullable=False)


class SignalHistory(Base):
    __tablename__ = "signal_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_date = Column(Date, index=True, nullable=False)
    run_id = Column(String(36), index=True, nullable=False)
    agent_id = Column(String(64), index=True, nullable=False)
    ticker = Column(String(32), index=True, nullable=False)
    score = Column(Float, nullable=False)
    details = Column(JSON, default=dict, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=default_uuid)
    run_id = Column(String(36), index=True, nullable=False)
    ticker = Column(String(32), index=True, nullable=False)
    decision = Column(String(32), nullable=False)
    position_type = Column(String(32), nullable=False)
    shares = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class TradeDecisionRecord(Base):
    __tablename__ = "trade_decisions"

    id = Column(String(36), primary_key=True, default=default_uuid)
    run_id = Column(String(36), index=True, nullable=False)
    ticker = Column(String(32), index=True, nullable=False)
    decision = Column(String(32), index=True, nullable=False)
    position_type = Column(String(32), nullable=False)
    shares = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    origin = Column(String(32), nullable=False, default="AUTONOMOUS")
    payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class Fill(Base):
    __tablename__ = "fills"

    id = Column(String(36), primary_key=True, default=default_uuid)
    order_id = Column(String(36), index=True, nullable=False)
    run_id = Column(String(36), index=True, nullable=False)
    ticker = Column(String(32), index=True, nullable=False)
    action = Column(String(16), nullable=False)
    shares = Column(Integer, nullable=False)
    fill_price = Column(Float, nullable=False)
    charges = Column(Float, nullable=False)
    execution_type = Column(String(64), nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class Position(Base):
    __tablename__ = "positions"

    ticker = Column(String(32), primary_key=True)
    shares = Column(Integer, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    sector = Column(String(128), nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    trailing_stop_price = Column(Float, nullable=True)
    position_type = Column(String(32), nullable=False)
    last_updated = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class DailyMark(Base):
    __tablename__ = "daily_marks"

    mark_date = Column(Date, primary_key=True)
    portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    total_realized_pnl = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False)
    benchmark_close = Column(Float, nullable=True)
    benchmark_return_pct = Column(Float, nullable=True)
    alpha_pct = Column(Float, nullable=True)
    details = Column(JSON, default=dict, nullable=False)


class ChargeSchedule(Base):
    __tablename__ = "charge_schedules"

    id = Column(String(36), primary_key=True, default=default_uuid)
    broker = Column(String(64), index=True, nullable=False)
    venue = Column(String(64), index=True, nullable=False)
    product = Column(String(32), index=True, nullable=False)
    effective_date = Column(Date, index=True, nullable=False)
    schedule = Column(JSON, default=dict, nullable=False)


class Reflection(Base):
    __tablename__ = "reflections"

    id = Column(String(36), primary_key=True, default=default_uuid)
    reflection_date = Column(Date, index=True, nullable=False)
    agent_id = Column(String(64), index=True, nullable=False)
    summary = Column(Text, nullable=False)
    lessons = Column(JSON, default=list, nullable=False)


class RuntimeState(Base):
    __tablename__ = "runtime_state"

    id = Column(Integer, primary_key=True, default=1)
    autonomy_paused = Column(Integer, nullable=False, default=0)
    entries_blocked = Column(Integer, nullable=False, default=0)
    exits_only = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_reason = Column(Text, nullable=True)


class DeskMessage(Base):
    __tablename__ = "desk_messages"

    id = Column(String(36), primary_key=True, default=default_uuid)
    scope = Column(String(64), index=True, nullable=False, default="global")
    status = Column(String(32), index=True, nullable=False, default="active")
    raw_text = Column(Text, nullable=False)
    parsed_intent = Column(JSON, default=dict, nullable=False)
    effective_from = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class RuntimeOverride(Base):
    __tablename__ = "runtime_overrides"

    id = Column(String(36), primary_key=True, default=default_uuid)
    scope = Column(String(64), index=True, nullable=False, default="global")
    key = Column(String(128), index=True, nullable=False)
    enabled = Column(Integer, nullable=False, default=1)
    value = Column(JSON, default=dict, nullable=False)
    effective_from = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class OperatorAction(Base):
    __tablename__ = "operator_actions"

    id = Column(String(36), primary_key=True, default=default_uuid)
    action = Column(String(128), index=True, nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeats"

    service_name = Column(String(64), primary_key=True)
    instance_id = Column(String(128), nullable=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    details = Column(JSON, default=dict, nullable=False)


class MemoryNode(Base):
    __tablename__ = "memory_nodes"

    id = Column(String(36), primary_key=True, default=default_uuid)
    node_type = Column(String(64), index=True, nullable=False)
    ref_id = Column(String(128), index=True, nullable=False)
    content = Column(Text, nullable=False)
    details = Column(JSON, default=dict, nullable=False)


class MemoryEdge(Base):
    __tablename__ = "memory_edges"

    id = Column(String(36), primary_key=True, default=default_uuid)
    source_ref = Column(String(128), index=True, nullable=False)
    target_ref = Column(String(128), index=True, nullable=False)
    relation = Column(String(64), index=True, nullable=False)
    details = Column(JSON, default=dict, nullable=False)


class AgentSignalOutcome(Base):
    __tablename__ = "agent_signal_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(36), index=True, nullable=False)
    agent_id = Column(String(64), index=True, nullable=False)
    ticker = Column(String(32), index=True, nullable=False)
    outcome_5d = Column(Float, nullable=True)
    outcome_10d = Column(Float, nullable=True)
    directionally_correct = Column(Integer, nullable=True)
    was_decisive = Column(Integer, nullable=True)
    responsibility = Column(String(64), nullable=True)
    details = Column(JSON, default=dict, nullable=False)


class AgentICHistory(Base):
    __tablename__ = "agent_ic_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ic_date = Column(Date, index=True, nullable=False)
    agent_id = Column(String(64), index=True, nullable=False)
    ic_value = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=True)
    avg_rr = Column(Float, nullable=True)
    details = Column(JSON, default=dict, nullable=False)

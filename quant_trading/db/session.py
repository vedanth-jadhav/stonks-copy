from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from .base import Base
from .models import ChargeSchedule, RuntimeState


def create_engine_and_sessionmaker(database_url: str) -> tuple[object, sessionmaker[Session]]:
    if database_url.startswith("sqlite") and ":memory:" in database_url:
        # Use SQLite named shared-cache in-memory mode so multiple connections (and threads)
        # see the same schema/data, but each engine remains isolated.
        memdb = f"memdb_{uuid4().hex}"
        engine = create_engine(
            f"sqlite:///file:{memdb}?mode=memory&cache=shared",
            connect_args={"check_same_thread": False, "uri": True},
        )
    else:
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    return engine, sessionmaker(engine, expire_on_commit=False)


def init_db(engine: object, session_factory: sessionmaker[Session]) -> None:
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    position_columns = {column["name"] for column in inspector.get_columns("positions")}
    daily_mark_columns = {column["name"] for column in inspector.get_columns("daily_marks")}
    if "sector" not in position_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE positions ADD COLUMN sector VARCHAR(128)"))
    if "total_realized_pnl" not in daily_mark_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE daily_marks ADD COLUMN total_realized_pnl FLOAT NOT NULL DEFAULT 0"))
    with session_factory() as session:
        existing = session.scalar(select(ChargeSchedule).limit(1))
        if existing is None:
            session.add(
                ChargeSchedule(
                    broker="zerodha",
                    venue="NSE",
                    product="CNC",
                    effective_date=date(2025, 1, 1),
                    schedule={
                        "brokerage_buy": 0.0,
                        "brokerage_sell": 0.0,
                        "stt_buy": 0.001,
                        "stt_sell": 0.001,
                        "exchange_buy": 0.0000335,
                        "exchange_sell": 0.0000335,
                        "sebi_buy": 0.000001,
                        "sebi_sell": 0.000001,
                        "stamp_buy": 0.00015,
                        "gst_rate": 0.18,
                        "dp_sell_flat": 15.93,
                        "slippage_buy": 0.0005,
                        "slippage_sell": 0.0005,
                    },
                )
            )
        runtime_state = session.get(RuntimeState, 1)
        if runtime_state is None:
            session.add(RuntimeState(id=1))
        session.commit()

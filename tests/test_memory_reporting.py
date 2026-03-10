from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from quant_trading.db.models import MemoryNode, Reflection
from quant_trading.db.repository import QuantRepository
from sqlalchemy.orm import Session

from quant_trading.db.models import AgentICHistory, AgentSignalOutcome, DailyMark, Position
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.memory.attribution import attribute_trade_outcome
from quant_trading.memory.graph import GraphMemory
from quant_trading.memory.structured import latest_lessons
from quant_trading.memory.reflection import build_reflection_prompt, run_reflection
from quant_trading.reports.weekly import write_weekly_report


def build_session() -> Session:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return session_factory()


def build_repository() -> QuantRepository:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return QuantRepository(engine, session_factory)


def test_attribute_trade_outcome_marks_decisive_loss_and_root_cause() -> None:
    payload = attribute_trade_outcome(
        conviction_threshold=0.6,
        signals={"agent_03_momentum": 0.8, "agent_09_sentiment": -0.1},
        outcome=-0.04,
    )
    assert payload["agent_03_momentum"]["responsibility"] == "PRIMARY_LOSS_CAUSE"
    assert payload["agent_03_momentum"]["root_cause"] == "AGENT_FAILURE:agent_03_momentum"


def test_graph_memory_search_ranks_exact_ref_matches_first() -> None:
    session = build_session()
    graph = GraphMemory(session)
    graph.add_episode("agent_03:reliance", "Momentum failed in caution regime")
    graph.add_episode("agent_09:tcs", "Sentiment neutral after no fresh articles")

    hits = graph.search_hits("agent_03 caution", limit=2)
    assert hits[0].ref_id == "agent_03:reliance"
    assert "Momentum" in hits[0].content


def test_latest_lessons_formats_reflection_payloads() -> None:
    session = build_session()
    session.add(
        Reflection(
            reflection_date=date(2026, 3, 6),
            agent_id="agent_03_momentum",
            summary="Momentum summary",
            lessons=[{"headline": "Regime", "lesson": "Reduce size in caution regime", "confidence": 0.8}],
        )
    )
    session.commit()

    lessons = latest_lessons(session, "agent_03_momentum")

    assert lessons == ["Regime: Reduce size in caution regime (confidence=0.8)"]


def test_reflection_falls_back_to_deterministic_summary_when_gateway_missing() -> None:
    session = build_session()
    session.add(
        AgentSignalOutcome(
            trade_id="trade-1",
            agent_id="agent_03_momentum",
            ticker="RELIANCE",
            outcome_5d=0.05,
            outcome_10d=0.08,
            directionally_correct=1,
            was_decisive=1,
            responsibility="PRIMARY_WIN_DRIVER",
            details={},
        )
    )
    session.add(
        AgentICHistory(
            ic_date=date(2026, 3, 6),
            agent_id="agent_03_momentum",
            ic_value=0.07,
            win_rate=0.58,
            avg_rr=2.1,
            details={},
        )
    )
    session.commit()

    prompt = build_reflection_prompt(session=session, agent_id="agent_03_momentum")
    assert "Observed trades: 1" in prompt

    reflection = run_reflection(
        session=session,
        gateway=None,
        agent_id="agent_03_momentum",
        reflection_date=date(2026, 3, 6),
        model_alias="reflection",
    )
    assert "agent_03_momentum has 1 attributed outcomes" in reflection.summary
    assert reflection.lessons


def test_repository_builds_memory_prompts_from_lessons_and_episodes() -> None:
    repository = build_repository()
    with repository.session_factory() as session:
        session.add(
            Reflection(
                reflection_date=date(2026, 3, 6),
                agent_id="agent_03_momentum",
                summary="Momentum summary",
                lessons=[{"headline": "Regime", "lesson": "Reduce size in caution regime", "confidence": 0.8}],
            )
        )
        session.add(
            MemoryNode(
                node_type="episode",
                ref_id="agent_03_momentum:RELIANCE:trade-1",
                content="agent_03_momentum on RELIANCE produced PRIMARY_LOSS_CAUSE in caution regime.",
                details={"agent_id": "agent_03_momentum"},
            )
        )
        session.commit()

    prompts = repository.get_memory_prompts()

    assert "Recent lessons:" in prompts["agent_03_momentum"]
    assert "Reduce size in caution regime" in prompts["agent_03_momentum"]
    assert "Similar episodes:" in prompts["agent_03_momentum"]
    assert "PRIMARY_LOSS_CAUSE" in prompts["agent_03_momentum"]


def test_weekly_report_renders_marks_and_positions(tmp_path: Path) -> None:
    session = build_session()
    session.add(
        DailyMark(
            mark_date=date(2026, 3, 6),
            portfolio_value=1_020_000,
            cash_balance=600_000,
            realized_pnl=5_000,
            unrealized_pnl=15_000,
            benchmark_close=22_100,
            benchmark_return_pct=0.8,
            alpha_pct=1.2,
            details={},
        )
    )
    session.add(
        Position(
            ticker="RELIANCE",
            shares=10,
            avg_entry_price=1250.0,
            total_cost=12_500.0,
            stop_loss_price=1160.0,
            trailing_stop_price=None,
            position_type="QUALITY",
            last_updated=datetime.now(UTC),
        )
    )
    session.commit()

    output = write_weekly_report(session=session, output_path=tmp_path / "week.md")
    contents = output.read_text()
    assert "Portfolio Summary" in contents
    assert "RELIANCE" in contents

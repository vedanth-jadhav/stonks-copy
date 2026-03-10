from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from quant_trading.db.models import AgentICHistory, AgentSignalOutcome, Reflection
from quant_trading.schemas import ReflectionLesson
from quant_trading.timeutils import market_today
from quant_trading.tools.cliproxy import CLIProxyGateway


def _within_lookback(day: date | None, cutoff: date) -> bool:
    return day is None or day >= cutoff


def _outcome_date(row: AgentSignalOutcome) -> date | None:
    value = (row.details or {}).get("signal_date")
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def build_reflection_prompt(session: Session, agent_id: str, lookback_days: int = 30) -> str:
    cutoff = market_today() - timedelta(days=lookback_days)
    outcomes = [
        row
        for row in session.query(AgentSignalOutcome).filter(AgentSignalOutcome.agent_id == agent_id).all()
        if _within_lookback(_outcome_date(row), cutoff)
    ]
    ic_rows = session.query(AgentICHistory).filter(AgentICHistory.agent_id == agent_id, AgentICHistory.ic_date >= cutoff).all()
    win_rate = (
        sum(1 for row in outcomes if (row.outcome_5d or 0.0) > 0) / len(outcomes) if outcomes else 0.0
    )
    ic_mean = mean([row.ic_value for row in ic_rows]) if ic_rows else 0.0
    responsibilities: dict[str, int] = {}
    for row in outcomes:
        if row.responsibility:
            responsibilities[row.responsibility] = responsibilities.get(row.responsibility, 0) + 1

    top_causes = ", ".join(f"{key}:{value}" for key, value in sorted(responsibilities.items())) or "none"
    return (
        f"Agent: {agent_id}\n"
        f"Lookback days: {lookback_days}\n"
        f"Observed trades: {len(outcomes)}\n"
        f"Win rate: {win_rate:.2%}\n"
        f"Average IC: {ic_mean:.4f}\n"
        f"Responsibility counts: {top_causes}\n"
        "Return compact JSON with keys summary and lessons. "
        "Each lesson must include headline, lesson, confidence."
    )


def deterministic_reflection(session: Session, agent_id: str, lookback_days: int = 30) -> tuple[str, list[dict]]:
    cutoff = market_today() - timedelta(days=lookback_days)
    outcomes = [
        row
        for row in session.query(AgentSignalOutcome).filter(AgentSignalOutcome.agent_id == agent_id).all()
        if _within_lookback(_outcome_date(row), cutoff)
    ]
    positives = [row for row in outcomes if (row.outcome_5d or 0.0) > 0]
    negatives = [row for row in outcomes if (row.outcome_5d or 0.0) < 0]
    summary = (
        f"{agent_id} has {len(outcomes)} attributed outcomes: "
        f"{len(positives)} positive and {len(negatives)} negative."
    )
    lessons = [
        ReflectionLesson(
            agent_id=agent_id,
            headline="Coverage",
            lesson=f"Memory currently contains {len(outcomes)} attributed trades for {agent_id}.",
            confidence=0.5,
        ).model_dump(),
        ReflectionLesson(
            agent_id=agent_id,
            headline="Bias",
            lesson="Keep neutral outputs when data quality is weak; avoid forcing directional calls.",
            confidence=0.6,
        ).model_dump(),
    ]
    return summary, lessons


def run_reflection(
    session: Session,
    gateway: CLIProxyGateway | None,
    agent_id: str,
    reflection_date: date,
    model_alias: str,
) -> Reflection:
    prompt = build_reflection_prompt(session=session, agent_id=agent_id)
    response: dict
    if gateway is None:
        summary, lessons = deterministic_reflection(session=session, agent_id=agent_id)
        response = {"summary": summary, "lessons": lessons}
    else:
        try:
            response = gateway.generate_json(
                model_alias=model_alias,
                system_prompt="You summarize trading agent lessons as terse production JSON.",
                user_prompt=prompt,
            )
        except Exception:
            summary, lessons = deterministic_reflection(session=session, agent_id=agent_id)
            response = {"summary": summary, "lessons": lessons}

    reflection = Reflection(
        reflection_date=reflection_date,
        agent_id=agent_id,
        summary=response.get("summary", f"No reflection available for {agent_id}."),
        lessons=response.get("lessons", []),
    )
    session.add(reflection)
    session.commit()
    return reflection

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from quant_trading.db.models import AgentICHistory, Reflection


def latest_lessons(session: Session, agent_id: str, limit: int = 12) -> list[str]:
    rows = (
        session.query(Reflection)
        .filter(Reflection.agent_id == agent_id)
        .order_by(Reflection.reflection_date.desc())
        .limit(limit)
        .all()
    )
    lessons: list[str] = []
    for row in rows:
        for lesson in row.lessons or []:
            if isinstance(lesson, dict):
                headline = str(lesson.get("headline") or "").strip()
                body = str(lesson.get("lesson") or "").strip()
                confidence = lesson.get("confidence")
                rendered = f"{headline}: {body}".strip(": ").strip()
                if confidence is not None:
                    rendered = f"{rendered} (confidence={confidence})"
                lessons.append(rendered)
            elif isinstance(lesson, str):
                lessons.append(lesson)
    return lessons[:limit]


def seed_ic_values(session: Session, agent_ids: list[str], for_date: date) -> None:
    if session.query(AgentICHistory).filter(AgentICHistory.ic_date == for_date).first():
        return
    for agent_id in agent_ids:
        session.add(AgentICHistory(ic_date=for_date, agent_id=agent_id, ic_value=0.0, details={"seeded_at": datetime.now(UTC).isoformat()}))
    session.commit()

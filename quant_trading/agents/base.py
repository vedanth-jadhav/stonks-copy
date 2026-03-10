from __future__ import annotations

from datetime import UTC, datetime

from quant_trading.schemas import AgentResult, AgentStatus, MarketContext


class BaseAgent:
    agent_id = "base"

    def run(self, context: MarketContext) -> AgentResult:
        started = datetime.now(UTC)
        scores, artifacts, warnings = self.evaluate(context)
        finished = datetime.now(UTC)
        status = AgentStatus.SUCCESS if scores or artifacts else AgentStatus.NEUTRAL
        return AgentResult(
            agent_id=self.agent_id,
            run_id=context.run_id,
            status=status,
            scores_by_ticker=scores,
            artifacts=artifacts,
            warnings=warnings,
            started_at=started,
            finished_at=finished,
        )

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        _ = context
        return {}, {}, []

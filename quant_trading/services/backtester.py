from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
import math
from statistics import mean

from sqlalchemy import delete, select

from quant_trading.db.repository import QuantRepository
from quant_trading.db.models import AgentICHistory, AgentSignalOutcome, Fill, Order, SignalHistory
from quant_trading.memory.graph import GraphMemory
from quant_trading.memory.attribution import attribute_trade_outcome
from quant_trading.timeutils import market_today
from quant_trading.tools.yfinance_client import YFinanceClient


def _corr(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    mean_a = mean(a)
    mean_b = mean(b)
    dev_a = [x - mean_a for x in a]
    dev_b = [x - mean_b for x in b]
    denom = (sum(x * x for x in dev_a) * sum(y * y for y in dev_b)) ** 0.5
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(dev_a, dev_b)) / denom


def _decay_lambda(ic_5d: float, ic_10d: float) -> float | None:
    if ic_5d == 0 or ic_10d == 0:
        return None
    ratio = abs(ic_10d) / abs(ic_5d)
    if ratio <= 0:
        return None
    return max(0.0, -math.log(ratio) / 5.0)


@dataclass(slots=True)
class BackfillSummary:
    signal_rows_updated: int
    attributed_trades: int
    ic_rows: int

    @property
    def updated_signal_rows(self) -> int:
        return self.signal_rows_updated


class BacktesterService:
    def __init__(
        self,
        repository: QuantRepository | None = None,
        session_factory=None,
        market_data: YFinanceClient | None = None,
        conviction_threshold: float = 0.6,
    ) -> None:
        if repository is None and session_factory is None:
            raise ValueError("BacktesterService requires a repository or session_factory.")
        self.session_factory = session_factory or repository.session_factory
        self.market_data = market_data or YFinanceClient()
        self.conviction_threshold = conviction_threshold

    def _price_series(self, ticker: str) -> list[tuple[date, float]]:
        symbol = ticker if ticker.endswith(".NS") else f"{ticker}.NS"
        price_data = self.market_data.load_price_data(symbol, period="2y")
        return [(bar.as_of.date(), bar.close) for bar in price_data.history]

    @staticmethod
    def _forward_return(series: list[tuple[date, float]], anchor_date: date, horizon: int) -> float | None:
        if not series:
            return None
        dates = [item[0] for item in series]
        closes = [item[1] for item in series]
        start_idx = next((idx for idx, series_date in enumerate(dates) if series_date >= anchor_date), None)
        if start_idx is None:
            return None
        end_idx = start_idx + horizon
        if end_idx >= len(closes):
            return None
        start_close = closes[start_idx]
        end_close = closes[end_idx]
        if start_close <= 0:
            return None
        return (end_close / start_close) - 1.0

    def run_backfill(self, as_of: date | None = None) -> BackfillSummary:
        anchor = as_of or market_today()
        updated_signal_rows = 0
        attributed_trades = 0
        ic_rows = 0

        with self.session_factory() as session:
            graph = GraphMemory(session)
            signals = session.scalars(select(SignalHistory).order_by(SignalHistory.signal_date.asc(), SignalHistory.id.asc())).all()
            price_cache: dict[str, list[tuple[date, float]]] = {}
            grouped_for_ic: dict[str, list[tuple[float, float, float | None]]] = defaultdict(list)

            for signal in signals:
                series = price_cache.setdefault(signal.ticker, self._price_series(signal.ticker))
                forward_5d = self._forward_return(series, signal.signal_date, 5)
                forward_10d = self._forward_return(series, signal.signal_date, 10)
                if forward_5d is None:
                    continue
                signal.details = {
                    **(signal.details or {}),
                    "forward_return_5d": forward_5d,
                    "forward_return_10d": forward_10d,
                }
                grouped_for_ic[signal.agent_id].append((signal.score, forward_5d, forward_10d))
                updated_signal_rows += 1

            session.execute(delete(AgentICHistory).where(AgentICHistory.ic_date == anchor))
            raw_ic_rows: list[tuple[str, float, float, float | None, int, float | None, int]] = []
            for agent_id, rows in grouped_for_ic.items():
                recent_rows = rows[-63:]
                xs_5d = [row[0] for row in recent_rows]
                ys_5d = [row[1] for row in recent_rows]
                rows_10d = [(score, ret_10d) for score, _, ret_10d in recent_rows if ret_10d is not None]
                xs_10d = [row[0] for row in rows_10d]
                ys_10d = [float(row[1]) for row in rows_10d]
                ic_5d = _corr(xs_5d, ys_5d)
                ic_10d = _corr(xs_10d, ys_10d) if len(rows_10d) >= 2 else None
                decay_lambda = _decay_lambda(ic_5d, ic_10d or 0.0) if ic_10d is not None else None
                wins = [1.0 if value > 0 else 0.0 for value in ys_5d]
                gains = [value for value in ys_5d if value > 0]
                losses = [abs(value) for value in ys_5d if value < 0]
                raw_ic_rows.append(
                    (
                        agent_id,
                        ic_5d,
                        ic_10d or 0.0,
                        mean(wins) if wins else 0.0,
                        (mean(gains) / mean(losses)) if gains and losses else None,
                        len(recent_rows),
                        decay_lambda,
                        len(rows_10d),
                    )
                )

            active_total = sum(max(row[1], 0.0) for row in raw_ic_rows if row[1] >= 0.04 and row[5] >= 30)
            for agent_id, ic_5d, ic_10d, win_rate, avg_rr, sample_size, decay_lambda, sample_size_10d in raw_ic_rows:
                active = ic_5d >= 0.04 and sample_size >= 30
                ic_weight = (max(ic_5d, 0.0) / active_total) if active_total > 0 and active else 0.0
                session.add(
                    AgentICHistory(
                        ic_date=anchor,
                        agent_id=agent_id,
                        ic_value=ic_5d,
                        win_rate=win_rate,
                        avg_rr=avg_rr,
                        details={
                            "sample_size": sample_size,
                            "sample_size_10d": sample_size_10d,
                            "active": active,
                            "ic_weight": round(ic_weight, 6),
                            "ic_10d": ic_10d,
                            "decay_lambda": decay_lambda,
                        },
                    )
                )
                ic_rows += 1

            orders = {order.id: order for order in session.scalars(select(Order)).all()}
            fills = session.scalars(select(Fill).where(Fill.action == "BUY")).all()
            for fill in fills:
                order = orders.get(fill.order_id)
                if order is None:
                    continue
                active_agent_weights = dict((order.payload or {}).get("active_agent_weights") or {})
                signal_rows = session.scalars(
                    select(SignalHistory).where(
                        SignalHistory.run_id == fill.run_id,
                        SignalHistory.ticker == fill.ticker,
                    )
                ).all()
                if not signal_rows:
                    continue
                if active_agent_weights:
                    signal_rows = [row for row in signal_rows if row.agent_id in active_agent_weights]
                if not signal_rows:
                    continue
                series = price_cache.setdefault(fill.ticker, self._price_series(fill.ticker))
                anchor_date = min(row.signal_date for row in signal_rows)
                forward_5d = self._forward_return(series, anchor_date, 5)
                if forward_5d is None:
                    continue
                forward_10d = self._forward_return(series, anchor_date, 10)
                trade_signals = {row.agent_id: row.score for row in signal_rows}
                attribution = attribute_trade_outcome(
                    conviction_threshold=self.conviction_threshold,
                    signals=trade_signals,
                    outcome=forward_5d,
                )
                session.execute(delete(AgentSignalOutcome).where(AgentSignalOutcome.trade_id == order.id))
                for agent_id, row in attribution.items():
                    session.add(
                        AgentSignalOutcome(
                            trade_id=order.id,
                            agent_id=agent_id,
                            ticker=fill.ticker,
                            outcome_5d=forward_5d,
                            outcome_10d=forward_10d,
                            directionally_correct=int(bool(row["directionally_correct"])),
                            was_decisive=int(bool(row["was_decisive"])),
                            responsibility=row["responsibility"],
                            details={
                                "signal_score": row["signal_score"],
                                "root_cause": row["root_cause"],
                                "run_id": fill.run_id,
                                "signal_date": anchor_date.isoformat(),
                            },
                        )
                    )
                    ref_id = f"{agent_id}:{fill.ticker}:{order.id}"
                    content = (
                        f"{agent_id} on {fill.ticker} produced {row['responsibility']} "
                        f"with signal {row['signal_score']:.4f}, 5d outcome {forward_5d:.4f}, "
                        f"root cause {row['root_cause']}."
                    )
                    graph.add_episode(
                        ref_id=ref_id,
                        content=content,
                        metadata={
                            "agent_id": agent_id,
                            "ticker": fill.ticker,
                            "outcome_5d": forward_5d,
                            "outcome_10d": forward_10d,
                            "responsibility": row["responsibility"],
                            "root_cause": row["root_cause"],
                        },
                    )
                    graph.relate(source_ref=agent_id, target_ref=ref_id, relation="generated_episode", metadata={"ticker": fill.ticker})
                    graph.relate(source_ref=fill.ticker, target_ref=ref_id, relation="episode_for_ticker", metadata={"agent_id": agent_id})
                attributed_trades += 1

            session.commit()

        return BackfillSummary(
            signal_rows_updated=updated_signal_rows,
            attributed_trades=attributed_trades,
            ic_rows=ic_rows,
        )

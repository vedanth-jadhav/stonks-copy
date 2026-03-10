from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from quant_trading.timeutils import market_date_for
from quant_trading.types import JobStatus, PortfolioSnapshot

from .models import ChargeSchedule, Fill, JobRun, Position


@dataclass(slots=True)
class OpenLot:
    ticker: str
    shares: int
    net_cost_per_share: float
    acquired_at: datetime


@dataclass(slots=True)
class PositionProjection:
    ticker: str
    shares: int
    avg_entry_price: float
    total_cost: float
    sector: str | None
    stop_loss_price: float | None
    trailing_stop_price: float | None
    position_type: str
    last_updated: datetime


@dataclass(slots=True)
class PortfolioLedger:
    cash_balance: float
    total_realized_pnl: float
    total_charges_paid: float
    positions: list[PositionProjection] = field(default_factory=list)
    realized_pnl_by_date: dict[date, float] = field(default_factory=dict)

    def shares_for_ticker(self, ticker: str) -> int:
        position = next((row for row in self.positions if row.ticker == ticker), None)
        return position.shares if position is not None else 0


def _fallback_metadata(position: Position | None) -> dict[str, object]:
    if position is None:
        return {}
    return {
        "sector": position.sector,
        "stop_loss_price": position.stop_loss_price,
        "trailing_stop_price": position.trailing_stop_price,
        "position_type": position.position_type,
        "last_updated": position.last_updated,
    }


def _update_metadata(metadata: dict[str, object], fill: Fill) -> dict[str, object]:
    details = dict(fill.details or {})
    next_metadata = dict(metadata)
    for key in ("sector", "stop_loss_price", "trailing_stop_price", "position_type"):
        if details.get(key) is not None:
            next_metadata[key] = details[key]
    next_metadata["last_updated"] = fill.created_at
    return next_metadata


def reconcile_trade_ledger(session: Session, starting_cash: float, as_of: date | None = None) -> PortfolioLedger:
    fills = session.scalars(select(Fill).order_by(Fill.created_at.asc(), Fill.id.asc())).all()
    existing_positions = {row.ticker: row for row in session.scalars(select(Position)).all()}
    cash = starting_cash
    realized = 0.0
    charges = 0.0
    lots_by_ticker: dict[str, list[OpenLot]] = {}
    metadata_by_ticker: dict[str, dict[str, object]] = {
        ticker: _fallback_metadata(position)
        for ticker, position in existing_positions.items()
    }
    realized_pnl_by_date: dict[date, float] = {}

    for fill in fills:
        fill_date = market_date_for(fill.created_at)
        if as_of is not None and fill_date > as_of:
            break

        notional = fill.fill_price * fill.shares
        charges += fill.charges
        ticker_lots = lots_by_ticker.setdefault(fill.ticker, [])
        metadata_by_ticker[fill.ticker] = _update_metadata(metadata_by_ticker.get(fill.ticker, {}), fill)

        if fill.action == "BUY":
            cash -= notional + fill.charges
            ticker_lots.append(
                OpenLot(
                    ticker=fill.ticker,
                    shares=fill.shares,
                    net_cost_per_share=(notional + fill.charges) / fill.shares,
                    acquired_at=fill.created_at,
                )
            )
            continue

        cash += notional - fill.charges
        remaining_to_sell = fill.shares
        sell_realized = 0.0
        while remaining_to_sell > 0:
            if not ticker_lots:
                raise ValueError(f"Oversold {fill.ticker}: attempted to sell {fill.shares} shares without enough open lots.")
            open_lot = ticker_lots[0]
            matched_shares = min(open_lot.shares, remaining_to_sell)
            matched_notional = fill.fill_price * matched_shares
            matched_charges = fill.charges * (matched_shares / fill.shares)
            sell_realized += matched_notional - matched_charges - (open_lot.net_cost_per_share * matched_shares)
            open_lot.shares -= matched_shares
            remaining_to_sell -= matched_shares
            if open_lot.shares == 0:
                ticker_lots.pop(0)
        realized += sell_realized
        realized_pnl_by_date[fill_date] = realized_pnl_by_date.get(fill_date, 0.0) + sell_realized

    positions: list[PositionProjection] = []
    for ticker, ticker_lots in sorted(lots_by_ticker.items()):
        if not ticker_lots:
            continue
        shares = sum(lot.shares for lot in ticker_lots)
        total_cost = sum(lot.net_cost_per_share * lot.shares for lot in ticker_lots)
        metadata = metadata_by_ticker.get(ticker, {})
        last_updated = metadata.get("last_updated")
        if not isinstance(last_updated, datetime):
            last_updated = max((lot.acquired_at for lot in ticker_lots), default=datetime.now(UTC))
        positions.append(
            PositionProjection(
                ticker=ticker,
                shares=shares,
                avg_entry_price=(total_cost / shares) if shares > 0 else 0.0,
                total_cost=total_cost,
                sector=metadata.get("sector") if isinstance(metadata.get("sector"), str) else None,
                stop_loss_price=float(metadata["stop_loss_price"]) if metadata.get("stop_loss_price") is not None else None,
                trailing_stop_price=float(metadata["trailing_stop_price"]) if metadata.get("trailing_stop_price") is not None else None,
                position_type=str(metadata.get("position_type") or "QUALITY"),
                last_updated=last_updated,
            )
        )

    return PortfolioLedger(
        cash_balance=cash,
        total_realized_pnl=realized,
        total_charges_paid=charges,
        positions=positions,
        realized_pnl_by_date=realized_pnl_by_date,
    )


def snapshot_from_ledger(ledger: PortfolioLedger, price_map: dict[str, float] | None = None) -> PortfolioSnapshot:
    total_deployed = sum(position.total_cost for position in ledger.positions)
    if price_map is None:
        market_value = total_deployed
        priced_positions = 0
        unpriced_positions = len(ledger.positions)
    else:
        market_value = 0.0
        priced_positions = 0
        unpriced_positions = 0
        for position in ledger.positions:
            price = price_map.get(position.ticker)
            if price is None:
                market_value += position.total_cost
                unpriced_positions += 1
                continue
            market_value += position.shares * price
            priced_positions += 1
    portfolio_value = ledger.cash_balance + market_value
    return PortfolioSnapshot(
        cash_balance=ledger.cash_balance,
        total_deployed=total_deployed,
        total_market_value=market_value,
        portfolio_value=portfolio_value,
        total_unrealized_pnl=market_value - total_deployed,
        total_realized_pnl=ledger.total_realized_pnl,
        total_charges_paid=ledger.total_charges_paid,
        open_positions=len(ledger.positions),
        priced_positions=priced_positions,
        unpriced_positions=unpriced_positions,
    )


def reconcile_portfolio(session: Session, starting_cash: float, price_map: dict[str, float] | None = None, as_of: date | None = None) -> PortfolioSnapshot:
    ledger = reconcile_trade_ledger(session, starting_cash=starting_cash, as_of=as_of)
    return snapshot_from_ledger(ledger, price_map=price_map)


def mark_stale_running_jobs(session: Session) -> int:
    jobs = session.scalars(select(JobRun).where(JobRun.status == JobStatus.RUNNING.value)).all()
    for job in jobs:
        job.status = JobStatus.ABORTED.value
        job.finished_at = datetime.now(UTC)
        job.error = "Recovered after process restart."
    session.commit()
    return len(jobs)


def latest_charge_schedule(session: Session, broker: str, venue: str, product: str) -> ChargeSchedule:
    stmt = (
        select(ChargeSchedule)
        .where(
            ChargeSchedule.broker == broker,
            ChargeSchedule.venue == venue,
            ChargeSchedule.product == product,
        )
        .order_by(desc(ChargeSchedule.effective_date))
        .limit(1)
    )
    schedule = session.scalar(stmt)
    if schedule is None:
        raise LookupError(f"Missing charge schedule for {broker}/{venue}/{product}")
    return schedule

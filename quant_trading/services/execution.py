from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from math import floor

from quant_trading.config import get_settings
from quant_trading.db.repository import QuantRepository
from quant_trading.execution import compute_delivery_charges, compute_entry_fill, compute_exit_fill
from quant_trading.schemas import DecisionType, MarketContext, PositionType, PriceData, SessionState, TradeDecision


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    order_id: str
    fill_id: str
    ticker: str
    action: str
    fill_price: float
    charges: float
    execution_type: str


class ExecutionService:
    def __init__(self, repository: QuantRepository) -> None:
        self.repository = repository
        self.settings = get_settings()

    def execute(self, run_id: str, context: MarketContext, decision: TradeDecision) -> ExecutionResult | None:
        if decision.decision not in {DecisionType.BUY, DecisionType.SELL}:
            return None
        if not self._within_execution_window(context, decision):
            return None

        price_data = context.price_bundle.get(decision.ticker) or PriceData(ticker=decision.ticker)
        if self._fair_value(price_data) <= 0:
            return None

        action = decision.decision.value
        execution_type = "PLANNED_DELIVERY"
        if decision.decision is DecisionType.SELL and context.session_state in {SessionState.OPEN, SessionState.POST_MARKET}:
            execution_type = "DEFENSIVE_INTRADAY"

        shares = max(decision.shares, 1)
        universe_item = next((item for item in context.universe if item.ticker == decision.ticker), None)
        market_cap_cr = universe_item.market_cap_cr if universe_item else None
        if decision.decision is DecisionType.SELL:
            available_shares = self.repository.open_shares_for_ticker(decision.ticker)
            if available_shares < shares:
                raise ValueError(f"Unable to sell {shares} shares of {decision.ticker}; only {available_shares} shares are open.")
        if decision.decision is DecisionType.BUY:
            fill_price = compute_entry_fill(price_data, market_cap_cr=market_cap_cr)
        else:
            fill_price = compute_exit_fill(
                price_data,
                market_cap_cr=market_cap_cr,
                ltp=price_data.last_price,
                defensive=execution_type == "DEFENSIVE_INTRADAY",
            )
        trade_value = fill_price * shares
        schedule = self.repository.latest_charge_schedule()
        charges = compute_delivery_charges(schedule, trade_value=trade_value, action=action).total
        order_id = self.repository.record_trade_decision(run_id=run_id, decision=decision)
        fill_id = self.repository.record_fill(
            order_id=order_id,
            run_id=run_id,
            ticker=decision.ticker,
            action=action,
            shares=shares,
            fill_price=fill_price,
            charges=charges,
            execution_type=execution_type,
            metadata={
                "target_weight": decision.target_weight,
                "sector": universe_item.sector if universe_item else None,
                "position_type": decision.position_type.value,
                "stop_loss_price": decision.stop_policy.hard_stop_price,
                "trailing_stop_price": decision.stop_policy.trailing_stop_price,
                "reason_code": decision.reason_code,
            },
        )
        self.repository.apply_fill_to_positions(
            ticker=decision.ticker,
            action=action,
            shares=shares,
            fill_price=fill_price,
            charges=charges,
            sector=universe_item.sector if universe_item else None,
            position_type=decision.position_type.value,
            stop_loss_price=decision.stop_policy.hard_stop_price,
            trailing_stop_price=decision.stop_policy.trailing_stop_price,
        )
        return ExecutionResult(
            order_id=order_id,
            fill_id=fill_id,
            ticker=decision.ticker,
            action=action,
            fill_price=fill_price,
            charges=charges,
            execution_type=execution_type,
        )

    def shares_for_target_weight(self, portfolio_value: float, target_weight: float, price_data: PriceData) -> int:
        fair_value = self._fair_value(price_data)
        if fair_value <= 0:
            return 0
        return max(floor((portfolio_value * target_weight) / fair_value), 0)

    def _fair_value(self, price_data: PriceData) -> float:
        if price_data.previous_bar is not None:
            bar = price_data.previous_bar
            return (bar.high + bar.low + bar.close) / 3
        values = [value for value in (price_data.prev_high, price_data.prev_low, price_data.prev_close) if value is not None]
        if len(values) == 3:
            return sum(values) / 3
        return price_data.last_price or 0.0

    def _within_execution_window(self, context: MarketContext, decision: TradeDecision) -> bool:
        if not context.is_market_day:
            return False

        entry_open = time.fromisoformat(self.settings.market.entry_window_open)
        entry_close = time.fromisoformat(self.settings.market.entry_window_close)
        exit_close = time.fromisoformat(self.settings.market.exit_window_close)
        valid_until = decision.entry_policy.valid_until
        action = decision.decision

        if action is DecisionType.BUY:
            if context.session_state is not SessionState.OPEN:
                return False
            if not (entry_open <= context.time_ist <= entry_close):
                return False
            if valid_until is not None and context.time_ist > valid_until:
                return False
            return True

        if action is DecisionType.SELL:
            if context.session_state not in {SessionState.OPEN, SessionState.POST_MARKET}:
                return False
            if context.time_ist > exit_close:
                return False
            if valid_until is not None and context.time_ist > valid_until:
                return False
            return True

        return False

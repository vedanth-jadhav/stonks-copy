"""
engine.py — Walk-forward backtest simulation engine.

Replays 4 OHLCV-computable agents (Momentum, Reversion, Liquidity, Sector)
day by day over a historical date range, simulating the BOSS agent's
decision logic: IC-weighted conviction, position sizing, stop-loss checks.

Usage:
    from quant_trading.backtest.engine import BacktestEngine
    from quant_trading.backtest.data_loader import DataLoader

    loader = DataLoader()
    engine = BacktestEngine(loader)
    result = engine.run("2021-01-01", "2025-12-31", initial_capital=1_000_000)
    result.print_report()
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from statistics import mean, pstdev
from typing import TYPE_CHECKING

import pandas as pd

from quant_trading.backtest.data_loader import (
    SECTOR_INDEX_MAP,
    DataLoader,
)
from quant_trading.backtest.signals import (
    _corr,
    compute_liquidity_score,
    compute_momentum_scores_cross_section,
    compute_reversion_score,
    compute_sector_multipliers,
    infer_regime,
)

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config constants (mirrors quant_trading/config.py defaults)
# ---------------------------------------------------------------------------

INITIAL_CAPITAL = 1_000_000.0
CASH_BUFFER_PCT = 0.35          # always keep 35% cash
MAX_POSITION_PCT = 0.15         # max 15% per single position
MAX_SECTOR_PCT = 0.30           # max 30% per sector
STOP_LOSS_PCT = 0.07            # hard stop 7% below entry
TRAILING_STOP_PCT = 0.07        # trailing stop 7% trail
CONVICTION_THRESHOLD = 0.45    # lowered from 0.60 (only 3 signal agents vs 9)
MIN_POSITIVE_AGENTS = 2         # at least 2 of 3 agents positive
BROKERAGE_RATE = 0.001          # 0.1% per trade (simplified)
LOOKBACK_IC = 63                # bars for IC calculation


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimPosition:
    ticker: str
    shares: int
    entry_price: float
    stop_loss_price: float
    trailing_stop_price: float
    entry_date: date
    sector: str


@dataclass
class SimTrade:
    ticker: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    holding_days: int
    exit_reason: str


@dataclass
class BacktestResult:
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    nav_series: list[tuple[date, float]]
    benchmark_series: list[tuple[date, float]]
    trades: list[SimTrade]

    # Computed metrics (populated by _compute_metrics)
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    win_rate_pct: float = 0.0
    avg_holding_days: float = 0.0
    total_trades: int = 0
    benchmark_return_pct: float = 0.0
    alpha_pct: float = 0.0

    def print_report(self) -> None:
        n500 = len(self.nav_series)
        print("\n" + "=" * 50)
        print("BACKTEST SUMMARY")
        print("=" * 50)
        print(f"Period:          {self.start_date} → {self.end_date}")
        print(f"Agents:          Momentum, Reversion, Liquidity + Sector multiplier")
        print(f"Initial Capital: ₹{self.initial_capital:,.0f}")
        print(f"Final Capital:   ₹{self.final_capital:,.0f}")
        print(f"Total Return:    {self.total_return_pct:+.1f}%")
        print(f"CAGR:            {self.cagr_pct:+.1f}%")
        print(f"Sharpe Ratio:    {self.sharpe_ratio:.2f}")
        print(f"Sortino Ratio:   {self.sortino_ratio:.2f}")
        print(f"Max Drawdown:    {self.max_drawdown_pct:.1f}%")
        print(f"Calmar Ratio:    {self.calmar_ratio:.2f}")
        print(f"Win Rate:        {self.win_rate_pct:.1f}%")
        print(f"Avg Hold (days): {self.avg_holding_days:.1f}")
        print(f"Total Trades:    {self.total_trades}")
        print(f"Benchmark Ret:   {self.benchmark_return_pct:+.1f}%  (^NSEI)")
        print(f"Alpha:           {self.alpha_pct:+.1f}%")
        print(f"Trading Days:    {n500}")
        print("=" * 50)
        print()

        if self.trades:
            print("LAST 10 TRADES")
            print("-" * 70)
            print(f"{'Ticker':<12} {'Entry':>10} {'Exit':>10} {'PnL':>10} {'Hold':>5} {'Reason'}")
            print("-" * 70)
            for t in self.trades[-10:]:
                print(
                    f"{t.ticker:<12} {str(t.entry_date):>10} {str(t.exit_date):>10}"
                    f" {t.pnl:>+9.0f} {t.holding_days:>5}  {t.exit_reason}"
                )
            print()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class BacktestEngine:
    """Walk-forward backtest engine using OHLCV-computable signals."""

    def __init__(self, loader: DataLoader) -> None:
        self._loader = loader

    def run(
        self,
        start: str,
        end: str,
        initial_capital: float = INITIAL_CAPITAL,
    ) -> BacktestResult:
        """
        Run the walk-forward backtest.

        Args:
            start: ISO date string, e.g. "2021-01-01"
            end:   ISO date string, e.g. "2025-12-31"
            initial_capital: Starting cash in INR

        Returns:
            BacktestResult with equity curve and metrics.
        """
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)

        log.info("Loading universe…")
        universe = self._loader.universe(start=start, end=end)
        if not universe:
            raise RuntimeError("Universe is empty — run `download` first.")
        log.info("Universe: %d tickers", len(universe))

        # Load all price data into memory (sliced to [start, end])
        price_map: dict[str, pd.DataFrame] = {}
        for item in universe:
            df = self._loader.prices(item["yf_ticker"])
            if df is not None:
                price_map[item["symbol"]] = df.loc[start:end]

        # Load reference data
        nifty_full = self._loader.prices("^NSEI")
        vix_full = self._loader.prices("^INDIAVIX")
        if nifty_full is None:
            raise RuntimeError("^NSEI data missing — run `download` first.")
        nifty = nifty_full.loc[start:end]
        vix = vix_full.loc[start:end] if vix_full is not None else pd.DataFrame()

        # Load sector ETF data
        sector_price_map: dict[str, pd.DataFrame] = {}
        for etf in set(SECTOR_INDEX_MAP.values()):
            df = self._loader.prices(etf)
            if df is not None:
                sector_price_map[etf] = df.loc[start:end]

        # Determine trading days (from Nifty calendar)
        trading_days = [d.date() for d in nifty.index]
        log.info("Trading days: %d", len(trading_days))

        # State
        cash = initial_capital
        positions: dict[str, SimPosition] = {}
        nav_series: list[tuple[date, float]] = []
        benchmark_series: list[tuple[date, float]] = []
        trades: list[SimTrade] = []

        # IC history for adaptive weighting: {agent: [(score, fwd_5d_return), ...]}
        ic_history: dict[str, list[tuple[float, float]]] = {
            "momentum": [], "reversion": [], "liquidity": []
        }

        # Main loop
        for day_idx, today in enumerate(trading_days):
            today_str = today.isoformat()

            # Slice historical data up to (and including) today for each ticker
            today_prices: dict[str, pd.DataFrame] = {
                sym: df.loc[:today_str] for sym, df in price_map.items()
            }
            today_nifty = nifty.loc[:today_str]
            today_vix_df = vix.loc[:today_str] if not vix.empty else pd.DataFrame()

            vix_close = 18.0
            if not today_vix_df.empty:
                vix_close = float(today_vix_df["Close"].iloc[-1])
            regime = infer_regime(vix_close)

            # ---------------------------------------------------------------
            # 1. Compute signals (no lookahead — uses data up to today)
            # ---------------------------------------------------------------
            sector_mults = compute_sector_multipliers(
                {etf: df.loc[:today_str] for etf, df in sector_price_map.items()},
                SECTOR_INDEX_MAP,
            )

            mom_scores = compute_momentum_scores_cross_section(
                list(today_prices.keys()),
                today_prices,
                today_nifty,
                vix_close,
                regime,
            )

            rev_scores: dict[str, float] = {}
            liq_scores: dict[str, float] = {}
            for sym, df in today_prices.items():
                rev_scores[sym] = compute_reversion_score(df)
                liq_scores[sym] = compute_liquidity_score(df)

            # ---------------------------------------------------------------
            # 2. Compute IC weights (after 63 days of signal history)
            # ---------------------------------------------------------------
            ic_weights = self._compute_ic_weights(ic_history)

            # ---------------------------------------------------------------
            # 3. Stop checks for existing positions (before new entries)
            # ---------------------------------------------------------------
            cash, positions, new_trades = self._check_stops(
                today, today_prices, positions, cash, mom_scores, rev_scores, liq_scores, sector_mults, ic_weights
            )
            trades.extend(new_trades)

            # ---------------------------------------------------------------
            # 4. Entry decisions
            # ---------------------------------------------------------------
            if day_idx + 1 < len(trading_days):
                next_day = trading_days[day_idx + 1]
                next_day_str = next_day.isoformat()
                portfolio_value = self._nav(cash, positions, today_prices)

                cash, positions, new_trades = self._process_entries(
                    today,
                    next_day_str,
                    today_prices,
                    price_map,
                    universe,
                    positions,
                    cash,
                    portfolio_value,
                    mom_scores,
                    rev_scores,
                    liq_scores,
                    sector_mults,
                    ic_weights,
                )
                trades.extend(new_trades)

            # ---------------------------------------------------------------
            # 5. EOD NAV
            # ---------------------------------------------------------------
            portfolio_value = self._nav(cash, positions, today_prices)
            nav_series.append((today, portfolio_value))

            nifty_close = float(today_nifty["Close"].iloc[-1]) if not today_nifty.empty else 0.0
            benchmark_series.append((today, nifty_close))

            # ---------------------------------------------------------------
            # 6. Update IC history: pair each signal with its realised 5-day
            #    forward return.  On day t we know what price was t-5 days ago,
            #    so we retrospectively attach the fwd return to the score that
            #    was recorded 5 trading days earlier.
            # ---------------------------------------------------------------
            if day_idx >= 5:
                past_day = trading_days[day_idx - 5]
                past_day_str = past_day.isoformat()
                past_prices = {sym: df.loc[:past_day_str] for sym, df in price_map.items()}
                past_mom = compute_momentum_scores_cross_section(
                    list(past_prices.keys()), past_prices, nifty.loc[:past_day_str], 18.0
                )
                for sym, df in price_map.items():
                    df_past = df.loc[:past_day_str]
                    df_now = df.loc[:today_str]
                    if df_past.empty or df_now.empty:
                        continue
                    fwd_5d = (
                        float(df_now["Close"].iloc[-1]) / float(df_past["Close"].iloc[-1])
                    ) - 1.0
                    if sym in past_mom:
                        ic_history["momentum"].append((past_mom[sym], fwd_5d))
                    past_rev = compute_reversion_score(df_past)
                    ic_history["reversion"].append((past_rev, fwd_5d))
                    past_liq = compute_liquidity_score(df_past)
                    ic_history["liquidity"].append((past_liq, fwd_5d))

        # ---------------------------------------------------------------
        # Flatten remaining positions at end of period
        # ---------------------------------------------------------------
        last_day = trading_days[-1] if trading_days else end_d
        last_prices = {sym: df for sym, df in price_map.items()}
        cash, positions, final_trades = self._liquidate_all(last_day, last_prices, positions, cash)
        trades.extend(final_trades)

        # Final capital = cash after liquidation (all positions closed)
        final_capital = cash

        result = BacktestResult(
            start_date=start_d,
            end_date=end_d,
            initial_capital=initial_capital,
            final_capital=final_capital,
            nav_series=nav_series,
            benchmark_series=benchmark_series,
            trades=trades,
        )
        _compute_metrics(result)
        return result

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _nav(
        self,
        cash: float,
        positions: dict[str, SimPosition],
        today_prices: dict[str, pd.DataFrame],
    ) -> float:
        position_value = 0.0
        for sym, pos in positions.items():
            df = today_prices.get(sym)
            if df is not None and not df.empty:
                position_value += pos.shares * float(df["Close"].iloc[-1])
            else:
                position_value += pos.shares * pos.entry_price
        return cash + position_value

    def _compute_ic_weights(
        self,
        ic_history: dict[str, list[tuple[float, float]]],
    ) -> dict[str, float]:
        """Compute Pearson IC per agent from accumulated (score, fwd_return) pairs."""
        weights: dict[str, float] = {}
        total = 0.0
        for agent, pairs in ic_history.items():
            if len(pairs) < LOOKBACK_IC:
                weights[agent] = 1.0  # equal weight fallback
                total += 1.0
                continue
            recent = pairs[-LOOKBACK_IC:]
            scores = [p[0] for p in recent]
            rets = [p[1] for p in recent]
            ic = _corr(scores, rets)
            w = max(0.0, ic)  # only use positive IC agents
            weights[agent] = w
            total += w

        if total == 0:
            n = len(ic_history)
            return {k: 1.0 / n for k in ic_history}
        return {k: v / total for k, v in weights.items()}

    def _conviction(
        self,
        ticker: str,
        mom: dict[str, float],
        rev: dict[str, float],
        liq: dict[str, float],
        sector_mults: dict[str, float],
        sector: str,
        ic_weights: dict[str, float],
    ) -> float:
        m = mom.get(ticker, 0.0)
        r = rev.get(ticker, 0.0)
        lq = liq.get(ticker, 0.0)
        wm = ic_weights.get("momentum", 1.0 / 3)
        wr = ic_weights.get("reversion", 1.0 / 3)
        wl = ic_weights.get("liquidity", 1.0 / 3)
        raw = (wm * m + wr * r + wl * lq) / max(abs(wm) + abs(wr) + abs(wl), 1e-9)
        mult = sector_mults.get(sector, 1.0)
        return raw * mult

    def _check_stops(
        self,
        today: date,
        today_prices: dict[str, pd.DataFrame],
        positions: dict[str, SimPosition],
        cash: float,
        mom: dict[str, float],
        rev: dict[str, float],
        liq: dict[str, float],
        sector_mults: dict[str, float],
        ic_weights: dict[str, float],
    ) -> tuple[float, dict[str, SimPosition], list[SimTrade]]:
        exits: list[str] = []
        exit_prices: dict[str, tuple[float, str]] = {}

        for sym, pos in positions.items():
            df = today_prices.get(sym)
            if df is None or df.empty:
                continue
            today_low = float(df["Low"].iloc[-1])
            today_close = float(df["Close"].iloc[-1])

            if today_low <= pos.stop_loss_price:
                exit_prices[sym] = (pos.stop_loss_price, "hard_stop")
                exits.append(sym)
            elif today_low <= pos.trailing_stop_price:
                exit_prices[sym] = (pos.trailing_stop_price, "trailing_stop")
                exits.append(sym)
            else:
                # Conviction exit (uses real sector_mults, not empty dict)
                conviction = self._conviction(sym, mom, rev, liq, sector_mults, pos.sector, ic_weights)
                if conviction < 0:
                    exit_prices[sym] = (today_close, "conviction_negative")
                    exits.append(sym)
                else:
                    # Update trailing stop
                    new_trail = max(pos.trailing_stop_price, today_close * (1 - TRAILING_STOP_PCT))
                    positions = {
                        **positions,
                        sym: SimPosition(
                            ticker=pos.ticker,
                            shares=pos.shares,
                            entry_price=pos.entry_price,
                            stop_loss_price=pos.stop_loss_price,
                            trailing_stop_price=new_trail,
                            entry_date=pos.entry_date,
                            sector=pos.sector,
                        ),
                    }

        new_trades: list[SimTrade] = []
        for sym in exits:
            pos = positions[sym]
            exit_price, reason = exit_prices[sym]
            gross = pos.shares * exit_price
            fee = gross * BROKERAGE_RATE
            cash += gross - fee
            pnl = (pos.shares * exit_price) - (pos.shares * pos.entry_price) - fee
            trade = SimTrade(
                ticker=sym,
                entry_date=pos.entry_date,
                exit_date=today,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                shares=pos.shares,
                pnl=pnl,
                holding_days=(today - pos.entry_date).days,
                exit_reason=reason,
            )
            new_trades.append(trade)
            positions = {k: v for k, v in positions.items() if k != sym}

        return cash, positions, new_trades

    def _process_entries(
        self,
        today: date,
        next_day_str: str,
        today_prices: dict[str, pd.DataFrame],
        price_map: dict[str, pd.DataFrame],
        universe: list[dict],
        positions: dict[str, SimPosition],
        cash: float,
        portfolio_value: float,
        mom: dict[str, float],
        rev: dict[str, float],
        liq: dict[str, float],
        sector_mults: dict[str, float],
        ic_weights: dict[str, float],
    ) -> tuple[float, dict[str, SimPosition], list[SimTrade]]:
        deployable = portfolio_value * (1 - CASH_BUFFER_PCT) - (portfolio_value - cash)
        if deployable <= 0:
            return cash, positions, []

        candidates: list[tuple[float, dict]] = []
        for item in universe:
            sym = item["symbol"]
            if sym in positions:
                continue
            sector = item.get("sector", "")
            conviction = self._conviction(sym, mom, rev, liq, sector_mults, sector, ic_weights)
            if conviction < CONVICTION_THRESHOLD:
                continue

            # Check min positive agents
            positive_count = sum(
                1
                for score in [mom.get(sym, 0.0), rev.get(sym, 0.0), liq.get(sym, 0.0)]
                if score > 0
            )
            if positive_count < MIN_POSITIVE_AGENTS:
                continue

            candidates.append((conviction, item))

        # Sort by conviction descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        new_trades: list[SimTrade] = []
        sector_exposure: dict[str, float] = {}
        for _, pos in positions.items():
            df = today_prices.get(pos.ticker)
            val = pos.shares * float(df["Close"].iloc[-1]) if df is not None and not df.empty else 0.0
            sector_exposure[pos.sector] = sector_exposure.get(pos.sector, 0.0) + val

        for conviction, item in candidates:
            if deployable <= 0:
                break
            sym = item["symbol"]
            sector = item.get("sector", "")
            adv_cr = item.get("adv_cr", 100.0)

            # Position size
            kelly_frac = _half_kelly(win_rate=0.55, avg_rr=1.5)
            liq_cap = min(MAX_POSITION_PCT, (adv_cr / 1000) * 0.02)
            size_pct = min(kelly_frac, liq_cap, MAX_POSITION_PCT)

            # Sector exposure cap
            sector_val = sector_exposure.get(sector, 0.0)
            if sector_val / portfolio_value >= MAX_SECTOR_PCT:
                continue

            target_value = min(portfolio_value * size_pct, deployable)
            if target_value < 1000:
                continue

            # Fill at next-day open
            next_df = price_map.get(sym)
            if next_df is None:
                continue
            try:
                next_open_row = next_df.loc[next_day_str:]
                if next_open_row.empty:
                    continue
                fill_price = float(next_open_row["Open"].iloc[0])
            except (KeyError, IndexError):
                continue

            if fill_price <= 0:
                continue

            shares = int(target_value / fill_price)
            if shares <= 0:
                continue

            actual_cost = shares * fill_price
            fee = actual_cost * BROKERAGE_RATE
            total_cost = actual_cost + fee
            if total_cost > cash:
                continue

            cash -= total_cost
            deployable -= total_cost
            sector_exposure[sector] = sector_exposure.get(sector, 0.0) + actual_cost

            new_position = SimPosition(
                ticker=sym,
                shares=shares,
                entry_price=fill_price,
                stop_loss_price=fill_price * (1 - STOP_LOSS_PCT),
                trailing_stop_price=fill_price * (1 - TRAILING_STOP_PCT),
                entry_date=today,
                sector=sector,
            )
            positions = {**positions, sym: new_position}
            # Record the buy as an open trade (exit fields filled at close)
            new_trades.append(
                SimTrade(
                    ticker=sym,
                    entry_date=today,
                    exit_date=today,        # placeholder; overwritten at exit
                    entry_price=fill_price,
                    exit_price=fill_price,  # placeholder
                    shares=shares,
                    pnl=0.0,                # placeholder
                    holding_days=0,
                    exit_reason="open",
                )
            )

        return cash, positions, new_trades

    def _liquidate_all(
        self,
        today: date,
        price_map: dict[str, pd.DataFrame],
        positions: dict[str, SimPosition],
        cash: float,
    ) -> tuple[float, dict[str, SimPosition], list[SimTrade]]:
        trades: list[SimTrade] = []
        for sym, pos in list(positions.items()):
            df = price_map.get(sym)
            exit_price = pos.entry_price
            if df is not None and not df.empty:
                exit_price = float(df["Close"].iloc[-1])
            gross = pos.shares * exit_price
            fee = gross * BROKERAGE_RATE
            cash += gross - fee
            pnl = (pos.shares * exit_price) - (pos.shares * pos.entry_price) - fee
            trades.append(
                SimTrade(
                    ticker=sym,
                    entry_date=pos.entry_date,
                    exit_date=today,
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    shares=pos.shares,
                    pnl=pnl,
                    holding_days=(today - pos.entry_date).days,
                    exit_reason="end_of_period",
                )
            )
        return cash, {}, trades


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _compute_metrics(result: BacktestResult) -> None:
    if len(result.nav_series) < 2:
        return

    navs = [v for _, v in result.nav_series]
    benchmarks = [v for _, v in result.benchmark_series]

    daily_returns = [(navs[i] / navs[i - 1]) - 1 for i in range(1, len(navs))]

    # Sharpe
    if len(daily_returns) >= 2:
        avg_ret = mean(daily_returns)
        std_ret = pstdev(daily_returns)
        result.sharpe_ratio = round((avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0.0, 3)

        neg_rets = [r for r in daily_returns if r < 0]
        std_neg = pstdev(neg_rets) if len(neg_rets) > 1 else 0.0
        result.sortino_ratio = round((avg_ret / std_neg * math.sqrt(252)) if std_neg > 0 else 0.0, 3)

    # Max drawdown
    peak = navs[0]
    max_dd = 0.0
    for v in navs:
        peak = max(peak, v)
        dd = (v - peak) / peak
        max_dd = min(max_dd, dd)
    result.max_drawdown_pct = round(max_dd * 100, 2)

    # CAGR
    n_days = len(navs)
    total_ret = (navs[-1] / navs[0]) - 1
    cagr = (navs[-1] / navs[0]) ** (252 / max(n_days, 1)) - 1
    result.total_return_pct = round(total_ret * 100, 2)
    result.cagr_pct = round(cagr * 100, 2)
    result.final_capital = navs[-1]

    # Calmar
    result.calmar_ratio = round(
        result.cagr_pct / abs(result.max_drawdown_pct) if result.max_drawdown_pct != 0 else 0.0, 3
    )

    # Trade stats
    result.total_trades = len(result.trades)
    if result.trades:
        result.win_rate_pct = round(
            sum(1 for t in result.trades if t.pnl > 0) / len(result.trades) * 100, 1
        )
        result.avg_holding_days = round(mean(t.holding_days for t in result.trades), 1)

    # Benchmark
    if len(benchmarks) >= 2 and benchmarks[0] > 0:
        bench_ret = (benchmarks[-1] / benchmarks[0]) - 1
        result.benchmark_return_pct = round(bench_ret * 100, 2)
        result.alpha_pct = round(result.total_return_pct - result.benchmark_return_pct, 2)


def _half_kelly(win_rate: float, avg_rr: float) -> float:
    """Half-Kelly fraction for position sizing."""
    kelly = ((win_rate * avg_rr) - (1 - win_rate)) / max(avg_rr, 1e-9)
    return max(0.01, min(MAX_POSITION_PCT, kelly / 2))
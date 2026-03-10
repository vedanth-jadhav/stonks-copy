"""
cli.py — Command-line interface for the standalone backtest.

Usage:
    # Step 1: Download historical data (run once)
    python -m quant_trading.backtest.cli download --start 2020-01-01 --end 2025-12-31

    # Step 2: Run the backtest
    python -m quant_trading.backtest.cli run --start 2021-01-01 --end 2025-12-31

    # Options:
    python -m quant_trading.backtest.cli run --start 2021-01-01 --end 2025-12-31 \\
        --capital 1000000 \\
        --cache-dir data/backtest_cache \\
        --output backtest_result.json

    # Quick smoke test (1 year, faster):
    python -m quant_trading.backtest.cli run --start 2024-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def _cmd_download(args: argparse.Namespace) -> None:
    from quant_trading.backtest.data_loader import DataLoader

    loader = DataLoader(cache_dir=args.cache_dir)
    print(f"Downloading Nifty 500 data ({args.start} → {args.end})…")
    print(f"Cache directory: {args.cache_dir}")
    print("This may take 10–30 minutes on first run (500+ tickers).\n")
    loader.download(start=args.start, end=args.end)
    cache = Path(args.cache_dir)
    files = list(cache.glob("*.pkl"))
    print(f"\nDownload complete. {len(files)} cache files saved to {cache}.")


def _cmd_run(args: argparse.Namespace) -> None:
    from quant_trading.backtest.data_loader import DataLoader
    from quant_trading.backtest.engine import BacktestEngine

    loader = DataLoader(cache_dir=args.cache_dir)
    engine = BacktestEngine(loader)

    print(f"\nRunning backtest: {args.start} → {args.end}")
    print(f"Initial capital: ₹{args.capital:,.0f}")
    print("Computing signals day by day (walk-forward, no lookahead)…\n")

    result = engine.run(
        start=args.start,
        end=args.end,
        initial_capital=float(args.capital),
    )
    result.print_report()

    if args.output:
        out_path = Path(args.output)
        summary = {
            "start_date": str(result.start_date),
            "end_date": str(result.end_date),
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_return_pct": result.total_return_pct,
            "cagr_pct": result.cagr_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "max_drawdown_pct": result.max_drawdown_pct,
            "calmar_ratio": result.calmar_ratio,
            "win_rate_pct": result.win_rate_pct,
            "avg_holding_days": result.avg_holding_days,
            "total_trades": result.total_trades,
            "benchmark_return_pct": result.benchmark_return_pct,
            "alpha_pct": result.alpha_pct,
            "nav_series": [[str(d), v] for d, v in result.nav_series],
            "benchmark_series": [[str(d), v] for d, v in result.benchmark_series],
        }
        out_path.write_text(json.dumps(summary, indent=2))
        print(f"Results saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Standalone historical backtest for the stonks trading system."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # download subcommand
    dl = sub.add_parser("download", help="Download Nifty 500 OHLCV data from yfinance")
    dl.add_argument("--start", default="2020-01-01", help="Start date (YYYY-MM-DD)")
    dl.add_argument("--end", default="2025-12-31", help="End date (YYYY-MM-DD)")
    dl.add_argument("--cache-dir", default="data/backtest_cache", help="Local cache directory")

    # run subcommand
    run = sub.add_parser("run", help="Run the walk-forward backtest")
    run.add_argument("--start", required=True, help="Backtest start date (YYYY-MM-DD)")
    run.add_argument("--end", required=True, help="Backtest end date (YYYY-MM-DD)")
    run.add_argument("--capital", type=float, default=1_000_000, help="Initial capital in INR")
    run.add_argument("--cache-dir", default="data/backtest_cache", help="Local cache directory")
    run.add_argument("--output", default=None, help="Path to save JSON results (optional)")

    args = parser.parse_args()

    if args.command == "download":
        _cmd_download(args)
    elif args.command == "run":
        _cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
data_loader.py — Download and cache historical OHLCV data for the backtest.

Usage:
    from quant_trading.backtest.data_loader import DataLoader
    loader = DataLoader()
    loader.download(start="2020-01-01", end="2025-12-31")
    tickers = loader.universe()
    prices = loader.prices("RELIANCE")  # returns pd.DataFrame with OHLCV
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pickle

import pandas as pd
import requests
import yfinance as yf

log = logging.getLogger(__name__)

# NSE archives: current Nifty 500 constituents
_NSE_NIFTY500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"

# Sector index ETF tickers available on yfinance
SECTOR_TICKERS = [
    "^CNXIT",
    "^NSEBANK",
    "^CNXFMCG",
    "^CNXPHARMA",
    "^CNXAUTO",
    "^CNXENERGY",
    "^CNXCAPGOODS",
    "^CNXMETAL",
    "^CNXREALTY",
    "^CNXINFRA",
    "^CNXMEDIA",
    "^CNXCHEM",
]

BENCHMARK_TICKER = "^NSEI"
VIX_TICKER = "^INDIAVIX"

# Sector label -> sector index ETF ticker (exact mirror of SECTOR_INDEX_MAP in agents/core.py)
SECTOR_INDEX_MAP: dict[str, str] = {
    "IT": "^CNXIT",
    "Banking": "^NSEBANK",
    "Bank": "^NSEBANK",
    "FMCG": "^CNXFMCG",
    "Pharma": "^CNXPHARMA",
    "Auto": "^CNXAUTO",
    "Energy": "^CNXENERGY",
    "Capital Goods": "^CNXCAPGOODS",
    "Metals": "^CNXMETAL",
    "Realty": "^CNXREALTY",
    "Infrastructure": "^CNXINFRA",
    "Media": "^CNXMEDIA",
    "Chemicals": "^CNXCHEM",
}

# Static sector mapping for common Nifty 500 tickers (NSE symbol -> sector label)
# Sourced from NSE industry classification. Covers ~150 large/mid cap stocks.
TICKER_SECTOR_MAP: dict[str, str] = {
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "SBIN": "Banking",
    "BANKBARODA": "Banking",
    "PNB": "Banking",
    "CANBK": "Banking",
    "FEDERALBNK": "Banking",
    "IDFCFIRSTB": "Banking",
    "INDUSINDBK": "Banking",
    "BANDHANBNK": "Banking",
    "AUBANK": "Banking",
    "CITYUNIONBK": "Banking",
    "HDFCLIFE": "Financial Services",
    "SBILIFE": "Financial Services",
    "ICICIGI": "Financial Services",
    "BAJFINANCE": "Financial Services",
    "BAJAJFINSV": "Financial Services",
    "CHOLAFIN": "Financial Services",
    "MUTHOOTFIN": "Financial Services",
    "PFC": "Financial Services",
    "RECLTD": "Financial Services",
    "SHRIRAMFIN": "Financial Services",
    "TCS": "IT",
    "INFY": "IT",
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "LTIM": "IT",
    "MPHASIS": "IT",
    "PERSISTENT": "IT",
    "COFORGE": "IT",
    "OFSS": "IT",
    "RELIANCE": "Energy",
    "BPCL": "Energy",
    "ONGC": "Energy",
    "IOC": "Energy",
    "GAIL": "Energy",
    "NTPC": "Energy",
    "POWERGRID": "Energy",
    "TATAPOWER": "Energy",
    "ADANIGREEN": "Energy",
    "ADANIPORTS": "Infrastructure",
    "LARSEN": "Capital Goods",
    "BHEL": "Capital Goods",
    "ABB": "Capital Goods",
    "SIEMENS": "Capital Goods",
    "HAVELLS": "Capital Goods",
    "CGPOWER": "Capital Goods",
    "HINDUNILVR": "FMCG",
    "ITC": "FMCG",
    "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG",
    "DABUR": "FMCG",
    "MARICO": "FMCG",
    "COLPAL": "FMCG",
    "GODREJCP": "FMCG",
    "EMAMILTD": "FMCG",
    "TATACONSUM": "FMCG",
    "SUNPHARMA": "Pharma",
    "DRREDDY": "Pharma",
    "CIPLA": "Pharma",
    "DIVISLAB": "Pharma",
    "BIOCON": "Pharma",
    "AUROPHARMA": "Pharma",
    "TORNTPHARM": "Pharma",
    "LUPIN": "Pharma",
    "ALKEM": "Pharma",
    "IPCALAB": "Pharma",
    "MARUTI": "Auto",
    "TATAMOTORS": "Auto",
    "M&M": "Auto",
    "BAJAJ-AUTO": "Auto",
    "HEROMOTOCO": "Auto",
    "EICHERMOT": "Auto",
    "ASHOKLEY": "Auto",
    "ESCORTS": "Auto",
    "BALKRISIND": "Auto",
    "BOSCHLTD": "Auto",
    "TATASTEEL": "Metals",
    "JSWSTEEL": "Metals",
    "HINDALCO": "Metals",
    "VEDL": "Metals",
    "COALINDIA": "Metals",
    "NMDC": "Metals",
    "SAIL": "Metals",
    "NATIONALUM": "Metals",
    "HINDCOPPER": "Metals",
    "BHARTIARTL": "Media",   # Telecom — closest available index is Media
    "DLF": "Realty",
    "GODREJPROP": "Realty",
    "PRESTIGE": "Realty",
    "BRIGADE": "Realty",
    "PHOENIXLTD": "Realty",
    "ASIANPAINT": "Chemicals",
    "BERGER": "Chemicals",
    "PIDILITIND": "Chemicals",
    "TITAN": "Capital Goods",
    "AMBUJACEM": "Infrastructure",
    "ACC": "Infrastructure",
    "SHREECEM": "Infrastructure",
    "APOLLOHOSP": "Pharma",
    "MAXHEALTH": "Pharma",
    "FORTIS": "Pharma",
    "TITAN": "Capital Goods",
    "VOLTAS": "Capital Goods",
    "WHIRLPOOL": "Capital Goods",
    "ZOMATO": "Financial Services",
    "NYKAA": "Financial Services",
    "DMART": "FMCG",
    "TRENT": "FMCG",
}


class DataLoader:
    """Downloads and caches Nifty 500 OHLCV data for backtesting."""

    def __init__(self, cache_dir: str | Path = "data/backtest_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ticker_list: list[dict] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, start: str = "2020-01-01", end: str = "2025-12-31") -> None:
        """Download Nifty 500 list + OHLCV for all tickers. Saves as parquet."""
        tickers_meta = self._fetch_nifty500_list()
        all_tickers = (
            [f"{m['symbol']}.NS" for m in tickers_meta]
            + SECTOR_TICKERS
            + [BENCHMARK_TICKER, VIX_TICKER]
        )
        log.info("Downloading %d tickers (%s → %s)…", len(all_tickers), start, end)
        self._download_batch(all_tickers, start, end)
        # Save the metadata (symbol + industry) for universe filtering
        meta_path = self.cache_dir / "nifty500_meta.pkl"
        with open(meta_path, "wb") as f:
            pickle.dump(tickers_meta, f)
        log.info("Saved Nifty 500 metadata → %s", meta_path)

    def universe(
        self,
        start: str,
        end: str,
        min_adv_cr: float = 50.0,
        min_bars: int = 252,
    ) -> list[dict]:
        """
        Return filtered universe of tickers that have sufficient data.

        Each entry: {"symbol": str, "yf_ticker": str, "sector": str, "industry": str}
        """
        meta = self._load_meta()
        result: list[dict] = []
        for row in meta:
            symbol: str = row["symbol"]
            yf_ticker = f"{symbol}.NS"
            df = self._load_parquet(yf_ticker)
            if df is None:
                continue
            # Apply date filter
            df = df.loc[start:end]
            if len(df) < min_bars:
                continue
            # ADV filter: median 20-day ADV in crores
            adv = self._median_adv_cr(df)
            if adv < min_adv_cr:
                continue
            sector = TICKER_SECTOR_MAP.get(symbol, row.get("industry", ""))
            result.append(
                {
                    "symbol": symbol,
                    "yf_ticker": yf_ticker,
                    "sector": sector,
                    "industry": row.get("industry", ""),
                    "adv_cr": round(adv, 2),
                }
            )
        log.info("Universe: %d tickers after filters", len(result))
        return result

    def prices(self, symbol_or_ticker: str) -> pd.DataFrame | None:
        """
        Load cached OHLCV DataFrame for a ticker.

        Accepts bare NSE symbol ("RELIANCE") or full yfinance ticker ("RELIANCE.NS" / "^NSEI").
        Columns: Open, High, Low, Close, Volume
        Index: DatetimeIndex
        """
        if symbol_or_ticker.startswith("^"):
            key = symbol_or_ticker
        elif symbol_or_ticker.endswith(".NS"):
            key = symbol_or_ticker
        else:
            key = f"{symbol_or_ticker}.NS"
        return self._load_parquet(key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_nifty500_list(self) -> list[dict]:
        """Download Nifty 500 CSV from NSE archives. Returns list of {symbol, company, industry}."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; backtest-engine/1.0)",
            "Referer": "https://www.nseindia.com/",
        }
        resp = requests.get(_NSE_NIFTY500_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        # NSE CSV columns: Company Name, Industry, Symbol, Series, ISIN Code
        result = []
        for _, row in df.iterrows():
            symbol = str(row.get("Symbol", "")).strip()
            company = str(row.get("Company Name", "")).strip()
            industry = str(row.get("Industry", "")).strip()
            if symbol:
                result.append({"symbol": symbol, "company": company, "industry": industry})
        log.info("Fetched %d Nifty 500 tickers from NSE archives", len(result))
        return result

    def _download_batch(self, tickers: list[str], start: str, end: str) -> None:
        """Download OHLCV for each ticker and save as parquet. Skips already-cached."""
        for ticker in tickers:
            path = self._parquet_path(ticker)
            if path.exists():
                log.debug("Cache hit: %s", ticker)
                continue
            try:
                df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
                if df.empty:
                    log.warning("No data for %s — skipping", ticker)
                    continue
                # Flatten MultiIndex columns if present (yfinance v0.2+)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.index = pd.to_datetime(df.index)
                with open(path, "wb") as f:
                    pickle.dump(df, f)
                log.debug("Saved %s (%d rows)", ticker, len(df))
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to download %s: %s", ticker, exc)

    def _load_parquet(self, ticker: str) -> pd.DataFrame | None:
        path = self._parquet_path(ticker)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                df: pd.DataFrame = pickle.load(f)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to read cache for %s: %s", ticker, exc)
            return None

    def _load_meta(self) -> list[dict]:
        meta_path = self.cache_dir / "nifty500_meta.pkl"
        if not meta_path.exists():
            raise FileNotFoundError(
                "Nifty 500 metadata not found. Run `download` first."
            )
        with open(meta_path, "rb") as f:
            return pickle.load(f)

    def _parquet_path(self, ticker: str) -> Path:
        safe = ticker.replace("^", "IDX_").replace(".", "_")
        return self.cache_dir / f"{safe}.pkl"

    @staticmethod
    def _median_adv_cr(df: pd.DataFrame) -> float:
        """Compute median 20-day ADV in crores from OHLCV DataFrame."""
        notional = df["Close"] * df["Volume"]
        adv = notional.rolling(20).mean().dropna()
        if adv.empty:
            return 0.0
        return float(adv.median()) / 1e7

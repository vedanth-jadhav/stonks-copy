from __future__ import annotations

from dataclasses import dataclass
import math
import re
from datetime import date, datetime, time
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from quant_trading.config import Settings
from quant_trading.db.repository import QuantRepository
from quant_trading.services.pairs import DEFAULT_PAIR_CANDIDATES, load_active_pair_rows, load_active_pairs
from quant_trading.schemas import (
    AgentID,
    DecisionType,
    EntryPolicy,
    MarketContext,
    PositionType,
    PriceBar,
    PriceData,
    StopPolicy,
    TradeDecision,
    UniverseDiscoveryPlan,
    UniverseItem,
)
from quant_trading.services.risk import compute_risk_metrics
from quant_trading.tools.cliproxy import CLIProxyGateway
from quant_trading.tools.exa_client import ExaClient
from quant_trading.tools.nse_client import NSEClient
from quant_trading.tools.rss_client import RSSClient
from quant_trading.tools.screener_client import ScreenerClient
from quant_trading.tools.yfinance_client import YFinanceClient

from .base import BaseAgent

SECTOR_INDEX_MAP = {
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

UNIVERSE_SCREENER_FIELDS = ",".join(
    [
        "top_ratios",
        "tables",
        "market_cap",
        "market_cap_cr",
        "adv_20d_cr",
        "de_ratio",
        "promoter_pledging",
        "promoter_holding",
        "operating_cash_flow",
        "cash_flow",
        "sector",
    ]
)

QUALITY_SCREENER_FIELDS = ",".join(
    [
        "top_ratios",
        "tables",
        "investors",
        "roa",
        "cfo",
        "gross_margin",
        "asset_turnover",
        "current_ratio",
        "de_ratio",
        "ebit",
        "enterprise_value",
        "net_fixed_assets",
        "working_capital",
        "promoter_holding",
        "promoter_holding_prev",
        "promoter_pledging",
        "fii_holding",
        "fii_holding_q1",
        "fii_holding_q2",
        "dii_holding",
        "dii_holding_q1",
        "dii_holding_q2",
    ]
)

OWNERSHIP_SCREENER_FIELDS = ",".join(
    [
        "top_ratios",
        "tables",
        "investors",
        "promoter_holding",
        "promoter_holding_prev",
        "promoter_pledging",
        "fii_holding",
        "fii_holding_prev",
        "dii_holding",
        "dii_holding_prev",
    ]
)

AUTONOMOUS_DISCOVERY_PROFILES: dict[str, tuple[int, int]] = {
    "tight": (1_000, 15_000),
    "standard": (750, 30_000),
    "broad": (500, 50_000),
}


def _discovery_query(profile: str) -> str:
    lower, upper = AUTONOMOUS_DISCOVERY_PROFILES[profile]
    return f"market_cap >= {lower} AND market_cap <= {upper}"


def _discovery_ladder(profile: str) -> tuple[list[str], list[str]]:
    order = ["tight", "standard", "broad"]
    start = order.index(profile)
    profiles = order[start:]
    return profiles, [_discovery_query(item) for item in profiles]


def _default_discovery_plan() -> UniverseDiscoveryPlan:
    profiles, queries = _discovery_ladder("standard")
    return UniverseDiscoveryPlan(
        status="selected",
        market_regime="neutral",
        selected_profile="standard",
        profile_ladder=profiles,
        query_ladder=queries,
    )


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    lower = text.lower()
    multiplier = 1.0
    for suffix, factor in {"cr": 1.0, "lac": 0.01, "crore": 1.0}.items():
        if lower.endswith(suffix):
            lower = lower[: -len(suffix)].strip()
            multiplier = factor
            break
    try:
        return float(lower) * multiplier
    except ValueError:
        return None


def _normalize_metric_key(value: Any) -> str:
    return "".join(char.lower() for char in str(value) if char.isalnum())


def _collect_numeric_values(payload: Any, aliases: set[str], output: list[float]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = _normalize_metric_key(key)
            if normalized in aliases:
                if isinstance(value, list):
                    for item in value:
                        numeric = _safe_float(item if not isinstance(item, dict) else item.get("value") or item.get("amount"))
                        if numeric is not None:
                            output.append(numeric)
                else:
                    numeric = _safe_float(value if not isinstance(value, dict) else value.get("value") or value.get("amount"))
                    if numeric is not None:
                        output.append(numeric)
            _collect_numeric_values(value, aliases, output)
    elif isinstance(payload, list):
        for item in payload:
            _collect_numeric_values(item, aliases, output)


def _metric_values(ratios: dict[str, Any], raw: dict[str, Any], *aliases: str) -> list[float]:
    normalized_aliases = {_normalize_metric_key(alias) for alias in aliases}
    values: list[float] = []
    for source in (ratios, raw):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if _normalize_metric_key(key) in normalized_aliases:
                numeric = _safe_float(value if not isinstance(value, dict) else value.get("value") or value.get("amount"))
                if numeric is not None:
                    values.append(numeric)
        _collect_numeric_values(source, normalized_aliases, values)
    deduped: list[float] = []
    for value in values:
        if not deduped or value != deduped[-1]:
            deduped.append(value)
    return deduped


def _metric_value(ratios: dict[str, Any], raw: dict[str, Any], *aliases: str, default: float | None = None) -> float | None:
    values = _metric_values(ratios, raw, *aliases)
    return values[0] if values else default


def _merge_nested_dicts(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merge_nested_dicts(current, value)
        else:
            merged[key] = value
    return merged


def _metric_pair(ratios: dict[str, Any], raw: dict[str, Any], *aliases: str) -> tuple[float | None, float | None]:
    values = _metric_values(ratios, raw, *aliases)
    current = values[0] if values else None
    previous = values[1] if len(values) > 1 else current
    return current, previous


def _table_row_values(raw: dict[str, Any], table_aliases: tuple[str, ...], row_aliases: tuple[str, ...]) -> list[float]:
    table_names = {_normalize_metric_key(alias) for alias in table_aliases}
    row_names = {_normalize_metric_key(alias) for alias in row_aliases}
    tables = raw.get("tables") if isinstance(raw, dict) else None
    if not isinstance(tables, list):
        return []
    for table in tables:
        if not isinstance(table, dict):
            continue
        table_name = _normalize_metric_key(table.get("name"))
        if table_name not in table_names:
            continue
        rows = table.get("rows")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, list) or not row:
                continue
            label = _normalize_metric_key(row[0])
            if label not in row_names:
                continue
            values: list[float] = []
            for cell in row[1:]:
                numeric = _safe_float(cell)
                if numeric is not None:
                    values.append(numeric)
            if values:
                return values
    return []


def _table_metric_value(
    ratios: dict[str, Any],
    raw: dict[str, Any],
    metric_aliases: tuple[str, ...],
    table_aliases: tuple[str, ...],
    row_aliases: tuple[str, ...],
    *,
    default: float | None = None,
) -> float | None:
    direct = _metric_value(ratios, raw, *metric_aliases, default=None)
    if direct is not None:
        return direct
    values = _table_row_values(raw, table_aliases, row_aliases)
    return values[0] if values else default


def _table_metric_pair(
    ratios: dict[str, Any],
    raw: dict[str, Any],
    metric_aliases: tuple[str, ...],
    table_aliases: tuple[str, ...],
    row_aliases: tuple[str, ...],
) -> tuple[float | None, float | None]:
    direct = _metric_values(ratios, raw, *metric_aliases)
    if len(direct) >= 2:
        return direct[0], direct[1]
    table_values = _table_row_values(raw, table_aliases, row_aliases)
    values = direct if direct else table_values
    current = values[0] if values else None
    previous = values[1] if len(values) > 1 else current
    return current, previous


def _score_to_unit_interval(raw: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (raw - lo) / (hi - lo)))


def _normalize_key(value: Any) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _extract_series_values(value: Any) -> list[float]:
    if isinstance(value, (int, float, str)):
        parsed = _safe_float(value)
        return [parsed] if parsed is not None else []
    if isinstance(value, dict):
        ordered_keys = (
            "current",
            "latest",
            "now",
            "prev",
            "previous",
            "q1",
            "q2",
            "q3",
            "fy0",
            "fy1",
            "fy2",
            "value",
        )
        extracted: list[float] = []
        for key in ordered_keys:
            if key in value:
                parsed = _safe_float(value.get(key))
                if parsed is not None:
                    extracted.append(parsed)
        if extracted:
            return extracted
        for key in ("values", "series", "quarters", "history", "data"):
            if key in value and isinstance(value[key], list):
                nested: list[float] = []
                for item in value[key]:
                    nested.extend(_extract_series_values(item))
                if nested:
                    return nested
        return []
    if isinstance(value, list):
        extracted: list[float] = []
        for item in value:
            if isinstance(item, dict):
                if any(label in item for label in ("value", "close", "amount", "percent", "percentage")):
                    for key in ("value", "close", "amount", "percent", "percentage"):
                        parsed = _safe_float(item.get(key))
                        if parsed is not None:
                            extracted.append(parsed)
                            break
                else:
                    extracted.extend(_extract_series_values(item))
            else:
                parsed = _safe_float(item)
                if parsed is not None:
                    extracted.append(parsed)
        return extracted
    return []


def _extract_from_payload(payload: Any, aliases: tuple[str, ...]) -> float | None:
    alias_norms = {_normalize_key(alias) for alias in aliases}
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_norm = _normalize_key(key)
            if key_norm in alias_norms:
                series = _extract_series_values(value)
                if series:
                    return series[0]
                parsed = _safe_float(value)
                if parsed is not None:
                    return parsed
            nested = _extract_from_payload(value, aliases)
            if nested is not None:
                return nested
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                label = (
                    item.get("label")
                    or item.get("name")
                    or item.get("key")
                    or item.get("title")
                    or item.get("metric")
                    or item.get("heading")
                )
                if _normalize_key(label) in alias_norms:
                    series = _extract_series_values(item)
                    if series:
                        return series[0]
                nested = _extract_from_payload(item, aliases)
                if nested is not None:
                    return nested
    return None


def _extract_metric(raw: dict[str, Any], ratios: dict[str, Any], *aliases: str, default: float | None = None) -> float | None:
    for alias in aliases:
        parsed = _safe_float(ratios.get(alias))
        if parsed is not None:
            return parsed
    nested = _extract_from_payload(raw, aliases)
    if nested is not None:
        return nested
    return default


def _extract_metric_series(raw: dict[str, Any], ratios: dict[str, Any], *aliases: str) -> list[float]:
    ordered_ratio_aliases = []
    for alias in aliases:
        ordered_ratio_aliases.extend((alias, f"{alias} prev", f"{alias} q1", f"{alias} q2"))
    ratio_values = [_safe_float(ratios.get(alias)) for alias in ordered_ratio_aliases]
    ratio_series = [value for value in ratio_values if value is not None]
    if ratio_series:
        return ratio_series

    alias_norms = {_normalize_key(alias) for alias in aliases}
    search_stack = [raw]
    while search_stack:
        current = search_stack.pop(0)
        if isinstance(current, dict):
            for key, value in current.items():
                if _normalize_key(key) in alias_norms:
                    series = _extract_series_values(value)
                    if series:
                        return series
                search_stack.append(value)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, dict):
                    label = (
                        item.get("label")
                        or item.get("name")
                        or item.get("key")
                        or item.get("title")
                        or item.get("metric")
                        or item.get("heading")
                    )
                    if _normalize_key(label) in alias_norms:
                        series = _extract_series_values(item)
                        if series:
                            return series
                search_stack.append(item)
    return []


def _series_value(series: list[float], idx: int, fallback: float = 0.0) -> float:
    if idx < len(series):
        return series[idx]
    return fallback


def _closes(price: PriceData, lookback: int | None = None) -> list[float]:
    bars = price.history[-lookback:] if lookback else price.history
    return [bar.close for bar in bars]


def _returns(closes: list[float]) -> list[float]:
    if len(closes) < 2:
        return []
    return [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes))]


def _ema(values: list[float], span: int) -> float:
    if not values:
        return 0.0
    alpha = 2 / (span + 1)
    ema_value = values[0]
    for value in values[1:]:
        ema_value = (alpha * value) + ((1 - alpha) * ema_value)
    return ema_value


def _percentile_rank(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda item: item[1])
    if len(ordered) == 1:
        return {ordered[0][0]: 1.0}
    return {ticker: idx / (len(ordered) - 1) for idx, (ticker, _) in enumerate(ordered)}


def _corr(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    mean_a = mean(a)
    mean_b = mean(b)
    dev_a = [x - mean_a for x in a]
    dev_b = [x - mean_b for x in b]
    denom = math.sqrt(sum(x * x for x in dev_a) * sum(y * y for y in dev_b))
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(dev_a, dev_b)) / denom


def _linear_regression_beta_alpha(y: list[float], x: list[float]) -> tuple[float, float]:
    if len(y) != len(x) or len(y) < 3:
        return 1.0, 0.0
    mean_x = mean(x)
    mean_y = mean(y)
    var_x = sum((value - mean_x) ** 2 for value in x)
    if var_x == 0:
        return 1.0, 0.0
    cov_xy = sum((xv - mean_x) * (yv - mean_y) for xv, yv in zip(x, y))
    beta = cov_xy / var_x
    alpha = mean_y - (beta * mean_x)
    return beta, alpha


def _zscore(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    std = pstdev(values)
    if std == 0:
        return 0.0
    return (values[-1] - avg) / std


def _rank_time_series(values: list[float], window: int) -> float:
    if len(values) < window:
        return 0.0
    window_values = values[-window:]
    ordered = sorted(window_values)
    latest = window_values[-1]
    rank = ordered.index(latest)
    return rank / max(len(window_values) - 1, 1)


def _parse_date_like(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    candidates = (
        text,
        text.split("T")[0],
        text.split(" ")[0],
    )
    for candidate in candidates:
        for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


@dataclass(slots=True)
class FactorBundle:
    score: float
    details: dict[str, float]


class UniverseDiscoveryAgent(BaseAgent):
    agent_id = "agent_00_discovery"

    def __init__(self, nse: NSEClient | None = None, market_data: YFinanceClient | None = None) -> None:
        self.nse = nse
        self.market_data = market_data or YFinanceClient()

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        warnings: list[str] = []
        flows = self.nse.get_fii_dii_data() if self.nse is not None else []
        fii_5d_net = sum((_safe_float(row.get("netValue") or row.get("net")) or 0.0) for row in flows[-5:])
        vix = self.market_data.latest_price("^INDIAVIX") or 18.0
        nifty = self.market_data.load_price_data("^NSEI", period="1y")
        closes = _closes(nifty)
        if not closes:
            discovery = UniverseDiscoveryPlan(
                status="degraded",
                market_regime="degraded",
                selected_profile="standard",
                profile_ladder=["standard", "broad"],
                query_ladder=[_discovery_query("standard"), _discovery_query("broad")],
            )
            warnings.append("Discovery degraded: benchmark history unavailable from yfinance.")
            return {}, {
                "universe_discovery": discovery.model_dump(mode="json"),
                "india_vix": round(vix, 2),
                "fii_5d_net": round(fii_5d_net, 2),
                "nifty_above_sma200": False,
                "recent_return_20d_pct": 0.0,
                "provider_degraded": True,
            }, warnings
        sma200 = mean(closes[-200:]) if len(closes) >= 200 else (mean(closes) if closes else 0.0)
        nifty_above_sma200 = bool(closes and closes[-1] > sma200)
        recent_return_20d = 0.0
        if len(closes) >= 21 and closes[-21] > 0:
            recent_return_20d = ((closes[-1] / closes[-21]) - 1.0) * 100

        if vix >= 24 or not nifty_above_sma200 or fii_5d_net < -2_000:
            market_regime = "risk_off"
            selected_profile = "broad"
        elif vix < 16 and nifty_above_sma200 and fii_5d_net >= 0 and recent_return_20d > 0:
            market_regime = "risk_on"
            selected_profile = "tight"
        else:
            market_regime = "neutral"
            selected_profile = "standard"

        profile_ladder, query_ladder = _discovery_ladder(selected_profile)
        discovery = UniverseDiscoveryPlan(
            status="selected",
            market_regime=market_regime,
            selected_profile=selected_profile,
            profile_ladder=profile_ladder,
            query_ladder=query_ladder,
        )
        return {}, {
            "universe_discovery": discovery.model_dump(mode="json"),
            "india_vix": round(vix, 2),
            "fii_5d_net": round(fii_5d_net, 2),
            "nifty_above_sma200": nifty_above_sma200,
            "recent_return_20d_pct": round(recent_return_20d, 2),
            "provider_degraded": False,
        }, warnings


class UniverseAgent(BaseAgent):
    agent_id = AgentID.UNIVERSE

    def __init__(self, screener: ScreenerClient, settings: Settings, nse: NSEClient | None = None) -> None:
        self.screener = screener
        self.settings = settings
        self.nse = nse

    @staticmethod
    def _symbol_set(rows: list[dict[str, Any]]) -> set[str]:
        tickers: set[str] = set()
        for row in rows:
            symbol = (
                row.get("symbol")
                or row.get("ticker")
                or row.get("tradingsymbol")
                or row.get("sm_symbol")
                or row.get("name")
            )
            if symbol:
                tickers.add(str(symbol).strip().upper().replace(".NS", ""))
        return tickers

    @staticmethod
    def _rank_universe(universe: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            universe,
            key=lambda item: (
                item.get("adv_20d_cr") or 0.0,
                item.get("market_cap_cr") or 0.0,
                item.get("ticker") or "",
            ),
            reverse=True,
        )

    def _build_universe(self, items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
        universe: list[dict[str, Any]] = []
        rejection_reasons = {
            "surveillance": 0,
            "market_cap": 0,
            "adv": 0,
            "pledging": 0,
            "listing_age": 0,
            "debt": 0,
            "negative_cfo": 0,
            "circuit": 0,
        }
        surveillance = set()
        circuit_hits = set()
        if self.nse is not None:
            surveillance = self._symbol_set(self.nse.get_asm_list()) | self._symbol_set(self.nse.get_gsm_list())
            circuit_hits = self._symbol_set(self.nse.get_circuit_breaker_list())
        for item in items:
            data = item.get("data") or {}
            ratios = data.get("top_ratios") or {}
            symbol = data.get("symbol")
            if not symbol:
                continue
            symbol = str(symbol).upper().replace(".NS", "")
            market_cap = _metric_value(ratios, data, "Market Cap", "Market Cap (Cr)", "Market Cap Cr", "market_cap", "market_cap_cr")
            adv_20d = _metric_value(ratios, data, "ADV 20D Cr", "Avg Daily Volume 20D Cr", "adv_20d_cr", "average_daily_volume_20d_cr")
            promoter_pledge = _metric_value(ratios, data, "Promoter pledged", "Promoter pledging", "promoter_pledging", "promoter_pledge_pct", default=0.0) or 0.0
            if market_cap is None or market_cap < 500:
                rejection_reasons["market_cap"] += 1
                continue
            if adv_20d is None or adv_20d < 50:
                rejection_reasons["adv"] += 1
                continue
            if promoter_pledge > 30:
                rejection_reasons["pledging"] += 1
                continue
            if symbol in surveillance:
                rejection_reasons["surveillance"] += 1
                continue
            if symbol in circuit_hits:
                rejection_reasons["circuit"] += 1
                continue
            sector = data.get("sector") or (data.get("analysis") or {}).get("sector")
            bfsi = bool(sector and any(token in sector.lower() for token in ("bank", "finance", "insurance", "nbfc")))
            debt_equity = _metric_value(ratios, data, "Debt to equity", "DE Ratio", "de_ratio", "debt_equity")
            max_de = 8.0 if bfsi else 2.0
            if debt_equity is None or debt_equity > max_de:
                rejection_reasons["debt"] += 1
                continue
            listed_years = _metric_value(ratios, data, "Years Listed", "years_listed", "listing_years", "listed_years")
            if listed_years is None or listed_years < 3:
                rejection_reasons["listing_age"] += 1
                continue
            cfo_current, cfo_prev = _metric_pair(
                ratios,
                data,
                "Cash from operations",
                "Cash from operations prev",
                "cfo",
                "cfo_prev",
                "operating_cash_flow",
                "cashflowfromoperations",
            )
            if cfo_current is None or cfo_prev is None or (cfo_current < 0 and cfo_prev < 0):
                rejection_reasons["negative_cfo"] += 1
                continue
            universe.append(
                UniverseItem(
                    ticker=symbol,
                    company=data.get("name"),
                    sector=sector,
                    market_cap_cr=market_cap,
                    adv_20d_cr=adv_20d,
                    metadata={
                        "top_ratios": ratios,
                        "raw": data,
                        "promoter_pledge_pct": promoter_pledge,
                        "de_ratio": debt_equity,
                    },
                ).model_dump(mode="json")
            )
        return self._rank_universe(universe), rejection_reasons

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        warnings: list[str] = []
        discovery = context.universe_discovery if context.universe_discovery.query_ladder else _default_discovery_plan()
        selected_universe: list[dict[str, Any]] = []
        selected_rejections: dict[str, int] = {}
        selected_query = discovery.query_ladder[-1] if discovery.query_ladder else _discovery_query("broad")
        selected_profile = discovery.profile_ladder[-1] if discovery.profile_ladder else "broad"
        fallback_level = 0

        for idx, query in enumerate(discovery.query_ladder or [_discovery_query("standard")]):
            payload = self.screener.fetch_query(query, fields=UNIVERSE_SCREENER_FIELDS)
            universe, rejection_reasons = self._build_universe(payload.get("items", []))
            if len(universe) > discovery.target_max_count:
                universe = universe[: discovery.target_max_count]
            if len(universe) >= len(selected_universe):
                selected_universe = universe
                selected_rejections = rejection_reasons
                selected_query = query
                selected_profile = discovery.profile_ladder[idx] if idx < len(discovery.profile_ladder) else selected_profile
                fallback_level = idx
            if discovery.target_min_count <= len(universe) <= discovery.target_max_count:
                break

        if fallback_level > 0:
            warnings.append(f"Autonomous discovery broadened to fallback level {fallback_level}.")
        if not selected_universe:
            warnings.append("Universe fetch returned no investable symbols.")
        updated_discovery = discovery.model_copy(
            update={
                "status": "ready" if selected_universe else "empty",
                "fallback_level": fallback_level,
                "final_query": selected_query,
                "final_profile": selected_profile,
                "candidate_count": len(selected_universe),
            }
        )
        return {}, {
            "universe": selected_universe,
            "universe_size": len(selected_universe),
            "rejected_count": sum(selected_rejections.values()),
            "rejection_reasons": selected_rejections,
            "universe_discovery": updated_discovery.model_dump(mode="json"),
        }, warnings


class QualityAgent(BaseAgent):
    agent_id = AgentID.QUALITY

    def __init__(self, screener: ScreenerClient | None = None) -> None:
        self.screener = screener

    def _hydrate_item(self, item: UniverseItem, warnings: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
        raw = item.metadata.get("raw", {})
        ratios = item.metadata.get("top_ratios", {})
        if self.screener is None:
            return raw, ratios
        coverage = sum(
            bool(values)
            for values in (
                _metric_values(ratios, raw, "ROA", "roa"),
                _metric_values(ratios, raw, "Cash from operations", "cfo", "operating_cash_flow"),
                _metric_values(ratios, raw, "Current Ratio", "current_ratio"),
                _metric_values(ratios, raw, "Gross Margin", "gross_margin"),
                _metric_values(ratios, raw, "Asset Turnover", "asset_turnover"),
                _metric_values(ratios, raw, "Enterprise Value", "enterprise_value", "ev"),
                _metric_values(ratios, raw, "Promoter holding", "promoter_holding"),
                _metric_values(ratios, raw, "FII holding", "fii_holding"),
                _metric_values(ratios, raw, "DII holding", "dii_holding"),
            )
        )
        if coverage >= 5:
            return raw, ratios
        try:
            company = self.screener.fetch_company(item.ticker, fields=QUALITY_SCREENER_FIELDS)
        except Exception as exc:
            warnings.append(f"{item.ticker}: screener company hydrate failed: {exc}")
            return raw, ratios
        merged_raw = _merge_nested_dicts(raw, company)
        merged_ratios = dict(ratios)
        merged_ratios.update(company.get("top_ratios") or {})
        item.metadata["raw"] = merged_raw
        item.metadata["top_ratios"] = merged_ratios
        return merged_raw, merged_ratios

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        scores: dict[str, float] = {}
        filtered_universe: list[dict[str, Any]] = []
        breakdown: dict[str, dict[str, float]] = {}
        qualified_metrics: dict[str, dict[str, float]] = {}
        ey_values: dict[str, float] = {}
        roce_values: dict[str, float] = {}
        warnings: list[str] = []
        for item in context.universe:
            raw, ratios = self._hydrate_item(item, warnings)
            roe = _metric_value(ratios, raw, "ROE", "roe", "return_on_equity", default=0.0) or 0.0
            roce = _metric_value(ratios, raw, "ROCE", "roce", "return_on_capital_employed", default=0.0) or 0.0
            debt_equity = _metric_value(ratios, raw, "Debt to equity", "DE Ratio", "de_ratio", "debt_equity", default=0.0) or 0.0
            promoter, promoter_prev = _table_metric_pair(
                ratios,
                raw,
                ("Promoter holding", "Promoter holding prev", "promoter_holding", "promoter_holding_prev"),
                ("Shareholding Pattern", "Shareholding", "Investors"),
                ("Promoters", "Promoter", "Promoter Holding"),
            )
            promoter = promoter or 0.0
            promoter_prev = promoter_prev or promoter
            pledge = _metric_value(ratios, raw, "Promoter pledged", "promoter_pledging", "promoter_pledge_pct", default=0.0) or 0.0
            roa_source, roa_prev_source = _table_metric_pair(
                ratios,
                raw,
                ("ROA", "ROA Prev", "roa", "roa_prev", "return_on_assets"),
                ("Ratios", "Ratios 10Y", "Profitability"),
                ("ROA %", "ROA", "Return on Assets"),
            )
            roa = roa_source if roa_source is not None else roe / 3
            roa_prev = roa_prev_source if roa_prev_source is not None else max(roa - 0.5, 0.0)
            cfo_source, cfo_prev_source = _table_metric_pair(
                ratios,
                raw,
                ("Cash from operations", "Cash from operations prev", "cfo", "cfo_prev", "operating_cash_flow", "cashflowfromoperations"),
                ("Cash Flow", "Cash Flows", "Cash Flow Statement"),
                ("Cash from Operating Activity +", "Cash from Operating Activity", "Cash from operations", "Cash Flow from Operations"),
            )
            cfo = cfo_source or 0.0
            total_assets = _table_metric_value(
                ratios,
                raw,
                ("Total Assets", "total_assets", "assets", "totalassets"),
                ("Balance Sheet",),
                ("Total Assets",),
                default=1.0,
            ) or 1.0
            borrowings, borrowings_prev = _table_metric_pair(
                ratios,
                raw,
                ("Borrowings", "Borrowings prev", "long_term_borrowings", "long_term_debt"),
                ("Balance Sheet",),
                ("Borrowings +", "Borrowings", "Long Term Borrowings"),
            )
            ltd_ratio, ltd_ratio_prev = _metric_pair(ratios, raw, "LT Debt Ratio", "LT Debt Ratio Prev", "long_term_debt_ratio", "lt_debt_ratio", "debt_equity")
            if borrowings is not None and total_assets > 0:
                ltd_ratio = borrowings / total_assets
            if borrowings_prev is not None:
                total_assets_prev_values = _table_row_values(raw, ("Balance Sheet",), ("Total Assets",))
                total_assets_prev = total_assets_prev_values[1] if len(total_assets_prev_values) > 1 else total_assets
                ltd_ratio_prev = borrowings_prev / max(total_assets_prev, 1.0)
            ltd_ratio = ltd_ratio if ltd_ratio is not None else debt_equity
            ltd_ratio_prev = ltd_ratio_prev if ltd_ratio_prev is not None else max(ltd_ratio + 0.05, 0.0)
            current_ratio_source, current_ratio_prev_source = _table_metric_pair(
                ratios,
                raw,
                ("Current Ratio", "Current Ratio Prev", "current_ratio"),
                ("Ratios", "Ratios 10Y", "Financial Health"),
                ("Current Ratio",),
            )
            current_ratio = current_ratio_source if current_ratio_source is not None else 1.0
            current_ratio_prev = current_ratio_prev_source if current_ratio_prev_source is not None else max(current_ratio - 0.1, 0.0)
            shares_out_source, shares_prev_source = _table_metric_pair(
                ratios,
                raw,
                ("Shares Outstanding", "Shares Outstanding Prev", "shares_outstanding", "equity_shares"),
                ("Balance Sheet",),
                ("Equity Share Capital", "Equity Capital", "Share Capital"),
            )
            shares_out, shares_prev = shares_out_source, shares_prev_source
            gross_margin_source, gross_margin_prev_source = _table_metric_pair(
                ratios,
                raw,
                ("Gross Margin", "Gross Margin Prev", "gross_margin"),
                ("Profit & Loss", "P&L", "Quarterly Results", "Annual Results"),
                ("Gross Profit Margin %", "Gross Margin %", "Gross Margin", "OPM %"),
            )
            gross_margin = gross_margin_source or 0.0
            gross_margin_prev = gross_margin_prev_source if gross_margin_prev_source is not None else max(gross_margin - 1.0, 0.0)
            asset_turnover_source, asset_turnover_prev_source = _metric_pair(ratios, raw, "Asset Turnover", "Asset Turnover Prev", "asset_turnover")
            asset_turnover, asset_turnover_prev = asset_turnover_source, asset_turnover_prev_source
            if asset_turnover is None:
                sales_values = _table_row_values(raw, ("Profit & Loss", "P&L", "Annual Results"), ("Sales +", "Sales", "Revenue"))
                if sales_values:
                    asset_turnover = sales_values[0] / max(total_assets, 1.0)
                    if len(sales_values) > 1:
                        total_assets_values = _table_row_values(raw, ("Balance Sheet",), ("Total Assets",))
                        total_assets_prev = total_assets_values[1] if len(total_assets_values) > 1 else total_assets
                        asset_turnover_prev = sales_values[1] / max(total_assets_prev, 1.0)
            asset_turnover = asset_turnover or 0.0
            asset_turnover_prev = asset_turnover_prev if asset_turnover_prev is not None else max(asset_turnover - 0.05, 0.0)
            ebit = _table_metric_value(
                ratios,
                raw,
                ("EBIT", "ebit", "operating_profit"),
                ("Profit & Loss", "P&L", "Annual Results", "Quarterly Results"),
                ("EBIT", "Operating Profit", "Operating Profit +"),
                default=0.0,
            ) or 0.0
            enterprise_value = _metric_value(ratios, raw, "Enterprise Value", "enterprise_value", "ev")
            fixed_assets = _table_metric_value(
                ratios,
                raw,
                ("Net Fixed Assets", "net_fixed_assets", "fixed_assets"),
                ("Balance Sheet",),
                ("Net Block", "Net Fixed Assets", "Fixed Assets"),
                default=0.0,
            ) or 0.0
            working_capital = _table_metric_value(
                ratios,
                raw,
                ("Working Capital", "working_capital", "net_working_capital"),
                ("Balance Sheet",),
                ("Working Capital", "Net Current Assets"),
                default=0.0,
            ) or 0.0
            fii_values = _metric_values(ratios, raw, "FII holding", "FII holding q1", "FII holding q2", "fii_holding", "fii_holding_q1", "fii_holding_q2", "fii_holding_prev")
            if not fii_values:
                fii_values = _table_row_values(raw, ("Shareholding Pattern", "Shareholding", "Investors"), ("FIIs", "FII", "Foreign Institutions"))
            fii_now = fii_values[0] if fii_values else 0.0
            fii_q1 = fii_values[1] if len(fii_values) > 1 else fii_now
            fii_q2 = fii_values[2] if len(fii_values) > 2 else fii_q1
            dii_values = _metric_values(ratios, raw, "DII holding", "DII holding q1", "DII holding q2", "dii_holding", "dii_holding_q1", "dii_holding_q2", "dii_holding_prev")
            if not dii_values:
                dii_values = _table_row_values(raw, ("Shareholding Pattern", "Shareholding", "Investors"), ("DIIs", "DII", "Domestic Institutions"))
            dii_now = dii_values[0] if dii_values else 0.0
            dii_q1 = dii_values[1] if len(dii_values) > 1 else dii_now
            dii_q2 = dii_values[2] if len(dii_values) > 2 else dii_q1
            insider_selling = _metric_value(ratios, raw, "Insider selling", "insider_selling_pct", "insider_sell_pct", default=0.0) or 0.0
            available_fields = sum(
                metric is not None
                for metric in (
                    roa_source,
                    cfo_source,
                    current_ratio_source,
                    gross_margin_source,
                    asset_turnover_source,
                    enterprise_value,
                )
            )
            f_score = 0
            f_score += 1 if roa > 0 else 0
            f_score += 1 if cfo > 0 else 0
            f_score += 1 if roa > roa_prev else 0
            f_score += 1 if (cfo / max(total_assets, 1.0)) > roa else 0
            f_score += 1 if ltd_ratio < ltd_ratio_prev else 0
            f_score += 1 if current_ratio > current_ratio_prev else 0
            f_score += 1 if shares_out is None or shares_prev is None or shares_out <= shares_prev else 0
            f_score += 1 if gross_margin > gross_margin_prev else 0
            f_score += 1 if asset_turnover > asset_turnover_prev else 0
            sparse_fundamentals = sum(
                metric is not None
                for metric in (
                    roa_source,
                    cfo_source,
                    gross_margin_source,
                    asset_turnover_source,
                    shares_out_source,
                )
            ) <= 1
            if sparse_fundamentals and roe >= 15 and roce >= 18 and debt_equity <= 0.5:
                f_score = max(f_score, 6)
            adjustments = 0.0
            adjustments += 10.0 if promoter > 60 else 0.0
            adjustments += 5.0 if promoter > promoter_prev else 0.0
            adjustments -= 15.0 if 15 <= pledge <= 30 else 0.0
            adjustments -= 10.0 if fii_now < fii_q1 < fii_q2 else 0.0
            adjustments += 8.0 if dii_now > dii_q1 > dii_q2 else 0.0
            adjustments -= 20.0 if insider_selling > 1.0 else 0.0
            ey = (ebit / enterprise_value) if enterprise_value not in (None, 0.0) else 0.0
            capital_employed = fixed_assets + working_capital
            roce_raw = (ebit / capital_employed) if capital_employed > 0 else (roce / 100 if roce > 1 else roce)

            breakdown[item.ticker] = {
                "f_score": float(f_score),
                "ey": round(ey, 6),
                "roce": round(roce_raw, 6),
                "insider_selling_pct": round(insider_selling, 4),
                "adjustments": round(adjustments, 2),
            }
            if f_score < 6 and available_fields <= 2 and roe >= 15 and roce >= 18 and debt_equity <= 0.5:
                f_score = 6
                breakdown[item.ticker]["f_score"] = float(f_score)
                breakdown[item.ticker]["sparse_data_override"] = 1.0
            if f_score >= 6:
                ey_values[item.ticker] = ey
                roce_values[item.ticker] = roce_raw
                qualified_metrics[item.ticker] = {
                    "f_score": float(f_score),
                    "adjustments": adjustments,
                    "insider_selling_pct": insider_selling,
                }

        ey_rank = _percentile_rank(ey_values)
        roce_rank = _percentile_rank(roce_values)
        for item in context.universe:
            if item.ticker not in qualified_metrics:
                continue
            combined = ey_rank.get(item.ticker, 0.0) + roce_rank.get(item.ticker, 0.0)
            raw_quality = (combined / 2.0) * 100.0
            final_quality = max(0.0, min(100.0, raw_quality + qualified_metrics[item.ticker]["adjustments"]))
            scores[item.ticker] = round((final_quality / 50.0) - 1.0, 4)
            item_payload = item.model_dump(mode="json")
            item_payload["metadata"]["quality"] = {
                "f_score": qualified_metrics[item.ticker]["f_score"],
                "quality_score": round(final_quality, 4),
                "ey": ey_values.get(item.ticker, 0.0),
                "roce": roce_values.get(item.ticker, 0.0),
                "insider_selling_pct": qualified_metrics[item.ticker]["insider_selling_pct"],
            }
            filtered_universe.append(item_payload)
            breakdown[item.ticker]["quality_score"] = round(final_quality, 4)
        return scores, {"qualified_universe": filtered_universe, "qualified_count": len(filtered_universe), "breakdown": breakdown}, warnings


class MacroAgent(BaseAgent):
    agent_id = AgentID.MACRO

    def __init__(self, nse: NSEClient, market_data: YFinanceClient | None = None) -> None:
        self.nse = nse
        self.market_data = market_data or YFinanceClient()

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        warnings: list[str] = []
        flows = self.nse.get_fii_dii_data()
        recent_net = sum((_safe_float(row.get("netValue") or row.get("net")) or 0.0) for row in flows[-5:])
        vix = self.market_data.latest_price("^INDIAVIX") or 18.0
        nifty = self.market_data.load_price_data("^NSEI", period="1y")
        nifty_closes = _closes(nifty)
        if not nifty_closes:
            warnings.append("Macro degraded: benchmark history unavailable from yfinance.")
            return {}, {
                "regime": "DEGRADED",
                "india_vix": vix,
                "fii_5d_net": recent_net,
                "nifty_above_sma200": False,
                "breadth_pct": 0.0,
                "max_deploy": 0.0,
                "provider_degraded": True,
            }, warnings
        sma200 = mean(nifty_closes[-200:]) if len(nifty_closes) >= 200 else (mean(nifty_closes) if nifty_closes else 0.0)
        nifty_above_sma200 = bool(nifty_closes and nifty_closes[-1] > sma200)

        breadth_hits = 0
        breadth_total = 0
        for item in context.universe[:50]:
            price = context.price_bundle.get(item.ticker)
            if not price or len(price.history) < 50:
                continue
            closes = _closes(price, 50)
            breadth_total += 1
            if closes[-1] > mean(closes):
                breadth_hits += 1
        breadth = breadth_hits / breadth_total if breadth_total else 0.5

        if vix < 14:
            regime = "BULL"
            max_deploy = 0.65
        elif vix < 20:
            regime = "NEUTRAL"
            max_deploy = 0.50
        elif vix < 28:
            regime = "CAUTION"
            max_deploy = 0.35
        elif vix < 35:
            regime = "BEAR"
            max_deploy = 0.20
        else:
            regime = "CRISIS"
            max_deploy = 0.0

        if recent_net < -2_000 and regime == "BULL":
            regime = "NEUTRAL"
        elif recent_net < -2_000 and regime == "NEUTRAL":
            regime = "CAUTION"

        if not nifty_above_sma200:
            max_deploy *= 0.7
        if recent_net < -2_000:
            max_deploy *= 0.8
        if breadth < 0.35:
            max_deploy *= 0.25
        elif breadth < 0.50:
            max_deploy *= 0.50
        elif breadth < 0.70:
            max_deploy *= 0.80

        return {}, {
            "regime": regime,
            "india_vix": vix,
            "fii_5d_net": recent_net,
            "nifty_above_sma200": nifty_above_sma200,
            "breadth_pct": breadth,
            "max_deploy": round(max_deploy, 4),
            "provider_degraded": False,
        }, warnings


class EventAgent(BaseAgent):
    agent_id = AgentID.EVENTS
    REGULATORY_RISK_KEYWORDS = ("sebi", "investigation", "fraud", "auditor", "resignation", "forensic", "governance", "trading halt")
    BUYBACK_KEYWORDS = ("buyback", "open offer", "tender offer")
    ORDER_WIN_KEYWORDS = ("order win", "order received", "contract win", "contract awarded", "purchase order")
    EXPANSION_KEYWORDS = ("capacity expansion", "capex", "new plant", "expansion", "commissioned")
    QUERY_TEMPLATES = {
        "regulatory": "{name} NSE SEBI investigation fraud resignation auditor governance",
        "catalyst": "{name} NSE buyback order win contract capacity expansion",
        "earnings": "{name} NSE earnings results beat miss estimate",
    }

    def __init__(self, exa: ExaClient, rss: RSSClient, nse: NSEClient) -> None:
        self.exa = exa
        self.rss = rss
        self.nse = nse

    @staticmethod
    def _earnings_surprise_pct(text: str) -> float | None:
        match = re.search(r"(beat|beats|miss|misses|surprise)[^\d-]{0,24}(-?\d+(?:\.\d+)?)\s*%", text)
        if match is None:
            return None
        value = float(match.group(2))
        if "miss" in match.group(1):
            return -abs(value)
        return abs(value)

    @staticmethod
    def _entry_text(entry: Any) -> str:
        if isinstance(entry, dict):
            parts = [
                entry.get("title"),
                entry.get("headline"),
                entry.get("subject"),
                entry.get("purpose"),
                entry.get("description"),
                entry.get("summary"),
                entry.get("text"),
                entry.get("link"),
            ]
            return " ".join(str(part) for part in parts if part).lower()
        return str(entry).lower()

    @staticmethod
    def _entry_date(entry: Any) -> date | None:
        if not isinstance(entry, dict):
            return None
        for key in ("date", "exDate", "published", "publishedAt", "boardMeetingDate", "meetingDate"):
            parsed = _parse_date_like(entry.get(key))
            if parsed is not None:
                return parsed
        return None

    def _filter_circulars(self, item: UniverseItem, circulars: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ticker = item.ticker.upper()
        company = (item.company or "").lower()
        matched: list[dict[str, Any]] = []
        for circular in circulars:
            text = self._entry_text(circular)
            if ticker.lower() in text or (company and company in text):
                matched.append(circular)
        return matched

    @staticmethod
    def _has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for entry in entries:
            key = "|".join(
                [
                    str(entry.get("title") or entry.get("headline") or entry.get("subject") or "").strip().lower(),
                    str(entry.get("link") or entry.get("url") or "").strip().lower(),
                    str(entry.get("published") or entry.get("publishedAt") or entry.get("date") or "").strip().lower(),
                ]
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entry)
        return deduped

    def _search_exa(self, item: UniverseItem, topic: str, num_results: int = 2) -> list[dict[str, Any]]:
        if not self.exa.api_keys:
            return []
        query = self.QUERY_TEMPLATES[topic].format(name=item.company or item.ticker)
        return self.exa.search(self.agent_id, query, num_results=num_results)

    def _collect_external_evidence(self, item: UniverseItem) -> tuple[list[dict[str, Any]], dict[str, int]]:
        rss_results = self.rss.search(item.company or item.ticker, limit=4)
        exa_results: list[dict[str, Any]] = []
        low_coverage = len(rss_results) < 2
        if low_coverage or not any(self._has_keyword(self._entry_text(entry), self.REGULATORY_RISK_KEYWORDS) for entry in rss_results):
            exa_results.extend(self._search_exa(item, "regulatory"))
        if low_coverage or not any(
            self._has_keyword(self._entry_text(entry), self.BUYBACK_KEYWORDS + self.ORDER_WIN_KEYWORDS + self.EXPANSION_KEYWORDS)
            for entry in rss_results
        ):
            exa_results.extend(self._search_exa(item, "catalyst"))
        if low_coverage:
            exa_results.extend(self._search_exa(item, "earnings"))
        merged = self._dedupe_entries([*rss_results, *exa_results])
        return merged, {"rss": len(rss_results), "exa": len(exa_results)}

    def _recent_entries(
        self,
        entries: list[dict[str, Any]],
        *,
        keywords: tuple[str, ...],
        context_date: date,
        max_age_days: int,
    ) -> list[dict[str, Any]]:
        matched: list[dict[str, Any]] = []
        for entry in entries:
            entry_text = self._entry_text(entry)
            if not self._has_keyword(entry_text, keywords):
                continue
            entry_date = self._entry_date(entry)
            if entry_date is None or 0 <= (context_date - entry_date).days <= max_age_days:
                matched.append(entry)
        return matched

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        event_map: dict[str, dict[str, Any]] = {}
        circular_loader = getattr(self.nse, "get_latest_circulars", None)
        latest_circulars = circular_loader() if callable(circular_loader) else []
        for item in context.universe:
            actions = self.nse.get_corporate_actions(item.ticker)
            headlines, source_counts = self._collect_external_evidence(item)
            circulars = self._filter_circulars(item, latest_circulars)
            text_entries = actions + circulars + headlines
            text = " ".join(self._entry_text(entry) for entry in text_entries)
            days_to_earnings: int | None = None
            days_to_ex_dividend: int | None = None
            days_since_results: int | None = None
            block_reason = ""
            catalyst_type = ""
            for action in actions:
                action_text = self._entry_text(action)
                action_date = self._entry_date(action)
                days_out = (action_date - context.date).days if action_date is not None else None
                days_since = (context.date - action_date).days if action_date is not None else None
                if "result" in action_text or "earnings" in action_text:
                    if days_out is not None:
                        days_to_earnings = days_out if days_to_earnings is None else min(days_to_earnings, days_out)
                    if days_since is not None and days_since >= 0:
                        days_since_results = days_since if days_since_results is None else min(days_since_results, days_since)
                if "dividend" in action_text or "ex-dividend" in action_text:
                    if days_out is not None:
                        days_to_ex_dividend = days_out if days_to_ex_dividend is None else min(days_to_ex_dividend, days_out)
                if days_out is not None and 0 <= days_out <= 3 and any(word in action_text for word in ("split", "rights", "board")):
                    block_reason = f"board_event_in_{days_out}_days"
                if days_out is not None and 0 <= days_out <= 5 and ("result" in action_text or "earnings" in action_text):
                    block_reason = f"earnings_in_{days_out}_days"
                if days_out is not None and 0 <= days_out <= 2 and ("dividend" in action_text or "ex-dividend" in action_text):
                    block_reason = f"ex_dividend_in_{days_out}_days"
                if not block_reason and days_since is not None and 0 <= days_since <= 1 and ("result" in action_text or "earnings" in action_text):
                    block_reason = f"earnings_recent_{days_since}_days"

            regulatory_evidence = self._recent_entries(
                [*circulars, *headlines],
                keywords=self.REGULATORY_RISK_KEYWORDS,
                context_date=context.date,
                max_age_days=30,
            )
            if not block_reason and regulatory_evidence:
                block_reason = "regulatory_or_governance_risk"
            if not block_reason:
                earnings_window = re.search(r"earnings[^\d]{0,20}(\d+)\s+day", text)
                if earnings_window and int(earnings_window.group(1)) <= 5:
                    block_reason = f"earnings_in_{earnings_window.group(1)}_days"

            catalyst_score = 0.0
            earnings_surprise_pct = self._earnings_surprise_pct(text)
            buyback_evidence = self._recent_entries(
                headlines,
                keywords=self.BUYBACK_KEYWORDS,
                context_date=context.date,
                max_age_days=30,
            )
            order_evidence = self._recent_entries(
                headlines,
                keywords=self.ORDER_WIN_KEYWORDS,
                context_date=context.date,
                max_age_days=30,
            )
            expansion_evidence = self._recent_entries(
                headlines,
                keywords=self.EXPANSION_KEYWORDS,
                context_date=context.date,
                max_age_days=45,
            )
            if buyback_evidence:
                catalyst_score = 0.7
                catalyst_type = "buyback"
            elif earnings_surprise_pct is not None and days_since_results is not None and 2 <= days_since_results <= 20:
                if earnings_surprise_pct > 10:
                    catalyst_score = 0.8
                    catalyst_type = "post_earnings_drift"
                elif earnings_surprise_pct > 5:
                    catalyst_score = 0.4
                    catalyst_type = "post_earnings_drift"
                elif earnings_surprise_pct < -10:
                    catalyst_score = -0.8
                    catalyst_type = "negative_post_earnings_drift"
                elif earnings_surprise_pct < -5:
                    catalyst_score = -0.4
                    catalyst_type = "negative_post_earnings_drift"
            elif order_evidence or "beat" in text:
                catalyst_score = 0.5
                catalyst_type = "order_or_earnings_beat"
            elif expansion_evidence:
                catalyst_score = 0.4
                catalyst_type = "capacity_expansion"
            event_block = bool(block_reason)
            event_map[item.ticker] = {
                "event_block": event_block,
                "block_reason": block_reason,
                "article_count": len(headlines),
                "circular_count": len(circulars),
                "source_counts": source_counts,
                "days_to_earnings": days_to_earnings,
                "days_to_ex_dividend": days_to_ex_dividend,
                "days_since_results": days_since_results,
                "earnings_surprise_pct": earnings_surprise_pct or 0.0,
                "regulatory_evidence": [self._entry_text(entry)[:160] for entry in regulatory_evidence[:3]],
                "catalyst_evidence": [self._entry_text(entry)[:160] for entry in (buyback_evidence or order_evidence or expansion_evidence)[:3]],
                "catalyst_score": 0.0 if event_block else catalyst_score,
                "catalyst_type": "" if event_block else catalyst_type,
            }
        warnings = []
        if len(context.universe) > 20:
            warnings.append(f"Event coverage expanded to {len(context.universe)} names.")
        return {}, {"event_map": event_map}, warnings


class SentimentAgent(BaseAgent):
    agent_id = AgentID.SENTIMENT
    POSITIVE = ("order", "win", "beat", "record", "expansion", "buyback", "upgrade", "approval")
    NEGATIVE = ("fraud", "investigation", "sebi", "resignation", "default", "debt", "downgrade", "ban")

    def __init__(self, exa: ExaClient, rss: RSSClient) -> None:
        self.exa = exa
        self.rss = rss

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        scores: dict[str, float] = {}
        sentiment_map: dict[str, dict[str, Any]] = {}
        for item in context.universe:
            articles = self.rss.search(item.company or item.ticker, limit=4)
            if not articles and self.exa.api_keys:
                articles = self.exa.search(self.agent_id, f"{item.company or item.ticker} site:economictimes.com OR site:moneycontrol.com", num_results=4)
            pos = 0.0
            neg = 0.0
            fresh_articles = 0
            stale_articles = 0
            for article in articles:
                title = str(article.get("title") or article.get("text") or article).lower()
                article_date = EventAgent._entry_date(article)
                if article_date is None:
                    age_days = 1
                else:
                    age_days = max(0, (context.date - article_date).days)
                if age_days > 3:
                    stale_articles += 1
                    continue
                fresh_articles += 1
                decay = math.exp(-0.5 * age_days)
                pos += decay * sum(word in title for word in self.POSITIVE)
                neg += decay * sum(word in title for word in self.NEGATIVE)
            raw = (pos - neg) / max(pos + neg + 1, 1)
            scores[item.ticker] = max(-1.0, min(1.0, raw))
            sentiment_map[item.ticker] = {
                "article_count": len(articles),
                "fresh_article_count": fresh_articles,
                "stale_article_count": stale_articles,
                "positive_hits": round(pos, 4),
                "negative_hits": round(neg, 4),
            }
        warnings = []
        if len(context.universe) > 20:
            warnings.append(f"Sentiment coverage expanded to {len(context.universe)} names.")
        return scores, {"sentiment_map": sentiment_map}, warnings


class SectorAgent(BaseAgent):
    agent_id = AgentID.SECTOR

    def __init__(self, market_data: YFinanceClient) -> None:
        self.market_data = market_data

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        sector_scores: dict[str, float] = {}
        sector_map: dict[str, dict[str, float]] = {}
        observed_sectors = {item.sector for item in context.universe if item.sector}
        for sector in observed_sectors:
            ticker = SECTOR_INDEX_MAP.get(sector or "", "")
            if not ticker:
                continue
            price = self.market_data.load_price_data(ticker, period="1y")
            closes = _closes(price)
            if len(closes) < 127:
                continue
            r30 = (closes[-1] / closes[-30]) - 1
            r63 = (closes[-1] / closes[-63]) - 1
            r126 = (closes[-1] / closes[-126]) - 1
            sector_scores[sector] = (0.2 * r30) + (0.4 * r63) + (0.4 * r126)
        ranks = _percentile_rank(sector_scores)
        for sector, rank in ranks.items():
            sector_map[sector] = {
                "rank_score": rank,
                "weight_multiplier": 1.3 if rank > 0.75 else (0.5 if rank < 0.25 else 1.0),
            }
        return {}, {"sector_map": sector_map}, []


class OwnershipAgent(BaseAgent):
    agent_id = AgentID.OWNERSHIP

    def __init__(self, nse: NSEClient | None = None, screener: ScreenerClient | None = None) -> None:
        self.nse = nse
        self.screener = screener

    def _hydrate_item(self, item: UniverseItem, warnings: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
        raw = item.metadata.get("raw", {})
        ratios = item.metadata.get("top_ratios", {})
        if self.screener is None:
            return raw, ratios
        coverage = sum(
            bool(values)
            for values in (
                _metric_values(ratios, raw, "Promoter holding", "promoter_holding"),
                _metric_values(ratios, raw, "Promoter pledged", "promoter_pledging", "promoter_pledge_pct"),
                _metric_values(ratios, raw, "FII holding", "fii_holding"),
                _metric_values(ratios, raw, "DII holding", "dii_holding"),
            )
        )
        if coverage >= 3:
            return raw, ratios
        try:
            company = self.screener.fetch_company(item.ticker, fields=OWNERSHIP_SCREENER_FIELDS)
        except Exception as exc:
            warnings.append(f"{item.ticker}: screener ownership hydrate failed: {exc}")
            return raw, ratios
        merged_raw = _merge_nested_dicts(raw, company)
        merged_ratios = dict(ratios)
        merged_ratios.update(company.get("top_ratios") or {})
        item.metadata["raw"] = merged_raw
        item.metadata["top_ratios"] = merged_ratios
        return merged_raw, merged_ratios

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        scores: dict[str, float] = {}
        details: dict[str, dict[str, float]] = {}
        warnings: list[str] = []
        for item in context.universe:
            raw, ratios = self._hydrate_item(item, warnings)
            promoter, promoter_prev = _table_metric_pair(
                ratios,
                raw,
                ("Promoter holding", "Promoter holding prev", "promoter_holding", "promoter_holding_prev"),
                ("Shareholding Pattern", "Shareholding", "Investors"),
                ("Promoters", "Promoter", "Promoter Holding"),
            )
            promoter = promoter or 0.0
            promoter_prev = promoter_prev or promoter
            promoter_pledge = _metric_value(ratios, raw, "Promoter pledged", "promoter_pledging", "promoter_pledge_pct", default=0.0) or 0.0
            fii_now, fii_prev = _table_metric_pair(
                ratios,
                raw,
                ("FII holding", "FII holding prev", "fii_holding", "fii_holding_prev"),
                ("Shareholding Pattern", "Shareholding", "Investors"),
                ("FIIs", "FII", "Foreign Institutions"),
            )
            fii_now = fii_now or 0.0
            fii_prev = fii_prev or fii_now
            dii_now, dii_prev = _table_metric_pair(
                ratios,
                raw,
                ("DII holding", "DII holding prev", "dii_holding", "dii_holding_prev"),
                ("Shareholding Pattern", "Shareholding", "Investors"),
                ("DIIs", "DII", "Domestic Institutions"),
            )
            dii_now = dii_now or 0.0
            dii_prev = dii_prev or dii_now
            bulk_deals = self.nse.get_bulk_deals(item.ticker) if self.nse is not None else []
            block_deals = self.nse.get_block_deals(item.ticker) if self.nse is not None else []
            flow_signal = 0.0
            for deal in bulk_deals + block_deals:
                side = str(deal.get("buySell") or deal.get("side") or "").upper()
                quantity = _safe_float(deal.get("quantity") or deal.get("qty")) or 0.0
                if side.startswith("B"):
                    flow_signal += quantity
                elif side.startswith("S"):
                    flow_signal -= quantity
            flow_score = _score_to_unit_interval(flow_signal, -5_000_000, 5_000_000) * 2 - 1
            score = (
                0.35 * (_score_to_unit_interval(promoter, 35, 75) * 2 - 1)
                + 0.15 * (_score_to_unit_interval(promoter - promoter_prev, -3, 3) * 2 - 1)
                + 0.20 * (_score_to_unit_interval(fii_now - fii_prev, -3, 3) * 2 - 1)
                + 0.20 * (_score_to_unit_interval(dii_now - dii_prev, -3, 3) * 2 - 1)
                + 0.10 * flow_score
                - 0.30 * _score_to_unit_interval(promoter_pledge, 0, 30)
            )
            scores[item.ticker] = round(max(-1.0, min(1.0, score)), 4)
            details[item.ticker] = {
                "promoter_holding": promoter,
                "promoter_delta": round(promoter - promoter_prev, 4),
                "fii_delta": round(fii_now - fii_prev, 4),
                "dii_delta": round(dii_now - dii_prev, 4),
                "flow_signal": round(flow_signal, 2),
            }
        return scores, {"ownership_coverage": len(scores), "ownership_breakdown": details}, warnings


class RiskAgent(BaseAgent):
    agent_id = AgentID.RISK

    def __init__(self, market_data: YFinanceClient, repository: QuantRepository | None = None) -> None:
        self.market_data = market_data
        self.repository = repository

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        cash_pct = context.portfolio.cash_balance / max(context.portfolio.portfolio_value, 1.0)
        warnings: list[str] = []
        positions = self.repository.list_positions() if self.repository is not None else []
        price_bundle = dict(context.price_bundle)
        for position in positions:
            if position.ticker not in price_bundle:
                price_bundle[position.ticker] = self.market_data.load_price_data(f"{position.ticker}.NS", period="1y")
        if "^NSEI" not in price_bundle:
            price_bundle["^NSEI"] = self.market_data.load_price_data("^NSEI", period="1y")
        metrics = compute_risk_metrics(price_bundle=price_bundle, positions=positions, benchmark_ticker="^NSEI")
        var_95_pct = float(metrics["var_95_pct"])
        if cash_pct < 0.2:
            warnings.append("Cash buffer below 20%.")
        if var_95_pct > 0.025:
            warnings.append("VaR 95 exceeds 2.5% threshold.")
        if float(metrics["portfolio_beta"]) > 1.3:
            warnings.append("Portfolio beta exceeds 1.3.")
        if float(metrics["mdd_current_pct"]) > 0.12:
            warnings.append("Current max drawdown exceeds 12%.")
        for breach in metrics["stop_breaches"]:
            warnings.append(f"Stop breached for {breach['ticker']}.")
        hard_block = bool(metrics["stop_breaches"]) or float(metrics["var_95_pct"]) >= 0.05 or float(metrics["mdd_current_pct"]) >= 0.18 or context.regime == "CRISIS"
        position_scale = 1.0
        if not hard_block and (cash_pct < 0.2 or float(metrics["var_95_pct"]) >= 0.03 or float(metrics["mdd_current_pct"]) >= 0.10):
            position_scale = 0.5
        return {}, {
            "cash_pct": cash_pct,
            "var_95_pct": round(var_95_pct, 4),
            "portfolio_beta": metrics["portfolio_beta"],
            "mdd_current_pct": metrics["mdd_current_pct"],
            "stop_breaches": metrics["stop_breaches"],
            "hard_block": hard_block,
            "position_scale": position_scale,
            "open_positions": context.portfolio.open_positions,
        }, warnings


class MomentumAgent(BaseAgent):
    agent_id = AgentID.MOMENTUM

    def __init__(self, market_data: YFinanceClient) -> None:
        self.market_data = market_data

    def _bundle(self, item: UniverseItem, price: PriceData, benchmark: PriceData, regime: str, india_vix: float) -> FactorBundle | None:
        closes = _closes(price)
        if len(closes) < 252:
            return None
        rets = _returns(closes)
        vol = pstdev(rets[-63:]) if len(rets) >= 63 else 0.0
        raw_mom = (closes[-21] / closes[-252]) - 1.0
        mom_adj = raw_mom / vol if vol > 0 else 0.0

        bench_closes = _closes(benchmark)
        rs_signal = 0.0
        if len(bench_closes) >= 63:
            rs = (closes[-1] / closes[-63]) / max(bench_closes[-1] / bench_closes[-63], 1e-9)
            rs_signal = 1.0 if rs > 1.10 else (-1.0 if rs < 0.90 else 0.0)

        recent = price.history[-6:]
        vol_deltas = []
        intraday = []
        for idx in range(1, len(recent)):
            prev_vol = max(recent[idx - 1].volume, 1.0)
            vol_deltas.append(math.log(max(recent[idx].volume, 1.0)) - math.log(prev_vol))
            intraday.append((recent[idx].close - recent[idx].open) / max(recent[idx].open, 1e-6))
        alpha1 = -_corr(vol_deltas, intraday)

        annual = price.history[-252:]
        high_52 = max(bar.high for bar in annual)
        low_52 = min(bar.low for bar in annual)
        proximity = (closes[-1] - low_52) / max(high_52 - low_52, 1e-9)
        adv20 = mean(bar.volume for bar in price.history[-20:]) if len(price.history) >= 20 else 0.0
        breakout = 1.0 if proximity > 0.90 and price.history[-1].volume > (1.5 * adv20) else 0.0

        score = (0.45 * mom_adj) + (0.25 * rs_signal) + (0.15 * alpha1) + (0.15 * breakout)
        crash_mode = "normal"
        if india_vix > 28 or regime == "CRISIS":
            crash_mode = "disabled"
            score = 0.0
        elif india_vix > 20 or regime in {"CAUTION", "BEAR"}:
            crash_mode = "halved"
            score *= 0.5
        return FactorBundle(
            score=score,
            details={
                "raw_momentum": round(raw_mom, 6),
                "mom_adj": round(mom_adj, 6),
                "rs_signal": round(rs_signal, 4),
                "alpha1": round(alpha1, 6),
                "breakout": round(breakout, 4),
                "proximity_52w": round(proximity, 6),
                "india_vix": round(india_vix, 4),
                "crash_mode": 0.0 if crash_mode == "normal" else (0.5 if crash_mode == "halved" else 1.0),
            },
        )

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        benchmark = context.price_bundle.get("^NSEI") or self.market_data.load_price_data("^NSEI", period="1y")
        macro_result = context.upstream_results.get("agent_06_macro")
        india_vix = float((macro_result.artifacts.get("india_vix") if macro_result else None) or self.market_data.latest_price("^INDIAVIX") or 18.0)
        raw_scores: dict[str, float] = {}
        details: dict[str, dict[str, float]] = {}
        for item in context.universe[:50]:
            price = context.price_bundle.get(item.ticker) or self.market_data.load_price_data(f"{item.ticker}.NS", period="1y")
            bundle = self._bundle(item, price, benchmark, context.regime, india_vix)
            if bundle is None:
                continue
            raw_scores[item.ticker] = bundle.score
            details[item.ticker] = bundle.details
        ranked = _percentile_rank(raw_scores)
        scores = {
            ticker: (0.0 if abs(raw_scores.get(ticker, 0.0)) < 1e-9 else round((rank * 2) - 1, 4))
            for ticker, rank in ranked.items()
        }
        return scores, {"momentum_breakdown": details}, []


class ReversionAgent(BaseAgent):
    agent_id = AgentID.REVERSION

    def __init__(self, market_data: YFinanceClient) -> None:
        self.market_data = market_data

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        scores: dict[str, float] = {}
        details: dict[str, dict[str, float]] = {}
        for item in context.universe[:50]:
            price = context.price_bundle.get(item.ticker) or self.market_data.load_price_data(f"{item.ticker}.NS", period="6mo")
            if len(price.history) < 60:
                continue
            closes = _closes(price, 60)
            ema20 = _ema(closes[-20:], span=20)
            std20 = pstdev(closes[-20:]) if len(closes) >= 20 else 0.0
            z = ((closes[-1] - ema20) / std20) if std20 > 0 else 0.0

            bb_widths = []
            for idx in range(20, len(closes) + 1):
                window = closes[idx - 20 : idx]
                sma = mean(window)
                std = pstdev(window) if len(window) > 1 else 0.0
                bb_widths.append(((sma + 2 * std) - (sma - 2 * std)) / max(sma, 1e-9))
            compression = 1.0 if bb_widths and bb_widths[-1] <= sorted(bb_widths)[max(0, int(len(bb_widths) * 0.1) - 1)] else 0.0

            low_rank = 1.0 - _rank_time_series([bar.low for bar in price.history], 9)
            last_bar = price.history[-1]
            alpha101 = (last_bar.close - last_bar.open) / max((last_bar.high - last_bar.low) + 0.001, 1e-9)
            adv20 = mean(bar.volume for bar in price.history[-20:])
            alpha101 = alpha101 if last_bar.volume > (1.3 * adv20) else 0.0

            entry_zone = -3.5 < z < -2.0
            stop_breach = z <= -3.5
            exit_zone = z > -0.3
            overbought = z > 1.5

            if stop_breach:
                signal = -1.0
            elif entry_zone:
                signal = min(1.0, 0.55 + (0.20 * compression) + (0.15 * low_rank) + (0.10 * max(alpha101, 0.0)))
            elif overbought:
                signal = -0.75
            elif exit_zone:
                signal = -0.30
            else:
                signal = max(-0.2, min(0.4, (0.10 * compression) + (0.10 * low_rank) + (0.05 * alpha101) - (0.10 * max(z, 0.0))))

            scores[item.ticker] = round(max(-1.0, min(1.0, signal)), 4)
            details[item.ticker] = {
                "zscore": round(z, 4),
                "compression": compression,
                "alpha4_like": round(low_rank, 4),
                "alpha101": round(alpha101, 4),
                "entry_zone": 1.0 if entry_zone else 0.0,
                "exit_zone": 1.0 if exit_zone else 0.0,
                "stop_breach": 1.0 if stop_breach else 0.0,
            }
        return scores, {"reversion_breakdown": details}, []


class PairsAgent(BaseAgent):
    agent_id = AgentID.PAIRS

    def __init__(self, market_data: YFinanceClient, validated_pairs_path: Path | None = None) -> None:
        self.market_data = market_data
        self.validated_pairs_path = validated_pairs_path

    def _candidate_pairs(self) -> list[dict[str, Any]]:
        if self.validated_pairs_path is None:
            return [{"cheap": cheap, "rich": rich, "valid": False, "source": "fallback"} for cheap, rich in DEFAULT_PAIR_CANDIDATES]
        return load_active_pair_rows(self.validated_pairs_path, fallback=list(DEFAULT_PAIR_CANDIDATES))

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        scores: dict[str, float] = {}
        details: dict[str, dict[str, float]] = {}
        warnings: list[str] = []
        universe_tickers = {item.ticker for item in context.universe}
        validated_pairs = [row for row in self._candidate_pairs() if bool(row.get("valid"))]
        if not validated_pairs:
            warnings.append("Pairs agent disabled until validated pairs are available.")
            return scores, {"pairs_breakdown": details}, warnings
        for row in validated_pairs:
            cheap = str(row["cheap"])
            rich = str(row["rich"])
            if cheap not in universe_tickers or rich not in universe_tickers:
                continue
            cheap_price = context.price_bundle.get(cheap) or self.market_data.load_price_data(f"{cheap}.NS", period="6mo")
            rich_price = context.price_bundle.get(rich) or self.market_data.load_price_data(f"{rich}.NS", period="6mo")
            cheap_closes = _closes(cheap_price, 126)
            rich_closes = _closes(rich_price, 126)
            if len(cheap_closes) < 60 or len(rich_closes) < 60:
                continue
            log_y = [math.log(max(value, 1e-6)) for value in cheap_closes[-60:]]
            log_x = [math.log(max(value, 1e-6)) for value in rich_closes[-60:]]
            beta = float(row.get("beta") or 0.0)
            alpha = float(row.get("alpha") or 0.0)
            if beta == 0.0 and alpha == 0.0:
                beta, alpha = _linear_regression_beta_alpha(log_y, log_x)
            spread = [y - ((beta * x) + alpha) for y, x in zip(log_y, log_x)]
            z = _zscore(spread)
            half_life = float(row.get("half_life") or 0.0)
            adf_pvalue = float(row.get("adf_pvalue") or 0.0)
            entry_zone = z < -2.0
            exit_zone = z > -0.3
            stop_breach = z < -3.5
            if stop_breach:
                score = -1.0
            elif entry_zone:
                score = min(1.0, 0.6 + min(abs(z) - 2.0, 1.5) * 0.2)
            elif exit_zone:
                score = -0.35
            else:
                score = 0.0
            scores[cheap] = round(score, 4)
            details[cheap] = {
                "paired_with": rich,
                "spread_z": round(z, 4),
                "beta": round(beta, 4),
                "alpha": round(alpha, 6),
                "half_life": round(half_life, 4),
                "adf_pvalue": round(adf_pvalue, 6),
                "entry_zone": 1.0 if entry_zone else 0.0,
                "exit_zone": 1.0 if exit_zone else 0.0,
                "stop_breach": 1.0 if stop_breach else 0.0,
            }
        return scores, {"pairs_breakdown": details}, warnings


class LiquidityAgent(BaseAgent):
    agent_id = AgentID.LIQUIDITY

    def __init__(self, market_data: YFinanceClient) -> None:
        self.market_data = market_data

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        scores: dict[str, float] = {}
        metrics: dict[str, dict[str, float]] = {}
        for item in context.universe[:50]:
            price = context.price_bundle.get(item.ticker) or self.market_data.load_price_data(f"{item.ticker}.NS", period="3mo")
            if len(price.history) < 21:
                continue
            recent = price.history[-21:]
            adv_notional = mean(bar.close * bar.volume for bar in recent)
            adv_cr = adv_notional / 1e7
            returns = _returns([bar.close for bar in recent])
            illiquidity = mean((abs(ret) / max(bar.close * bar.volume, 1.0)) for ret, bar in zip(returns, recent[1:])) if returns else 0.0
            score = (0.8 * (_score_to_unit_interval(adv_cr, 25, 500) * 2 - 1)) - (0.2 * _score_to_unit_interval(illiquidity * 1e8, 0, 5))
            scores[item.ticker] = round(max(-1.0, min(1.0, score)), 4)
            metrics[item.ticker] = {"adv_20d_cr": round(adv_cr, 4), "amihud_like": round(illiquidity, 8)}
        return scores, {"liquidity_metrics": metrics}, []


class BacktesterAgent(BaseAgent):
    agent_id = AgentID.BACKTESTER

    def __init__(self, repository: QuantRepository) -> None:
        self.repository = repository

    def evaluate(self, context: MarketContext) -> tuple[dict[str, float], dict, list[str]]:
        ic_snapshot = self.repository.latest_ic_snapshot()
        active = {
            agent_id: float(data.get("ic_weight") or data.get("ic_value") or 0.0)
            for agent_id, data in ic_snapshot.items()
            if bool(data.get("active", True))
        }
        warnings: list[str] = []
        if not active:
            warnings.append("Backtester has no validated IC weights yet; trading weights withheld.")
        total = sum(active.values()) or 1.0
        weights = {agent_id: round(value / total, 6) for agent_id, value in active.items()}
        ic_values = {agent_id: float(data.get("ic_value") or 0.0) for agent_id, data in ic_snapshot.items()}
        decay = {agent_id: data.get("decay_lambda") for agent_id, data in ic_snapshot.items() if data.get("decay_lambda") is not None}
        active_signal_agents = sorted(weights)
        dormant_signal_agents = sorted(agent_id for agent_id, data in ic_snapshot.items() if not bool(data.get("active", True)))
        return {}, {
            "ic_weights": weights,
            "ic_values": ic_values,
            "ic_snapshot": ic_snapshot,
            "ic_decay": decay,
            "active_signal_agents": active_signal_agents,
            "dormant_signal_agents": dormant_signal_agents,
            "weights_ready": bool(weights),
        }, warnings


class BossAgent:
    agent_id = "boss"

    def __init__(self, repository: QuantRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def run(self, context: MarketContext) -> list[TradeDecision]:
        if context.runtime_overrides.get("pause_entries"):
            return []
        weights_result = context.upstream_results.get("agent_11_backtester")
        ic_weights = (weights_result.artifacts.get("ic_weights") if weights_result else {}) or {}
        ic_snapshot = (weights_result.artifacts.get("ic_snapshot") if weights_result else {}) or {}
        active_signal_agents = set((weights_result.artifacts.get("active_signal_agents") if weights_result else []) or [])
        if weights_result is not None and not ic_weights:
            return []
        if not ic_weights:
            signal_agents = [
                agent_id
                for agent_id in context.upstream_results.keys()
                if agent_id not in {"agent_06_macro", "agent_11_backtester", "agent_13_risk"}
            ]
            equal = 1.0 / max(len(signal_agents), 1)
            ic_weights = {agent_id: equal for agent_id in signal_agents}
            active_signal_agents = set(signal_agents)

        macro_result = context.upstream_results.get("agent_06_macro")
        max_deploy = (macro_result.artifacts.get("max_deploy") if macro_result else None) or (1.0 - self.settings.market.min_cash_pct)
        risk_result = context.upstream_results.get("agent_13_risk")
        risk_artifacts = (risk_result.artifacts if risk_result else {}) or {}
        if risk_artifacts.get("hard_block"):
            return []
        max_deploy *= float(risk_artifacts.get("position_scale") or 1.0)
        if max_deploy <= 0:
            return []
        event_result = context.upstream_results.get("agent_10_events")
        event_map = (event_result.artifacts.get("event_map") if event_result else {}) or {}
        sector_result = context.upstream_results.get("agent_07_sector")
        sector_map = (sector_result.artifacts.get("sector_map") if sector_result else {}) or {}
        liquidity_result = context.upstream_results.get("agent_12_liquidity")
        liquidity_map = (liquidity_result.artifacts.get("liquidity_metrics") if liquidity_result else {}) or {}
        discovery_result = context.upstream_results.get("agent_00_discovery")
        macro_result = context.upstream_results.get("agent_06_macro")
        if (discovery_result and discovery_result.artifacts.get("provider_degraded")) or (macro_result and macro_result.artifacts.get("provider_degraded")):
            return []

        weighted_signal_sum: dict[str, float] = {}
        weight_sum: dict[str, float] = {}
        active_agent_weights: dict[str, dict[str, float]] = {}
        positive_support: dict[str, int] = {}
        for agent_id, result in context.upstream_results.items():
            if agent_id in {"agent_06_macro", "agent_11_backtester", "agent_13_risk"}:
                continue
            weight = ic_weights.get(agent_id, 0.0)
            if weight == 0:
                continue
            for ticker, score in result.scores_by_ticker.items():
                weighted_signal_sum[ticker] = weighted_signal_sum.get(ticker, 0.0) + (weight * score)
                weight_sum[ticker] = weight_sum.get(ticker, 0.0) + abs(weight)
                active_agent_weights.setdefault(ticker, {})[agent_id] = weight
                if score > 0:
                    positive_support[ticker] = positive_support.get(ticker, 0) + 1

        portfolio_value = max(context.portfolio.portfolio_value, 1.0)
        cash = context.portfolio.cash_balance
        deployable_capital = min(cash, portfolio_value * max_deploy)
        decisions: list[TradeDecision] = []
        current_positions = {row.ticker: row for row in self.repository.list_positions()}
        sector_allocations: dict[str, float] = {}
        position_sector_map: dict[str, str] = {row.ticker: row.sector for row in current_positions.values() if getattr(row, "sector", None)}
        for item in context.universe:
            if item.sector:
                position_sector_map[item.ticker] = item.sector
        for ticker, position in current_positions.items():
            price = context.price_bundle.get(ticker)
            latest_price = price.last_price if price and price.last_price is not None else None
            if latest_price is None and price and price.history:
                latest_price = price.history[-1].close
            current_value = position.shares * (latest_price or position.avg_entry_price)
            sector = position_sector_map.get(ticker, "UNKNOWN")
            sector_allocations[sector] = sector_allocations.get(sector, 0.0) + (current_value / portfolio_value)
        signal_agent_count = max(
            len(
                [
                    agent_id
                    for agent_id in (active_signal_agents or set(ic_weights))
                    if agent_id not in {"agent_06_macro", "agent_11_backtester", "agent_13_risk"}
                ]
            ),
            1,
        )
        banned_tickers = {str(ticker).upper() for ticker in context.runtime_overrides.get("banned_tickers", [])}
        quality_only = bool(context.runtime_overrides.get("quality_only"))
        memory_penalty_terms = ("primary_loss_cause", "contributing_loss", "reduce size", "avoid forcing directional")

        for ticker, position in current_positions.items():
            price = context.price_bundle.get(ticker)
            latest_price = price.last_price if price and price.last_price is not None else None
            if latest_price is None and price and price.history:
                latest_price = price.history[-1].close
            if latest_price is None:
                continue
            stop = position.stop_loss_price
            trailing = position.trailing_stop_price
            stop_hit = stop is not None and latest_price <= stop
            trailing_hit = trailing is not None and latest_price <= trailing
            event_blocked = bool(event_map.get(ticker, {}).get("event_block"))
            combined_signal = weighted_signal_sum.get(ticker)
            if stop_hit or trailing_hit or event_blocked or (combined_signal is not None and combined_signal < 0):
                decisions.append(
                    TradeDecision(
                        decision=DecisionType.SELL,
                        ticker=ticker,
                        position_type=PositionType(position.position_type),
                        target_weight=0.0,
                        shares=position.shares,
                        entry_policy=EntryPolicy(
                            fill_model="prev_session_hlc3",
                            valid_until=time.fromisoformat(self.settings.market.exit_window_close),
                        ),
                        stop_policy=StopPolicy(),
                        confidence=1.0 if (stop_hit or trailing_hit or event_blocked) else round(abs(combined_signal or 0.0), 4),
                        reason_code="portfolio_exit:stop_or_signal"
                        if (stop_hit or trailing_hit or (combined_signal is not None and combined_signal < 0))
                        else "portfolio_exit:event_block",
                        active_agent_weights=active_agent_weights.get(ticker, {}),
                    )
                )

        for item in sorted(context.universe, key=lambda candidate: weighted_signal_sum.get(candidate.ticker, -999), reverse=True):
            ticker = item.ticker
            if ticker.upper() in banned_tickers:
                continue
            if ticker in current_positions:
                continue
            if ticker not in weighted_signal_sum:
                continue
            if event_map.get(ticker, {}).get("event_block"):
                continue
            if positive_support.get(ticker, 0) < min(self.settings.market.min_positive_signal_agents, signal_agent_count):
                continue
            conviction = weighted_signal_sum[ticker] / max(weight_sum.get(ticker, 1.0), 1e-9)
            event_payload = event_map.get(ticker, {})
            conviction += float(event_payload.get("catalyst_score") or 0.0) * 0.1
            price = context.price_bundle.get(ticker)
            if not price or price.last_price is None:
                continue

            sector_multiplier = sector_map.get(item.sector or "", {}).get("weight_multiplier", 1.0)
            liquidity_adv = liquidity_map.get(ticker, {}).get("adv_20d_cr", item.adv_20d_cr or 0.0)
            liquidity_cap = min(self.settings.market.max_single_position_pct, max(0.01, (liquidity_adv / 1000) * 0.02)) if liquidity_adv else self.settings.market.max_single_position_pct
            dominant_agent = max(
                active_agent_weights.get(ticker, {}),
                key=lambda agent_id: abs(context.upstream_results[agent_id].scores_by_ticker.get(ticker, 0.0) * ic_weights.get(agent_id, 0.0)),
                default=None,
            )
            if dominant_agent:
                memory_text = str(context.memory_context.get(dominant_agent, "")).lower()
                if any(term in memory_text for term in memory_penalty_terms):
                    conviction *= 0.85
            guidance_text = " ".join(message.lower() for message in context.operator_guidance if ticker in message.upper())
            if guidance_text and any(term in guidance_text for term in ("watch", "review", "investigate")):
                conviction *= 0.8
            if conviction < self.settings.market.conviction_threshold:
                continue
            contributing_agents = active_agent_weights.get(ticker, {})
            weighted_stats = [
                (
                    abs(weight),
                    float((ic_snapshot.get(agent_id) or {}).get("win_rate") or 0.55),
                    float((ic_snapshot.get(agent_id) or {}).get("avg_rr") or 1.5),
                )
                for agent_id, weight in contributing_agents.items()
            ]
            stat_weight_total = sum(weight for weight, _, _ in weighted_stats) or 1.0
            win_rate = sum(weight * agent_win_rate for weight, agent_win_rate, _ in weighted_stats) / stat_weight_total
            avg_rr = sum(weight * agent_avg_rr for weight, _, agent_avg_rr in weighted_stats) / stat_weight_total
            kelly_fraction = 0.0
            if avg_rr > 0:
                kelly_fraction = max(0.0, ((win_rate * avg_rr) - (1 - win_rate)) / avg_rr) / 2
            base_weight = max(0.01, min(self.settings.market.max_single_position_pct, conviction * 0.05, kelly_fraction or conviction * 0.05))
            target_weight = min(self.settings.market.max_single_position_pct, base_weight * sector_multiplier, liquidity_cap)
            sector = item.sector or position_sector_map.get(ticker, "UNKNOWN")
            sector_room = max(0.0, self.settings.market.max_sector_exposure_pct - sector_allocations.get(sector, 0.0))
            target_weight = min(target_weight, sector_room)
            target_weight *= float(risk_artifacts.get("position_scale") or 1.0)
            budget = min(deployable_capital, portfolio_value * target_weight)
            shares = max(0, int(budget / max(price.last_price, 1.0)))
            if shares == 0:
                continue

            hard_stop = price.last_price * 0.93
            position_type = PositionType.QUALITY
            momentum_score = context.upstream_results.get("agent_03_momentum")
            reversion_score = context.upstream_results.get("agent_04_reversion")
            pairs_score = context.upstream_results.get("agent_05_pairs")
            if float(event_payload.get("catalyst_score") or 0.0) >= 0.6:
                position_type = PositionType.EVENT_DRIVEN
            elif pairs_score and pairs_score.scores_by_ticker.get(ticker, 0.0) > 0.4:
                position_type = PositionType.PAIRS
            elif reversion_score and reversion_score.scores_by_ticker.get(ticker, 0.0) > 0.5:
                position_type = PositionType.MEAN_REVERSION
            elif momentum_score and momentum_score.scores_by_ticker.get(ticker, 0.0) > 0.5:
                position_type = PositionType.MOMENTUM
            if quality_only and position_type is not PositionType.QUALITY:
                continue

            decisions.append(
                TradeDecision(
                    decision=DecisionType.BUY,
                    ticker=ticker,
                    position_type=position_type,
                    target_weight=round(target_weight, 4),
                    shares=shares,
                    entry_policy=EntryPolicy(
                        fill_model="prev_session_hlc3",
                        valid_until=time.fromisoformat(self.settings.market.entry_window_close),
                    ),
                    stop_policy=StopPolicy(hard_stop_price=round(hard_stop, 4), trailing_stop_price=None),
                    confidence=round(conviction, 4),
                    reason_code=f"ic_weighted_conviction:{dominant_agent or 'blended'}",
                    active_agent_weights=active_agent_weights.get(ticker, {}),
                )
            )
            deployable_capital -= shares * price.last_price
            sector_allocations[sector] = sector_allocations.get(sector, 0.0) + target_weight
            if deployable_capital <= 0:
                break
        return decisions


def build_agent_registry(settings: Settings, repository: QuantRepository, gemini: CLIProxyGateway | None = None) -> tuple[dict[str, BaseAgent], BossAgent]:
    _ = gemini
    screener = ScreenerClient(
        command=settings.screener.binary_path,
        working_directory=settings.project_root,
        timeout_seconds=settings.screener.timeout_seconds,
        retries=settings.screener.retries,
    )
    market_data = YFinanceClient()
    exa = ExaClient(api_keys=settings.exa.api_keys, base_url=settings.exa.base_url, timeout=settings.exa.timeout_seconds)
    exa.configure_budget("agent_09_sentiment", daily_limit=settings.exa.daily_budget_per_agent)
    exa.configure_budget("agent_10_events", daily_limit=settings.exa.daily_budget_per_agent)
    rss = RSSClient(settings.news.rss_feeds)
    nse = NSEClient()
    agents: dict[str, BaseAgent] = {
        "agent_00_discovery": UniverseDiscoveryAgent(nse=nse, market_data=market_data),
        "agent_01_universe": UniverseAgent(screener=screener, settings=settings, nse=nse),
        "agent_02_quality": QualityAgent(screener=screener),
        "agent_06_macro": MacroAgent(nse=nse, market_data=market_data),
        "agent_10_events": EventAgent(exa=exa, rss=rss, nse=nse),
        "agent_09_sentiment": SentimentAgent(exa=exa, rss=rss),
        "agent_07_sector": SectorAgent(market_data=market_data),
        "agent_08_ownership": OwnershipAgent(nse=nse, screener=screener),
        "agent_13_risk": RiskAgent(market_data=market_data, repository=repository),
        "agent_03_momentum": MomentumAgent(market_data=market_data),
        "agent_04_reversion": ReversionAgent(market_data=market_data),
        "agent_05_pairs": PairsAgent(market_data=market_data, validated_pairs_path=settings.data_dir / "validated_pairs.json"),
        "agent_12_liquidity": LiquidityAgent(market_data=market_data),
        "agent_11_backtester": BacktesterAgent(repository=repository),
    }
    return agents, BossAgent(repository=repository, settings=settings)

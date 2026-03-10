from __future__ import annotations

import json
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from quant_trading.agents.core import (
    BacktesterAgent,
    BossAgent,
    EventAgent,
    MacroAgent,
    MomentumAgent,
    OwnershipAgent,
    PairsAgent,
    QualityAgent,
    ReversionAgent,
    SentimentAgent,
    UniverseAgent,
    UniverseDiscoveryAgent,
)
from quant_trading.config import ScreenerSettings, Settings
from quant_trading.db.repository import QuantRepository
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.schemas import (
    AgentResult,
    AgentStatus,
    DecisionType,
    MarketContext,
    PortfolioSnapshot,
    PositionType,
    PriceBar,
    PriceData,
    SessionState,
    UniverseDiscoveryPlan,
    UniverseItem,
)


def build_context(universe: list[UniverseItem] | None = None, upstream_results: dict[str, AgentResult] | None = None) -> MarketContext:
    now = datetime.now(UTC)
    return MarketContext(
        run_id="run-1",
        timestamp_utc=now,
        market="NSE",
        date=now.date(),
        time_ist=time(10, 0),
        session_state=SessionState.OPEN,
        is_market_day=True,
        portfolio=PortfolioSnapshot(cash_balance=1_000_000.0, total_deployed=0.0, portfolio_value=1_000_000.0),
        universe=universe or [],
        price_bundle={},
        memory_context={},
        upstream_results=upstream_results or {},
    )


class DummyScreenerClient:
    def fetch_query(self, query, **kwargs):
        _ = query, kwargs
        return {
            "items": [
                {
                    "data": {
                        "symbol": "RELIANCE",
                        "name": "Reliance Industries",
                        "sector": "Energy",
                        "top_ratios": {
                            "Market Cap Cr": "1800000",
                            "ADV 20D Cr": "1200",
                            "DE Ratio": "0.4",
                            "Years Listed": "12",
                            "Cash from operations": "25000",
                            "Cash from operations prev": "22000",
                            "ROE": "12",
                            "ROCE": "15",
                            "Current Ratio": "1.3",
                        },
                    }
                }
            ]
        }

    def fetch_company(self, symbol_or_url, **kwargs):
        _ = kwargs
        return {
            "symbol": str(symbol_or_url).upper(),
            "top_ratios": {
                "ROE": "20",
                "ROCE": "24",
                "Current Ratio": "1.6",
                "Debt to equity": "0.2",
            },
            "financials": {
                "roa": [{"value": 12}, {"value": 9}],
                "operating_cash_flow": [{"value": 1700}, {"value": 1500}],
                "total_assets": {"value": 5000},
                "current_ratio": [{"value": 1.6}, {"value": 1.3}],
                "gross_margin": [{"value": 52}, {"value": 48}],
                "asset_turnover": [{"value": 1.25}, {"value": 1.05}],
                "shares_outstanding": [{"value": 100}, {"value": 100}],
                "long_term_debt_ratio": [{"value": 0.12}, {"value": 0.18}],
                "enterprise_value": {"value": 15000},
                "ebit": {"value": 3200},
                "net_fixed_assets": {"value": 2400},
                "working_capital": {"value": 800},
            },
            "shareholding": {
                "promoter_holding": [{"value": 72}, {"value": 70}],
                "fii_holding": [{"value": 17}, {"value": 16}],
                "dii_holding": [{"value": 9}, {"value": 8}],
                "promoter_pledging": {"value": 0},
            },
        }


class DummyNSEClient:
    def __init__(self, rows):
        self.rows = rows

    def get_fii_dii_data(self):
        return self.rows

    def get_corporate_actions(self, symbol: str):
        _ = symbol
        return []

    def get_bulk_deals(self, symbol: str):
        _ = symbol
        return []

    def get_block_deals(self, symbol: str):
        _ = symbol
        return []

    def get_latest_circulars(self):
        return []

    def get_asm_list(self):
        return []

    def get_gsm_list(self):
        return []

    def get_circuit_breaker_list(self):
        return []


class DummyRSSClient:
    def __init__(self, rows=None):
        self.rows = rows or []

    def search(self, query: str, limit: int = 3):
        _ = query, limit
        return list(self.rows)


class DummyExaClient:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.api_keys = ["dummy"]

    def search(self, agent_id: str, query: str, num_results: int = 3):
        _ = agent_id, query, num_results
        return list(self.rows)


def build_repository() -> QuantRepository:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return QuantRepository(engine, session_factory)


class PriceAgentMarketData:
    def __init__(self, series: dict[str, list[float]], latest: dict[str, float] | None = None) -> None:
        self.series = series
        self.latest = latest or {}

    def latest_price(self, ticker: str) -> float | None:
        return self.latest.get(ticker)

    def load_price_data(self, ticker: str, period: str = "1y") -> PriceData:
        _ = period
        closes = self.series[ticker]
        start = datetime(2025, 1, 1, tzinfo=UTC)
        bars: list[PriceBar] = []
        for idx, close in enumerate(closes):
            when = start + timedelta(days=idx)
            bars.append(
                PriceBar(
                    open=close * 0.99,
                    high=close * 1.01,
                    low=close * 0.98,
                    close=close,
                    volume=1_000_000 + (idx * 1000),
                    as_of=when,
                )
            )
        return PriceData(ticker=ticker, last_price=closes[-1], previous_bar=bars[-1], history=bars)


def test_universe_agent_parses_and_filters_screener_payload() -> None:
    settings = Settings(screener=ScreenerSettings(binary_path=str(Path("/tmp/screener"))))
    agent = UniverseAgent(screener=DummyScreenerClient(), settings=settings)
    result = agent.run(build_context())
    universe = result.artifacts["universe"]
    assert result.status == AgentStatus.SUCCESS
    assert len(universe) == 1
    assert UniverseItem.model_validate(universe[0]).ticker == "RELIANCE"


def test_universe_agent_requests_targeted_screener_fields() -> None:
    class RecordingScreener(DummyScreenerClient):
        def __init__(self) -> None:
            self.calls = []

        def fetch_query(self, query, **kwargs):
            self.calls.append((query, kwargs))
            return super().fetch_query(query, **kwargs)

    settings = Settings(screener=ScreenerSettings(binary_path=str(Path("/tmp/screener"))))
    screener = RecordingScreener()
    agent = UniverseAgent(screener=screener, settings=settings)

    agent.run(build_context())

    assert screener.calls
    assert "market_cap" in screener.calls[0][1]["fields"]
    assert "cash_flow" in screener.calls[0][1]["fields"]
    assert "market_cap >=" in screener.calls[0][0]


def test_universe_discovery_agent_selects_tight_profile_in_risk_on_conditions() -> None:
    market_data = PriceAgentMarketData(
        series={"^NSEI": [float(100 + idx) for idx in range(250)]},
        latest={"^INDIAVIX": 12.0},
    )
    nse = DummyNSEClient([{"netValue": 500.0}] * 5)
    agent = UniverseDiscoveryAgent(nse=nse, market_data=market_data)

    result = agent.run(build_context())
    discovery = result.artifacts["universe_discovery"]

    assert discovery["selected_profile"] == "tight"
    assert discovery["market_regime"] == "risk_on"
    assert discovery["query_ladder"][0].startswith("market_cap >=")


def test_universe_agent_broadens_when_primary_query_is_too_small() -> None:
    class FallbackScreener(DummyScreenerClient):
        def __init__(self) -> None:
            self.queries: list[str] = []

        def fetch_query(self, query, **kwargs):
            self.queries.append(query)
            if ">= 1000" in query:
                return {
                    "items": [
                        {
                            "data": {
                                "symbol": "AARTIIND",
                                "name": "Aarti Industries",
                                "sector": "Chemicals",
                                "top_ratios": {
                                    "Market Cap Cr": "1200",
                                    "ADV 20D Cr": "150",
                                    "DE Ratio": "0.6",
                                    "Years Listed": "8",
                                    "Cash from operations": "800",
                                    "Cash from operations prev": "650",
                                },
                            }
                        }
                    ]
                }
            return {
                "items": [
                    {
                            "data": {
                                "symbol": f"STOCK{idx}",
                                "name": f"Stock {idx}",
                                "sector": "Chemicals",
                                "top_ratios": {
                                    "Market Cap Cr": str(1_000 + idx),
                                    "ADV 20D Cr": "120",
                                    "DE Ratio": "0.3",
                                    "Years Listed": "10",
                                    "Cash from operations": "900",
                                    "Cash from operations prev": "850",
                                },
                            }
                        }
                        for idx in range(25)
                    ]
                }

    screener = FallbackScreener()
    settings = Settings(screener=ScreenerSettings(binary_path=str(Path("/tmp/screener"))))
    agent = UniverseAgent(screener=screener, settings=settings)
    context = build_context()
    context = context.model_copy(
        update={
            "universe_discovery": UniverseDiscoveryPlan(
                status="selected",
                market_regime="risk_on",
                selected_profile="tight",
                profile_ladder=["tight", "standard", "broad"],
                query_ladder=[
                    "market_cap >= 1000 AND market_cap <= 15000",
                    "market_cap >= 750 AND market_cap <= 30000",
                    "market_cap >= 500 AND market_cap <= 50000",
                ],
            ),
        }
    )

    result = agent.run(context)

    assert result.artifacts["universe_size"] == 25
    assert result.artifacts["universe_discovery"]["fallback_level"] == 1
    assert result.artifacts["universe_discovery"]["final_profile"] == "standard"
    assert len(screener.queries) == 2


def test_quality_agent_scores_items_from_ratios() -> None:
    agent = QualityAgent()
    universe = [
        UniverseItem(
            ticker="RELIANCE",
            sector="Energy",
            metadata={
                "top_ratios": {
                    "ROE": "22",
                    "ROCE": "26",
                    "Debt to equity": "0.2",
                    "Dividend Yield": "2.0",
                }
            },
        )
    ]
    result = agent.run(build_context(universe=universe))
    assert result.scores_by_ticker["RELIANCE"] > 0.0


def test_quality_agent_hydrates_sparse_company_data_from_screener() -> None:
    agent = QualityAgent(screener=DummyScreenerClient())
    universe = [
        UniverseItem(
            ticker="INFY",
            sector="IT",
            metadata={"raw": {"top_ratios": {"ROE": "18"}}, "top_ratios": {"ROE": "18"}},
        )
    ]

    result = agent.run(build_context(universe=universe))

    assert result.scores_by_ticker["INFY"] > 0.0
    qualified = result.artifacts["qualified_universe"][0]
    assert qualified["metadata"]["raw"]["shareholding"]["promoter_holding"][0]["value"] == 72


def test_quality_agent_requests_targeted_screener_fields_on_hydration() -> None:
    class RecordingScreener(DummyScreenerClient):
        def __init__(self) -> None:
            self.calls = []

        def fetch_company(self, symbol_or_url, **kwargs):
            self.calls.append(kwargs)
            return super().fetch_company(symbol_or_url, **kwargs)

    screener = RecordingScreener()
    agent = QualityAgent(screener=screener)
    universe = [UniverseItem(ticker="INFY", metadata={"raw": {}, "top_ratios": {}})]

    agent.run(build_context(universe=universe))

    assert screener.calls
    assert "tables" in screener.calls[0]["fields"]
    assert "enterprise_value" in screener.calls[0]["fields"]


def test_quality_agent_uses_nested_statement_fields_for_piotroski_style_scoring() -> None:
    agent = QualityAgent()
    universe = [
        UniverseItem(
            ticker="TCS",
            sector="IT",
            metadata={
                "raw": {
                    "financials": {
                        "roa": [{"value": 14}, {"value": 11}],
                        "operating_cash_flow": [{"value": 1800}, {"value": 1500}],
                        "total_assets": {"value": 5000},
                        "current_ratio": [{"value": 1.8}, {"value": 1.4}],
                        "gross_margin": [{"value": 54}, {"value": 49}],
                        "asset_turnover": [{"value": 1.3}, {"value": 1.0}],
                        "shares_outstanding": [{"value": 100}, {"value": 100}],
                        "long_term_debt_ratio": [{"value": 0.1}, {"value": 0.2}],
                        "enterprise_value": {"value": 15000},
                        "ebit": {"value": 3200},
                        "net_fixed_assets": {"value": 2400},
                        "working_capital": {"value": 800},
                    },
                    "shareholding": {
                        "promoter_holding": [{"value": 72}, {"value": 70}],
                        "fii_holding": [{"value": 17}, {"value": 16}, {"value": 15}],
                        "dii_holding": [{"value": 9}, {"value": 8}, {"value": 7}],
                    },
                }
            },
        )
    ]
    result = agent.run(build_context(universe=universe))
    assert result.scores_by_ticker["TCS"] > 0.0
    assert result.artifacts["breakdown"]["TCS"]["f_score"] >= 6
    assert result.artifacts["breakdown"]["TCS"]["quality_score"] > 50


def test_quality_agent_uses_screener_tables_for_statement_math() -> None:
    agent = QualityAgent()
    universe = [
        UniverseItem(
            ticker="HDFCBANK",
            sector="Banking",
            metadata={
                "raw": {
                    "tables": [
                        {
                            "name": "Cash Flow",
                            "headers": ["", "Mar 2025", "Mar 2024"],
                            "rows": [["Cash from Operating Activity +", "1800", "1500"]],
                        },
                        {
                            "name": "Balance Sheet",
                            "headers": ["", "Mar 2025", "Mar 2024"],
                            "rows": [
                                ["Total Assets", "5000", "4500"],
                                ["Borrowings +", "400", "500"],
                                ["Equity Share Capital", "100", "100"],
                                ["Net Block", "2400", "2200"],
                                ["Working Capital", "800", "700"],
                            ],
                        },
                        {
                            "name": "Profit & Loss",
                            "headers": ["", "Mar 2025", "Mar 2024"],
                            "rows": [
                                ["Sales +", "7000", "6000"],
                                ["Operating Profit", "1400", "1080"],
                                ["OPM %", "20", "18"],
                            ],
                        },
                        {
                            "name": "Shareholding Pattern",
                            "headers": ["", "Dec 2025", "Sep 2025", "Jun 2025"],
                            "rows": [
                                ["Promoters", "72", "70", "69"],
                                ["FIIs", "17", "16", "15"],
                                ["DIIs", "9", "8", "7"],
                            ],
                        },
                    ]
                },
                "top_ratios": {
                    "ROE": "20",
                    "ROCE": "24",
                    "Current Ratio": "1.6",
                    "Enterprise Value": "15000",
                },
            },
        )
    ]

    result = agent.run(build_context(universe=universe))

    assert result.scores_by_ticker["HDFCBANK"] > 0.0
    assert result.artifacts["breakdown"]["HDFCBANK"]["f_score"] >= 6
    assert result.artifacts["breakdown"]["HDFCBANK"]["ey"] > 0


def test_ownership_agent_uses_holding_deltas_and_deal_flow() -> None:
    class FlowNSE(DummyNSEClient):
        def get_bulk_deals(self, symbol: str):
            _ = symbol
            return [{"buySell": "BUY", "quantity": 2_000_000}]

    agent = OwnershipAgent(nse=FlowNSE(rows=[]))
    universe = [
        UniverseItem(
            ticker="INFY",
            metadata={
                "raw": {
                    "shareholding": {
                        "promoter_holding": [{"value": 62}, {"value": 60}],
                        "fii_holding": [{"value": 24}, {"value": 22}],
                        "dii_holding": [{"value": 12}, {"value": 10}],
                        "promoter_pledging": {"value": 0},
                    }
                }
            },
        )
    ]
    result = agent.run(build_context(universe=universe))
    assert result.scores_by_ticker["INFY"] > 0.0
    assert result.artifacts["ownership_breakdown"]["INFY"]["flow_signal"] > 0


def test_ownership_agent_hydrates_missing_shareholding_from_screener() -> None:
    agent = OwnershipAgent(nse=DummyNSEClient(rows=[]), screener=DummyScreenerClient())
    universe = [UniverseItem(ticker="TCS", metadata={"raw": {}, "top_ratios": {}})]

    result = agent.run(build_context(universe=universe))

    assert result.scores_by_ticker["TCS"] > 0.0
    assert result.artifacts["ownership_breakdown"]["TCS"]["promoter_holding"] == 72


def test_ownership_agent_requests_targeted_screener_fields_on_hydration() -> None:
    class RecordingScreener(DummyScreenerClient):
        def __init__(self) -> None:
            self.calls = []

        def fetch_company(self, symbol_or_url, **kwargs):
            self.calls.append(kwargs)
            return super().fetch_company(symbol_or_url, **kwargs)

    screener = RecordingScreener()
    agent = OwnershipAgent(nse=DummyNSEClient(rows=[]), screener=screener)
    universe = [UniverseItem(ticker="TCS", metadata={"raw": {}, "top_ratios": {}})]

    agent.run(build_context(universe=universe))

    assert screener.calls
    assert "promoter_holding" in screener.calls[0]["fields"]
    assert "investors" in screener.calls[0]["fields"]


def test_ownership_agent_uses_shareholding_table_when_flat_ratios_missing() -> None:
    agent = OwnershipAgent(nse=DummyNSEClient(rows=[]))
    universe = [
        UniverseItem(
            ticker="SBIN",
            metadata={
                "raw": {
                    "tables": [
                        {
                            "name": "Shareholding Pattern",
                            "headers": ["", "Dec 2025", "Sep 2025"],
                            "rows": [
                                ["Promoters", "57", "56"],
                                ["FIIs", "11", "9"],
                                ["DIIs", "24", "23"],
                            ],
                        }
                    ]
                },
                "top_ratios": {},
            },
        )
    ]

    result = agent.run(build_context(universe=universe))

    assert result.scores_by_ticker["SBIN"] > 0.0
    assert result.artifacts["ownership_breakdown"]["SBIN"]["promoter_delta"] == 1.0
    assert result.artifacts["ownership_breakdown"]["SBIN"]["fii_delta"] == 2.0


def test_event_agent_blocks_upcoming_earnings_window_from_structured_action() -> None:
    class EventNSE(DummyNSEClient):
        def get_corporate_actions(self, symbol: str):
            _ = symbol
            return [{"purpose": "Quarterly Results", "date": datetime.now(UTC).date().isoformat()}]

    agent = EventAgent(exa=DummyExaClient(), rss=DummyRSSClient(), nse=EventNSE(rows=[]))
    universe = [UniverseItem(ticker="RELIANCE", company="Reliance Industries")]
    result = agent.run(build_context(universe=universe))
    assert result.artifacts["event_map"]["RELIANCE"]["event_block"] is True
    assert "earnings" in result.artifacts["event_map"]["RELIANCE"]["block_reason"]


def test_event_agent_blocks_recent_regulatory_risk_from_circulars() -> None:
    class CircularNSE(DummyNSEClient):
        def get_latest_circulars(self):
            return [
                {
                    "title": "SEBI investigation opened against Reliance Industries subsidiaries",
                    "published": datetime.now(UTC).date().isoformat(),
                }
            ]

    agent = EventAgent(exa=DummyExaClient(), rss=DummyRSSClient(), nse=CircularNSE(rows=[]))
    universe = [UniverseItem(ticker="RELIANCE", company="Reliance Industries")]

    result = agent.run(build_context(universe=universe))

    assert result.artifacts["event_map"]["RELIANCE"]["event_block"] is True
    assert result.artifacts["event_map"]["RELIANCE"]["block_reason"] == "regulatory_or_governance_risk"
    assert result.artifacts["event_map"]["RELIANCE"]["circular_count"] == 1


def test_event_agent_flags_buyback_as_positive_catalyst_when_not_blocked() -> None:
    rss = DummyRSSClient(rows=[{"title": "Infosys announces buyback plan after strong quarter"}])
    agent = EventAgent(exa=DummyExaClient(), rss=rss, nse=DummyNSEClient(rows=[]))
    universe = [UniverseItem(ticker="INFY", company="Infosys")]

    result = agent.run(build_context(universe=universe))

    assert result.artifacts["event_map"]["INFY"]["event_block"] is False
    assert result.artifacts["event_map"]["INFY"]["catalyst_type"] == "buyback"
    assert result.artifacts["event_map"]["INFY"]["catalyst_score"] >= 0.7


def test_event_agent_blocks_immediate_post_results_window() -> None:
    class RecentResultsNSE(DummyNSEClient):
        def get_corporate_actions(self, symbol: str):
            _ = symbol
            yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
            return [{"purpose": "Quarterly Results", "date": yesterday}]

    agent = EventAgent(exa=DummyExaClient(), rss=DummyRSSClient(), nse=RecentResultsNSE(rows=[]))
    universe = [UniverseItem(ticker="INFY", company="Infosys")]

    result = agent.run(build_context(universe=universe))

    assert result.artifacts["event_map"]["INFY"]["event_block"] is True
    assert result.artifacts["event_map"]["INFY"]["block_reason"].startswith("earnings_recent_")


def test_event_agent_uses_post_earnings_drift_window_for_positive_surprise() -> None:
    class DriftNSE(DummyNSEClient):
        def get_corporate_actions(self, symbol: str):
            _ = symbol
            past = (datetime.now(UTC) - timedelta(days=5)).date().isoformat()
            return [{"purpose": "Quarterly Results", "date": past}]

    rss = DummyRSSClient(rows=[{"title": "Infosys beats estimates by 12%", "published": datetime.now(UTC).date().isoformat()}])
    agent = EventAgent(exa=DummyExaClient(), rss=rss, nse=DriftNSE(rows=[]))
    universe = [UniverseItem(ticker="INFY", company="Infosys")]

    result = agent.run(build_context(universe=universe))

    assert result.artifacts["event_map"]["INFY"]["event_block"] is False
    assert result.artifacts["event_map"]["INFY"]["catalyst_type"] == "post_earnings_drift"
    assert result.artifacts["event_map"]["INFY"]["catalyst_score"] >= 0.8


def test_event_agent_collects_source_counts_and_evidence_from_exa_queries() -> None:
    class RecordingExa(DummyExaClient):
        def __init__(self):
            super().__init__(rows=[])
            self.queries = []

        def search(self, agent_id: str, query: str, num_results: int = 3):
            self.queries.append(query)
            if "SEBI" in query:
                return [{"title": "TCS faces SEBI investigation notice", "published": datetime.now(UTC).date().isoformat()}]
            if "buyback" in query:
                return [{"title": "TCS announces buyback after board approval", "published": datetime.now(UTC).date().isoformat()}]
            return [{"title": "TCS beats estimates by 12%", "published": datetime.now(UTC).date().isoformat()}]

    exa = RecordingExa()
    agent = EventAgent(exa=exa, rss=DummyRSSClient(rows=[]), nse=DummyNSEClient(rows=[]))
    universe = [UniverseItem(ticker="TCS", company="Tata Consultancy Services")]

    result = agent.run(build_context(universe=universe))
    event = result.artifacts["event_map"]["TCS"]

    assert len(exa.queries) >= 2
    assert event["source_counts"]["exa"] >= 2
    assert event["event_block"] is True
    assert event["regulatory_evidence"]


def test_sentiment_agent_ignores_stale_articles_and_decays_recent_ones() -> None:
    agent = SentimentAgent(
        exa=DummyExaClient(),
        rss=DummyRSSClient(
            rows=[
                {"title": "Infosys wins major cloud contract", "published": datetime.now(UTC).date().isoformat()},
                {"title": "Infosys buyback rumors", "published": datetime.now(UTC).date().isoformat()},
                {"title": "Infosys fraud probe", "published": "2026-02-20"},
            ]
        ),
    )
    universe = [UniverseItem(ticker="INFY", company="Infosys")]

    result = agent.run(build_context(universe=universe))
    payload = result.artifacts["sentiment_map"]["INFY"]

    assert result.scores_by_ticker["INFY"] > 0
    assert payload["fresh_article_count"] == 2
    assert payload["stale_article_count"] == 1


def test_macro_agent_classifies_negative_flow_as_caution() -> None:
    market_data = PriceAgentMarketData(series={"^NSEI": [float(100 + idx) for idx in range(250)]}, latest={"^INDIAVIX": 18.0})
    agent = MacroAgent(nse=DummyNSEClient(rows=[{"netValue": "-2500"}]), market_data=market_data)
    result = agent.run(build_context())
    assert result.artifacts["regime"] == "CAUTION"


def test_momentum_agent_disables_signal_when_vix_is_high() -> None:
    stock_series = [100 + (idx * 0.6) for idx in range(260)]
    benchmark_series = [100 + (idx * 0.3) for idx in range(260)]
    market_data = PriceAgentMarketData({"INFY.NS": stock_series, "^NSEI": benchmark_series}, latest={"^INDIAVIX": 31.0})
    agent = MomentumAgent(market_data=market_data)
    context = build_context(universe=[UniverseItem(ticker="INFY")]).model_copy(update={"regime": "NEUTRAL"})

    result = agent.run(context)

    assert result.scores_by_ticker["INFY"] == 0.0
    assert result.artifacts["momentum_breakdown"]["INFY"]["india_vix"] == 31.0
    assert result.artifacts["momentum_breakdown"]["INFY"]["crash_mode"] == 1.0


def test_reversion_agent_marks_entry_zone_and_stop_breach() -> None:
    entry_closes = [100.0] * 56 + [96.0, 94.0, 92.0, 90.0]
    stop_closes = [100.0] * 59 + [40.0]
    market_data = PriceAgentMarketData({"ENTRY.NS": entry_closes, "STOP.NS": stop_closes})
    agent = ReversionAgent(market_data=market_data)
    context = build_context(universe=[UniverseItem(ticker="ENTRY"), UniverseItem(ticker="STOP")])

    result = agent.run(context)

    assert result.artifacts["reversion_breakdown"]["ENTRY"]["entry_zone"] == 1.0
    assert result.scores_by_ticker["ENTRY"] > 0
    assert result.artifacts["reversion_breakdown"]["STOP"]["stop_breach"] == 1.0
    assert result.scores_by_ticker["STOP"] < 0


def test_pairs_agent_uses_validated_pair_metadata_and_long_only_zones(tmp_path: Path) -> None:
    validated = {
        "pairs": [
            {"cheap": "CHEAP", "rich": "RICH", "beta": 1.0, "alpha": 0.0, "half_life": 8.0, "adf_pvalue": 0.01, "valid": True},
            {"cheap": "BROKEN", "rich": "ANCHOR", "beta": 1.0, "alpha": 0.0, "half_life": 9.0, "adf_pvalue": 0.02, "valid": True},
        ]
    }
    path = tmp_path / "validated_pairs.json"
    path.write_text(json.dumps(validated))

    entry_spread = [0.0] * 40 + [(-0.001 * idx) for idx in range(20)]
    stop_spread = [0.0] * 59 + [-0.005]
    rich_closes = [100.0] * 60
    cheap_closes = [100.0 * (2.718281828 ** spread) for spread in entry_spread]
    broken_closes = [100.0 * (2.718281828 ** spread) for spread in stop_spread]
    market_data = PriceAgentMarketData(
        {
            "CHEAP.NS": cheap_closes,
            "RICH.NS": rich_closes,
            "BROKEN.NS": broken_closes,
            "ANCHOR.NS": rich_closes,
        }
    )
    agent = PairsAgent(market_data=market_data, validated_pairs_path=path)
    context = build_context(
        universe=[
            UniverseItem(ticker="CHEAP"),
            UniverseItem(ticker="RICH"),
            UniverseItem(ticker="BROKEN"),
            UniverseItem(ticker="ANCHOR"),
        ]
    )

    result = agent.run(context)

    assert result.scores_by_ticker["CHEAP"] > 0
    assert result.artifacts["pairs_breakdown"]["CHEAP"]["entry_zone"] == 1.0
    assert result.artifacts["pairs_breakdown"]["CHEAP"]["half_life"] == 8.0
    assert result.scores_by_ticker["BROKEN"] < 0
    assert result.artifacts["pairs_breakdown"]["BROKEN"]["stop_breach"] == 1.0


def test_boss_emits_buy_when_conviction_clears_threshold() -> None:
    repository = build_repository()
    boss = BossAgent(repository=repository, settings=Settings())
    upstream = {
        "agent_02_quality": AgentResult(
            agent_id="agent_02_quality",
            run_id="run-1",
            status=AgentStatus.SUCCESS,
            scores_by_ticker={"RELIANCE": 0.8},
            artifacts={},
            warnings=[],
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        ),
        "agent_03_momentum": AgentResult(
            agent_id="agent_03_momentum",
            run_id="run-1",
            status=AgentStatus.SUCCESS,
            scores_by_ticker={"RELIANCE": 0.7},
            artifacts={},
            warnings=[],
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        ),
    }
    context = build_context(
        universe=[UniverseItem(ticker="RELIANCE")],
        upstream_results=upstream,
    )
    context = context.model_copy(
        update={
            "price_bundle": {
                "RELIANCE": PriceData(
                    ticker="RELIANCE",
                    last_price=100.0,
                    previous_bar=PriceBar(
                        open=98.0,
                        high=101.0,
                        low=97.0,
                        close=100.0,
                        volume=1_000_000,
                        as_of=datetime.now(UTC),
                    ),
                )
            }
        }
    )
    decisions = boss.run(context)
    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.BUY


def test_boss_marks_event_driven_when_catalyst_is_strong() -> None:
    repository = build_repository()
    boss = BossAgent(repository=repository, settings=Settings())
    now = datetime.now(UTC)
    upstream = {
        "agent_02_quality": AgentResult(
            agent_id="agent_02_quality",
            run_id="run-1",
            status=AgentStatus.SUCCESS,
            scores_by_ticker={"INFY": 0.72},
            artifacts={},
            warnings=[],
            started_at=now,
            finished_at=now,
        ),
        "agent_03_momentum": AgentResult(
            agent_id="agent_03_momentum",
            run_id="run-1",
            status=AgentStatus.SUCCESS,
            scores_by_ticker={"INFY": 0.68},
            artifacts={},
            warnings=[],
            started_at=now,
            finished_at=now,
        ),
        "agent_10_events": AgentResult(
            agent_id="agent_10_events",
            run_id="run-1",
            status=AgentStatus.SUCCESS,
            scores_by_ticker={},
            artifacts={"event_map": {"INFY": {"event_block": False, "catalyst_score": 0.8, "catalyst_type": "buyback"}}},
            warnings=[],
            started_at=now,
            finished_at=now,
        ),
        "agent_11_backtester": AgentResult(
            agent_id="agent_11_backtester",
            run_id="run-1",
            status=AgentStatus.SUCCESS,
            scores_by_ticker={},
            artifacts={
                "ic_weights": {"agent_02_quality": 0.5, "agent_03_momentum": 0.5},
                "active_signal_agents": ["agent_02_quality", "agent_03_momentum"],
                "ic_snapshot": {
                    "agent_02_quality": {"win_rate": 0.58, "avg_rr": 1.8, "active": True},
                    "agent_03_momentum": {"win_rate": 0.57, "avg_rr": 1.7, "active": True},
                },
            },
            warnings=[],
            started_at=now,
            finished_at=now,
        ),
    }
    context = build_context(universe=[UniverseItem(ticker="INFY")], upstream_results=upstream)
    context = context.model_copy(
        update={
            "price_bundle": {
                "INFY": PriceData(
                    ticker="INFY",
                    last_price=100.0,
                    previous_bar=PriceBar(
                        open=99.0,
                        high=101.0,
                        low=98.0,
                        close=100.0,
                        volume=1_000_000,
                        as_of=now,
                    ),
                )
            }
        }
    )

    decisions = boss.run(context)

    assert len(decisions) == 1
    assert decisions[0].position_type == PositionType.EVENT_DRIVEN
    assert decisions[0].reason_code.startswith("ic_weighted_conviction:")


def test_backtester_agent_reports_dormant_signals_from_ic_snapshot() -> None:
    repository = build_repository()
    repository.replace_ic_history(
        ic_date=datetime.now(UTC).date(),
        rows=[
            {
                "agent_id": "agent_03_momentum",
                "ic_value": 0.06,
                "win_rate": 0.58,
                "avg_rr": 1.7,
                "details": {"sample_size": 45, "active": True, "ic_weight": 0.7, "ic_10d": 0.04, "decay_lambda": 0.08},
            },
            {
                "agent_id": "agent_09_sentiment",
                "ic_value": 0.02,
                "win_rate": 0.51,
                "avg_rr": 1.1,
                "details": {"sample_size": 12, "active": False, "ic_weight": 0.0, "ic_10d": 0.01},
            },
        ],
    )

    agent = BacktesterAgent(repository=repository)
    result = agent.run(build_context())

    assert result.artifacts["active_signal_agents"] == ["agent_03_momentum"]
    assert "agent_09_sentiment" in result.artifacts["dormant_signal_agents"]
    assert result.artifacts["ic_decay"]["agent_03_momentum"] == 0.08

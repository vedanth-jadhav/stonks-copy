from __future__ import annotations

from quant_trading.agents import build_agent_registry
from quant_trading.config import Settings, get_settings
from quant_trading.db.repository import QuantRepository
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.orchestrator import Orchestrator
from quant_trading.tools.cliproxy import CLIProxyGateway
from quant_trading.tools.yfinance_client import YFinanceClient
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quant_trading.web.gemini_oauth import GeminiOAuthManager


def build_runtime() -> tuple[Settings, QuantRepository, Orchestrator, GeminiOAuthManager]:
    from quant_trading.web.gemini_oauth import GeminiOAuthManager

    settings = get_settings()
    engine, session_factory = create_engine_and_sessionmaker(settings.database.url)
    init_db(engine, session_factory)
    repository = QuantRepository(engine, session_factory)
    gemini_oauth = GeminiOAuthManager(settings=settings)
    gemini = CLIProxyGateway(
        timeout=settings.cliproxy.timeout_seconds,
        connection_resolver=lambda: gemini_oauth.runtime_connection(start_service=True),
    )
    try:
        if gemini.is_configured():
            gemini.validate_aliases(settings.cliproxy.model_aliases)
    except Exception:
        pass
    agents, boss = build_agent_registry(settings=settings, repository=repository, gemini=gemini)
    orchestrator = Orchestrator(
        repository=repository,
        agents=agents,
        boss=boss,
        market_data=YFinanceClient(),
        gateway=gemini,
    )
    return settings, repository, orchestrator, gemini_oauth


def run_once() -> None:
    _, _, orchestrator, _ = build_runtime()
    orchestrator.startup_recovery()
    orchestrator.run_pipeline(trigger="bootstrap")


def main() -> None:
    from quant_trading.runner import main as runner_main

    runner_main()

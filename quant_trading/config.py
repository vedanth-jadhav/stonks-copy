from __future__ import annotations

import os
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class CLIProxySettings(BaseModel):
    base_url: str = "http://127.0.0.1:8317"
    api_key: str | None = None
    auth_dir: Path = Field(default_factory=lambda: Path("~/.cli-proxy-api").expanduser())
    timeout_seconds: float = 30.0
    model_aliases: dict[str, str] = Field(
        default_factory=lambda: {
            "boss": "gemini-3.1-pro-preview",
            "agents": "gemini-3-flash-preview",
            "reflection": "gemini-3-flash-preview",
        }
    )


class ExaSettings(BaseModel):
    api_keys: list[str] = Field(default_factory=list)
    base_url: str = "https://api.exa.ai"
    timeout_seconds: float = 20.0
    daily_budget_per_agent: int = 20


class ScreenerSettings(BaseModel):
    binary_path: str = str((Path(__file__).resolve().parents[1] / ".." / "screener" / "screener").resolve())
    timeout_seconds: int = 30
    retries: int = 2


class DatabaseSettings(BaseModel):
    url: str = "sqlite:///data/quant_trading.db"


class MarketSettings(BaseModel):
    timezone: str = "Asia/Kolkata"
    initial_capital: float = 1_000_000.0
    benchmark: str = "^NSEI"
    entry_window_open: str = "09:30"
    entry_window_close: str = "15:00"
    exit_window_close: str = "15:25"
    max_single_position_pct: float = 0.15
    max_sector_exposure_pct: float = 0.30
    min_cash_pct: float = 0.35
    conviction_threshold: float = 0.6
    min_positive_signal_agents: int = 6


class NewsSettings(BaseModel):
    rss_feeds: list[str] = Field(
        default_factory=lambda: [
            "https://www.moneycontrol.com/rss/business.xml",
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        ]
    )


class WebSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8800
    log_level: str = "warning"
    password: str = "quant"
    session_secret: str = "quant-trading-dev-session-secret"
    websocket_refresh_seconds: float = 5.0
    frontend_dir: Path = Field(default_factory=lambda: Path("frontend"))
    static_dir: Path = Field(default_factory=lambda: Path("frontend/dist"))


class Settings(BaseModel):
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
    data_dir: Path = Field(default_factory=lambda: Path("data"))
    reports_dir: Path = Field(default_factory=lambda: Path("reports"))
    logs_dir: Path = Field(default_factory=lambda: Path("logs"))
    cliproxy: CLIProxySettings = Field(default_factory=CLIProxySettings)
    exa: ExaSettings = Field(default_factory=ExaSettings)
    screener: ScreenerSettings = Field(default_factory=ScreenerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    market: MarketSettings = Field(default_factory=MarketSettings)
    news: NewsSettings = Field(default_factory=NewsSettings)
    web: WebSettings = Field(default_factory=WebSettings)

    @classmethod
    def from_env(cls) -> "Settings":
        aliases = {
            "boss": os.getenv("GEMINI_BOSS_MODEL", "gemini-3.1-pro-preview"),
            "agents": os.getenv("GEMINI_AGENTS_MODEL", "gemini-3-flash-preview"),
            "reflection": os.getenv("GEMINI_REFLECTION_MODEL", "gemini-3-flash-preview"),
        }
        exa_keys = [key for key in os.getenv("EXA_API_KEYS", "").split(",") if key]
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            reports_dir=Path(os.getenv("REPORTS_DIR", "reports")),
            logs_dir=Path(os.getenv("LOGS_DIR", "logs")),
            cliproxy=CLIProxySettings(
                base_url=os.getenv("CLIPROXY_BASE_URL", "http://127.0.0.1:8317"),
                api_key=os.getenv("CLIPROXY_API_KEY"),
                auth_dir=Path(os.getenv("CLIPROXY_AUTH_DIR", "~/.cli-proxy-api")).expanduser(),
                timeout_seconds=float(os.getenv("CLIPROXY_TIMEOUT_SECONDS", "30")),
                model_aliases=aliases,
            ),
            exa=ExaSettings(
                api_keys=exa_keys,
                timeout_seconds=float(os.getenv("EXA_TIMEOUT_SECONDS", "20")),
                daily_budget_per_agent=int(os.getenv("EXA_DAILY_BUDGET_PER_AGENT", "20")),
            ),
            screener=ScreenerSettings(
                binary_path=os.getenv(
                    "SCREENER_BINARY_PATH",
                    str((Path(__file__).resolve().parents[1] / ".." / "screener" / "screener").resolve()),
                ),
                timeout_seconds=int(os.getenv("SCREENER_TIMEOUT_SECONDS", "30")),
                retries=int(os.getenv("SCREENER_RETRIES", "2")),
            ),
            database=DatabaseSettings(url=os.getenv("DATABASE_URL", "sqlite:///data/quant_trading.db")),
            market=MarketSettings(
                initial_capital=float(os.getenv("INITIAL_CAPITAL", "1000000")),
            ),
            web=WebSettings(
                host=os.getenv("WEB_HOST", "127.0.0.1"),
                port=int(os.getenv("WEB_PORT", "8800")),
                log_level=os.getenv("WEB_LOG_LEVEL", "warning").lower(),
                password=os.getenv("WEB_PASSWORD", "quant"),
                session_secret=os.getenv("WEB_SESSION_SECRET", "quant-trading-dev-session-secret"),
                websocket_refresh_seconds=float(os.getenv("WEB_WEBSOCKET_REFRESH_SECONDS", "5")),
                frontend_dir=Path(os.getenv("WEB_FRONTEND_DIR", "frontend")),
                static_dir=Path(os.getenv("WEB_STATIC_DIR", "frontend/dist")),
            ),
        )

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.reports_dir, self.logs_dir, self.cliproxy.auth_dir):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def holiday_cache_dir(self) -> Path:
        return self.data_dir

    @property
    def validated_pairs_path(self) -> Path:
        return self.data_dir / "validated_pairs.json"

    def weekly_report_path(self, run_date: date) -> Path:
        return self.reports_dir / f"week_{run_date.isoformat()}.md"


def settings_dict(settings: Settings) -> dict[str, Any]:
    return settings.model_dump(mode="json")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_dirs()
    return settings

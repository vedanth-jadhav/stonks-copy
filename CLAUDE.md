# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python)
- **Install Dependencies**: `uv sync --extra runtime` (recommended) or `pip install -e '.[runtime]'`
- **Run Service**: `bash ops/scripts/run-service.sh` (Integrated web + scheduler)
- **Run Single/One-shot**: `bash ops/scripts/run-service.sh once`
- **Run Tests**: `pytest` or `pytest -q`
- **Lint/Check**: `mypy .` or `ruff check .`
- **Preflight Check**: `bash ops/scripts/doctor.sh`

### Frontend (Svelte)
- **Install**: `cd frontend && npm install`
- **Development**: `npm run dev` (from `frontend` directory)
- **Build**: `npm run build`
- **Lint/Check**: `npm run check`

## High-Level Architecture

### Core Pipeline
The system operates as an agentic pipeline orchestrated by the `Orchestrator` class (`quant_trading/orchestrator.py`). It executes a sequence of specialized agents (`quant_trading/agents/core.py`) that culminate in a final decision by the `BOSS` agent.

**Pipeline Sequence**:
`DISCOVERY` -> `UNIVERSE` -> `QUALITY` -> `MACRO` -> `EVENTS` -> `SENTIMENT` -> `SECTOR` -> `OWNERSHIP` -> `RISK` -> `MOMENTUM` -> `REVERSION` -> `PAIRS` -> `LIQUIDITY` -> `BACKTESTER` -> `BOSS`

### Data & Persistence
- **State**: Restart-safe behavior is achieved through `QuantRepository` (`quant_trading/db/repository.py`), which persists every step of the pipeline to a SQLite database (`data/quant_trading.db`).
- **Models**: SQLAlchemy models are defined in `quant_trading/db/models.py`.
- **Market Data**: Handled by wrappers in `quant_trading/tools/` (yfinance, NSE, Exa, Screener).

### Execution & Scheduling
- **Scheduler**: Uses `APScheduler` (`quant_trading/scheduler.py`) to trigger pipeline runs at specific IST times.
- **Jobs**: Job definitions and cron schedules are centralized in `quant_trading/jobs.py`.
- **Time**: Uses `Asia/Kolkata` (IST) for all market-related scheduling via `quant_trading/timeutils.py`.

### Environment & Config
- **Settings**: Pydantic-based settings in `quant_trading/config.py`.
- **Environment**: Managed via `.env` file (loaded by `run-service.sh`). Core variables include `CLIPROXY_API_KEY`, `DATABASE_URL`, and various model aliases (`GEMINI_BOSS_MODEL`, etc.).

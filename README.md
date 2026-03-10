# Quant Trading

Restart-safe paper trading system for Indian equities.

This README covers only the practical ops path: how to run the service locally, how to deploy it on macOS and Linux, and how to operate it on Lightning.ai without changing the application code.

## What Exists

- SQLite-backed orchestrator state and portfolio persistence
- 14-agent registry with deterministic Tier 1 and Tier 2 logic plus neutral-safe Tier 3 fallbacks
- CLIProxyAPI adapter for Gemini CLI OAuth model access
- Screener, Exa, RSS, NSE, and yfinance adapters
- Delivery-fill and defensive intraday-exit pricing logic
- Scheduler, weekly report writer, and embedded memory primitives
- FastAPI + websocket control-room backend
- Desktop Svelte control-room frontend served from the Python runtime
- Tests for scheduler wiring, repository recovery, execution math, market clock, and agent logic

## Runtime Reality

- The app is paper-only. There is no live broker integration.
- The Python app reads environment variables directly. It does not auto-load `.env`.
- `ops/scripts/run-service.sh` handles `.env` loading for local runs and service managers.
- `ops/scripts/doctor.sh` is a non-destructive preflight check for deployment readiness.
- Generated state lives under `data/`, `logs/`, and `reports/`.

## Prerequisites

- Python `3.12+`
- `uv` recommended, but not required
- Local `screener` binary available at `SCREENER_BINARY_PATH`
- A reachable `CLIProxyAPI` instance with a valid API key if Gemini-backed agents are enabled
- Optional runtime packages for full data access: `yfinance`, `feedparser`, `nseindiaapi`

## Local Setup

1. Create the runtime directories:

```bash
mkdir -p data logs reports
```

2. Copy the example environment file and edit it:

```bash
cp .env.example .env
```

3. Install dependencies.

With `uv`:

```bash
uv sync --extra runtime
```

Without `uv`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[runtime]'
```

4. Run the non-destructive preflight:

```bash
bash ops/scripts/doctor.sh
```

5. Run the service.

Integrated web + scheduler service:

```bash
bash ops/scripts/run-service.sh
```

One-shot bootstrap run:

```bash
bash ops/scripts/run-service.sh once
```

Direct web entrypoint:

```bash
quant-trading-web
```

Control room frontend development:

```bash
cd frontend
npm install
npm run dev
```

Production frontend build:

```bash
cd frontend
npm run build
```

6. Run tests before deployment changes:

```bash
pytest -q
```

## Environment Variables

The app currently reads these values from the environment:

- `CLIPROXY_BASE_URL`
- `CLIPROXY_API_KEY`
- `CLIPROXY_TIMEOUT_SECONDS`
- `GEMINI_BOSS_MODEL`
- `GEMINI_AGENTS_MODEL`
- `GEMINI_REFLECTION_MODEL`
- `EXA_API_KEYS`
- `EXA_TIMEOUT_SECONDS`
- `EXA_DAILY_BUDGET_PER_AGENT`
- `SCREENER_BINARY_PATH`
- `SCREENER_TIMEOUT_SECONDS`
- `SCREENER_RETRIES`
- `DATABASE_URL`
- `INITIAL_CAPITAL`
- `WEB_HOST`
- `WEB_PORT`
- `WEB_PASSWORD`
- `WEB_SESSION_SECRET`
- `WEB_WEBSOCKET_REFRESH_SECONDS`
- `WEB_FRONTEND_DIR`
- `WEB_STATIC_DIR`

Important:

- `EXA_API_KEYS` must be a comma-separated list.
- If `EXA_API_KEYS` is empty, Exa-backed agents will degrade to no-data behavior.
- CLIProxy alias validation only runs when `CLIPROXY_API_KEY` is set.

## macOS Deployment

For a persistent local workstation setup, use `launchd`.

1. Confirm the service starts manually:

```bash
bash /Users/vedanthjadhav/code/stonks/ops/scripts/run-service.sh
```

2. Create `~/Library/LaunchAgents/com.stonks.quant-trading.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.stonks.quant-trading</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>/Users/vedanthjadhav/code/stonks/ops/scripts/run-service.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/vedanthjadhav/code/stonks</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/vedanthjadhav/code/stonks/logs/launchd.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/vedanthjadhav/code/stonks/logs/launchd.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>ENV_FILE</key>
      <string>/Users/vedanthjadhav/code/stonks/.env</string>
    </dict>
  </dict>
</plist>
```

3. Load it:

```bash
launchctl unload ~/Library/LaunchAgents/com.stonks.quant-trading.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.stonks.quant-trading.plist
launchctl start com.stonks.quant-trading
```

4. Check status:

```bash
launchctl list | grep quant-trading
tail -f logs/launchd.stdout.log
```

Notes:

- `run-service.sh` sources `.env`, so you do not need to duplicate every env var into the plist.
- If you use a virtualenv instead of `uv`, make sure `python3` on your PATH resolves inside that environment when `launchd` starts the job. A simple fix is to prepend the venv’s `bin/` directory in the script or set PATH in the plist.

## Linux Deployment

For a VM or always-on Linux host, use `systemd`.

1. Create a dedicated service user if you want isolation:

```bash
sudo useradd --system --create-home --shell /bin/bash quantbot
```

2. Put the repo on disk and make sure `data/`, `logs/`, and `reports/` are writable by the service user.

3. Create `/etc/systemd/system/quant-trading.service`:

```ini
[Unit]
Description=Quant Trading Paper Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=quantbot
Group=quantbot
WorkingDirectory=/opt/stonks
Environment=ENV_FILE=/opt/stonks/.env
ExecStart=/bin/bash /opt/stonks/ops/scripts/run-service.sh
Restart=always
RestartSec=10
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

4. Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quant-trading.service
```

5. Inspect logs:

```bash
sudo systemctl status quant-trading.service
journalctl -u quant-trading.service -f
```

## Lightning.ai Deployment

Lightning is not an always-on VM in the usual sense. The important constraint is that the Studio can sleep after inactivity, so deployment must assume cold restarts.

Recommended pattern:

1. Keep the repo and SQLite database on persistent storage.
2. Store `.env` on the persistent volume, not only in the ephemeral workspace.
3. Install dependencies in the image or at startup.
4. Use a Lightning scheduled job to start the service each market day before pre-market work begins.

Suggested startup command:

```bash
cd /teamspace/studios/this_studio/stonks
bash ops/scripts/run-service.sh
```

Suggested preflight command for a second scheduled job or manual checks:

```bash
cd /teamspace/studios/this_studio/stonks
bash ops/scripts/doctor.sh
```

Operational guidance for Lightning:

- Schedule the start job before the first trading-session task, for example `08:10 IST`.
- Keep the database on persistent storage so restart recovery has real state to reconcile.
- Do not rely on `.env` being auto-loaded by notebooks or shell tabs; the launcher script handles that.
- Expect the process to die between sessions. That is acceptable because the application persists state and resumes from checkpoints on the next start.
- If you rebuild the environment often, prefer `uv sync --extra runtime` in the image or startup hook to keep dependency installation deterministic.

## Ops Scripts

`ops/scripts/run-service.sh`

- Loads `.env` from `ENV_FILE` or repo root
- Creates `data/`, `logs/`, and `reports/`
- Starts the long-running scheduler
- Supports `once` mode for a single bootstrap run

`ops/scripts/doctor.sh`

- Verifies Python version
- Checks for `uv` and `python3`
- Confirms required directories exist and are writable
- Verifies the configured Screener binary path exists
- Optionally checks CLIProxyAPI reachability if `curl`, `CLIPROXY_BASE_URL`, and `CLIPROXY_API_KEY` are present
- Warns when optional inputs like `EXA_API_KEYS` are missing

## Recommended Daily Ops Flow

1. `bash ops/scripts/doctor.sh`
2. `pytest -q`
3. `bash ops/scripts/run-service.sh once`
4. If the one-shot run is clean, start the long-running service

## Notes

- The repo ignores generated `data/`, `logs/`, and `reports/` directories by default.
- The launcher and doctor scripts are intentionally non-destructive to the trading state.
- This README documents the current codebase behavior. If future config fields are added in application code, update `.env.example` and this file at the same time.

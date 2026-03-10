#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
MODE="${1:-service}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/logs" "$ROOT_DIR/reports"
cd "$ROOT_DIR"

run_runner() {
  if command -v uv >/dev/null 2>&1; then
    exec uv run quant-trading-runner
  fi
  exec python3 -m quant_trading.runner
}

run_web() {
  if command -v uv >/dev/null 2>&1; then
    exec uv run quant-trading-web
  fi
  exec python3 -m quant_trading.web.app
}

if [[ "$MODE" == "once" ]]; then
  if command -v uv >/dev/null 2>&1; then
    exec uv run quant-trading-once
  fi
  exec python3 -c "from quant_trading.main import run_once; run_once()"
fi

if [[ "$MODE" == "runner" ]]; then
  run_runner
fi

if [[ "$MODE" == "web" ]]; then
  run_web
fi

if [[ "$MODE" != "service" ]]; then
  echo "Unknown mode: $MODE" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${RUNNER_PID:-}" ]]; then
    kill "$RUNNER_PID" 2>/dev/null || true
  fi
  if [[ -n "${WEB_PID:-}" ]]; then
    kill "$WEB_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if command -v uv >/dev/null 2>&1; then
  uv run quant-trading-runner &
  RUNNER_PID=$!
  uv run quant-trading-web &
  WEB_PID=$!
else
  python3 -m quant_trading.runner &
  RUNNER_PID=$!
  python3 -m quant_trading.web.app &
  WEB_PID=$!
fi

while kill -0 "$RUNNER_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
  sleep 2
done

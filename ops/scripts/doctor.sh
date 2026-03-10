#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
STATUS=0

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "WARN  .env not found at $ENV_FILE"
fi

pass() {
  printf 'PASS  %s\n' "$1"
}

warn() {
  printf 'WARN  %s\n' "$1"
}

fail() {
  printf 'FAIL  %s\n' "$1"
  STATUS=1
}

check_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    pass "command available: $name"
  else
    fail "missing command: $name"
  fi
}

check_dir() {
  local path="$1"
  if [[ -d "$path" && -w "$path" ]]; then
    pass "writable directory: $path"
  elif [[ -d "$path" ]]; then
    fail "directory not writable: $path"
  else
    fail "directory missing: $path"
  fi
}

echo "Repo: $ROOT_DIR"
echo "Env:  $ENV_FILE"

check_cmd python3

if command -v uv >/dev/null 2>&1; then
  pass "uv detected"
else
  warn "uv not detected; falling back to python3 -m quant_trading.main"
fi

python3 - <<'PY' || STATUS=1
import sys
if sys.version_info < (3, 12):
    raise SystemExit("FAIL  python3 must be >= 3.12")
print(f"PASS  python version: {sys.version.split()[0]}")
PY

check_dir "$ROOT_DIR/data"
check_dir "$ROOT_DIR/logs"
check_dir "$ROOT_DIR/reports"

if [[ -n "${SCREENER_BINARY_PATH:-}" ]]; then
  if [[ -x "$SCREENER_BINARY_PATH" || -f "$SCREENER_BINARY_PATH" ]]; then
    pass "screener binary path exists: $SCREENER_BINARY_PATH"
  else
    fail "screener binary path missing: $SCREENER_BINARY_PATH"
  fi
else
  fail "SCREENER_BINARY_PATH is not set"
fi

if [[ -n "${CLIPROXY_BASE_URL:-}" && -n "${CLIPROXY_API_KEY:-}" ]]; then
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS \
      -H "Authorization: Bearer $CLIPROXY_API_KEY" \
      "$CLIPROXY_BASE_URL/v1/models" >/dev/null; then
      pass "CLIProxyAPI reachable: $CLIPROXY_BASE_URL"
    else
      fail "CLIProxyAPI unreachable or unauthorized: $CLIPROXY_BASE_URL"
    fi
  else
    warn "curl not installed; skipping CLIProxyAPI connectivity check"
  fi
else
  warn "CLIPROXY_BASE_URL or CLIPROXY_API_KEY not set; skipping CLIProxyAPI connectivity check"
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  pass "DATABASE_URL configured: $DATABASE_URL"
else
  warn "DATABASE_URL not set; app will fall back to sqlite:///data/quant_trading.db"
fi

if [[ -n "${EXA_API_KEYS:-}" ]]; then
  pass "EXA_API_KEYS configured"
else
  warn "EXA_API_KEYS empty; Exa-backed agents will operate in no-data mode"
fi

exit "$STATUS"

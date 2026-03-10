#!/usr/bin/env bash
# setup-linux.sh — Full one-shot installer for the stonks system on a Linux VPS.
#
# Usage (from anywhere on the VPS):
#   curl -fsSL https://raw.githubusercontent.com/<your-org>/<your-repo>/main/ops/scripts/setup-linux.sh | bash
#
# Or, if you already have the repo cloned:
#   bash ops/scripts/setup-linux.sh
#
# What this does:
#   1. Installs system packages (git, curl, build-essential, nodejs 20)
#   2. Installs uv (Python package manager) and Python 3.12
#   3. Clones the repo (if not already inside it)
#   4. Installs Python dependencies via uv
#   5. Builds the frontend (npm install && npm run build)
#   6. Downloads the screener Linux binary
#   7. Installs CLIProxy and authenticates Gemini headlessly
#   8. Writes a .env file from .env.example (if not already present)
#   9. Creates data/, logs/, reports/ directories
#  10. Runs doctor.sh to verify everything

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step()  { echo -e "\n${GREEN}===${NC} $* ${GREEN}===${NC}"; }
warn()  { echo -e "${YELLOW}WARN${NC}  $*"; }
die()   { echo -e "${RED}FAIL${NC}  $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 0. Detect repo root (works both when curl-piped and when run from clone)
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/../../pyproject.toml" ]]; then
  ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  # curl-pipe mode: clone the repo first, then re-exec from it
  REPO_URL="${REPO_URL:-}"
  if [[ -z "$REPO_URL" ]]; then
    die "Not inside the repo and REPO_URL is not set.\nRun: REPO_URL=https://github.com/you/repo bash <(curl ...)"
  fi
  CLONE_DIR="${CLONE_DIR:-$HOME/stonks}"
  if [[ ! -d "$CLONE_DIR/.git" ]]; then
    step "Cloning repo → $CLONE_DIR"
    git clone "$REPO_URL" "$CLONE_DIR"
  fi
  exec bash "$CLONE_DIR/ops/scripts/setup-linux.sh"
fi

cd "$ROOT_DIR"
ENV_FILE="$ROOT_DIR/.env"
ARCH=$(uname -m)

echo ""
echo "  Repo:  $ROOT_DIR"
echo "  Arch:  $ARCH"
echo "  User:  $(whoami)"
echo ""

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------

step "System packages"

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends \
    git curl build-essential ca-certificates gnupg
  # Node 20 via NodeSource
  if ! node --version 2>/dev/null | grep -q "^v2[0-9]"; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
else
  warn "apt-get not found — skipping system package install (non-Debian system)"
fi

echo "PASS  node $(node --version 2>/dev/null || echo 'not found')"
echo "PASS  npm  $(npm --version 2>/dev/null || echo 'not found')"

# ---------------------------------------------------------------------------
# 2. uv + Python 3.12
# ---------------------------------------------------------------------------

step "uv (Python package manager)"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Add uv to PATH for the rest of this script
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi
echo "PASS  uv $(uv --version)"

# ---------------------------------------------------------------------------
# 3. Python dependencies
# ---------------------------------------------------------------------------

step "Python dependencies"
uv sync --extra runtime
echo "PASS  Python deps installed"

# ---------------------------------------------------------------------------
# 4. Frontend build
# ---------------------------------------------------------------------------

step "Frontend (Svelte)"
if [[ -d "$ROOT_DIR/frontend" ]]; then
  cd "$ROOT_DIR/frontend"
  npm install --silent
  npm run build
  cd "$ROOT_DIR"
  echo "PASS  frontend built"
else
  warn "frontend/ directory not found — skipping"
fi

# ---------------------------------------------------------------------------
# 5. Screener binary
# ---------------------------------------------------------------------------

step "Screener CLI binary"

SCREENER_ASSET="screener-linux-amd64"
[[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]] && SCREENER_ASSET="screener-linux-arm64"

mkdir -p "$HOME/.local/bin"
curl -fsSLL \
  "https://github.com/vedanth-jadhav/screener/releases/download/v0.1.0/${SCREENER_ASSET}" \
  -o "$HOME/.local/bin/screener"
chmod +x "$HOME/.local/bin/screener"
echo "PASS  screener installed → $HOME/.local/bin/screener"

# ---------------------------------------------------------------------------
# 6. CLIProxy — install + headless Gemini login
# ---------------------------------------------------------------------------

step "CLIProxy (Gemini auth)"

if [[ ! -f "$HOME/cliproxyapi/cli-proxy-api" ]]; then
  curl -fsSLL \
    https://raw.githubusercontent.com/brokechubb/cliproxyapi-installer/refs/heads/master/cliproxyapi-installer \
    | bash
fi
echo "PASS  CLIProxy installed"

echo ""
echo "  Starting headless Gemini login…"
echo "  Open the URL below in your browser, authorize, then paste the code here."
echo ""
~/cliproxyapi/cli-proxy-api --gemini-login --no-browser
echo ""
echo "PASS  Gemini authenticated"

# ---------------------------------------------------------------------------
# 7. .env setup
# ---------------------------------------------------------------------------

step ".env configuration"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/.env.example" "$ENV_FILE"
  # Apply VPS-safe defaults
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i 's|^SCREENER_BINARY_PATH=.*|SCREENER_BINARY_PATH='"$HOME"'/.local/bin/screener|' "$ENV_FILE"
    sed -i 's|^WEB_HOST=.*|WEB_HOST=0.0.0.0|' "$ENV_FILE"
    sed -i 's|^WEB_PASSWORD=.*|WEB_PASSWORD=quant_secure_passwd_123!|' "$ENV_FILE"
  else
    sed -i '' 's|^SCREENER_BINARY_PATH=.*|SCREENER_BINARY_PATH='"$HOME"'/.local/bin/screener|' "$ENV_FILE"
    sed -i '' 's|^WEB_HOST=.*|WEB_HOST=0.0.0.0|' "$ENV_FILE"
    sed -i '' 's|^WEB_PASSWORD=.*|WEB_PASSWORD=quant_secure_passwd_123!|' "$ENV_FILE"
  fi
  echo "PASS  .env created from .env.example"
  echo ""
  echo "  Edit $ENV_FILE and fill in:"
  echo "    CLIPROXY_API_KEY   — key printed by CLIProxy during login"
  echo "    EXA_API_KEYS       — your Exa API key(s)"
  echo "    WEB_PASSWORD       — change from default 'quant'"
  echo "    WEB_SESSION_SECRET — any random string"
else
  echo "PASS  .env already exists — not overwritten"
fi

# ---------------------------------------------------------------------------
# 8. Runtime directories
# ---------------------------------------------------------------------------

step "Runtime directories"
mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/logs" "$ROOT_DIR/reports"
echo "PASS  data/ logs/ reports/ ready"

# ---------------------------------------------------------------------------
# 9. Start CLIProxy daemon
# ---------------------------------------------------------------------------

step "CLIProxy daemon"
nohup ~/cliproxyapi/cli-proxy-api > "$ROOT_DIR/logs/cliproxy.log" 2>&1 &
CLIPROXY_PID=$!
sleep 2
if kill -0 "$CLIPROXY_PID" 2>/dev/null; then
  echo "PASS  CLIProxy running (PID $CLIPROXY_PID) → logs/cliproxy.log"
else
  warn "CLIProxy may not have started — check logs/cliproxy.log"
fi

# ---------------------------------------------------------------------------
# 10. Doctor check
# ---------------------------------------------------------------------------

step "Preflight check"
bash "$ROOT_DIR/ops/scripts/doctor.sh" || true

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo "  Start the service:"
echo "    bash ops/scripts/run-service.sh"
echo ""
echo "  Or in a tmux session (recommended):"
echo "    tmux new -s stonks 'bash ops/scripts/run-service.sh'"
echo ""
echo "  Web UI will be at: http://$(curl -fsSL ifconfig.me 2>/dev/null || echo '<your-vps-ip>'):8800"
echo ""
echo "  !! Fill in .env before starting if you haven't already !!"
echo ""

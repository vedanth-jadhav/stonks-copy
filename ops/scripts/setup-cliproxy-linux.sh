#!/usr/bin/env bash
# setup-cliproxy-linux.sh — Install CLIProxy and authenticate Gemini headlessly on a VPS.
#
# This is a one-time setup step. Run once before starting the app.
#
# Usage:
#   bash ops/scripts/setup-cliproxy-linux.sh
#
# After running, credentials are saved to ~/cliproxyapi/ and CLIProxy runs as a daemon.
# The app connects to it at http://127.0.0.1:8317 (set CLIPROXY_BASE_URL in .env).

set -euo pipefail

echo "=== Installing CLIProxy (community installer) ==="
curl -fsSL https://raw.githubusercontent.com/brokechubb/cliproxyapi-installer/refs/heads/master/cliproxyapi-installer | bash

echo ""
echo "=== Authenticating Gemini (headless) ==="
echo "Follow the URL printed below and paste the auth code back."
~/cliproxyapi/cli-proxy-api --gemini-login --no-browser

echo ""
echo "=== CLIProxy is authenticated. ==="
echo "Start it as a background daemon before running the app:"
echo "  nohup ~/cliproxyapi/cli-proxy-api &"
echo ""
echo "Add to your .env:"
echo "  CLIPROXY_BASE_URL=http://127.0.0.1:8317"
echo "  CLIPROXY_API_KEY=<key shown during login>"

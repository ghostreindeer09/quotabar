#!/usr/bin/env bash
# QuotaBar launcher script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting QuotaBar..."
echo "   Config will be saved to: ~/.quotabar/config.json"
echo "   Press Ctrl+C to stop"
echo ""

cd "$SCRIPT_DIR"
python3 app.py

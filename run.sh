#!/usr/bin/env bash
# QuotaBar launcher script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "🚀 Starting QuotaBar..."
echo "   Config will be saved to: ~/.quotabar/config.json"
echo "   Press Ctrl+C to stop"
echo ""

python3 app.py

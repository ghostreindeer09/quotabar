#!/usr/bin/env bash
# QuotaBar 1-Click Installer
# Just double-click this file from your Finder window to install and run!

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "⚡ Starting QuotaBar Installation ⚡"
echo "======================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 could not be found."
    echo "Please download and install Python from https://www.python.org/downloads/mac-osx/"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

echo "✅ Python 3 found!"

# Check if a virtual environment exists. If not, create it.
if [ ! -d "venv" ]; then
    echo "📦 Creating an isolated Python environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install the required packages quietly
echo "⬇️  Installing required packages (this may take a moment)..."
pip install -r requirements.txt --quiet --disable-pip-version-check

echo ""
echo "🎉 Installation Complete!"
echo "✨ Launching QuotaBar..."
echo "======================================"
echo ""

# Launch the app directly using the venv python
python3 app.py

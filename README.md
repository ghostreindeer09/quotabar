# QuotaBar ⚡

> A sleek macOS menu bar app that tracks your AI API usage quotas in real time.

![QuotaBar menubar preview](https://img.shields.io/badge/macOS-menu%20bar%20app-blue?style=flat-square) 
![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen?style=flat-square)

---

## Features

- **🔴🟡🟢 Visual usage bars** directly in your macOS menu bar
- **Multi-provider support**: OpenAI, Anthropic (Claude), Google Gemini, Groq, Cohere, Mistral AI
- **Per-provider submenus** showing:
  - Cost used vs monthly limit (with progress bar)
  - Token breakdown (input / output)
  - Request counts
- **Toggle providers on/off** without leaving the menu
- **Auto-refresh** every N seconds (configurable)
- **Threshold alerts** — macOS notifications when approaching your spending limit
- **Native Settings window** with dark theme (no HTML needed)

---

## Supported Providers & Usage Data

| Provider | Cost tracking | Token tracking | Notes |
|---|---|---|---|
| **OpenAI** | ✅ (Admin costs API or estimated) | ✅ | Needs Admin or standard API key |
| **Anthropic** | ✅ (estimated from tokens) | ✅ | Needs Admin API key for usage data |
| **Google Gemini** | ❌ (no public API) | ❌ | Key validation only |
| **Groq** | ❌ (no public API) | ❌ | Key validation only |
| **Cohere** | ❌ | ❌ | Key validation only |
| **Mistral AI** | ❌ | ❌ | Key validation only |

---

## Installation

### Method 1: Quick Setup (For Everyone) ✨

1. **Download the App:** Click the green **"Code"** button at the top of this page and select **"Download ZIP"**.
2. **Extract:** Find the downloaded ZIP file in your Downloads folder and double-click it to extract the folder.
3. **Install:** Open the extracted `quotabar-main` folder and simply **double-click** the `install.command` file.
   - *Note: If your Mac says it cannot be opened because it is from an unidentified developer, right-click the file and select "Open".*
4. **Done:** The script will handle everything automatically and launch QuotaBar!

### Method 2: Developer Setup (Advanced)

If you prefer using the terminal and managing your own virtual environment:

```bash
git clone https://github.com/yourname/quotabar.git
cd quotabar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run.sh
```

> **Note:** Requires Python 3.11+ and macOS 12+.

---

## Configuration

Configuration is stored at `~/.quotabar/config.json` and is auto-created on first run.

You can edit it via:
- **In-app Settings** — click the menu bar icon → ⚙️ Settings…
- **Directly** — `open ~/.quotabar/config.json`

### Config structure

```json
{
  "refresh_interval": 300,
  "alert_threshold": 80,
  "providers": {
    "openai": {
      "enabled": true,
      "api_key": "sk-...",
      "monthly_limit_usd": 100.0
    },
    "anthropic": {
      "enabled": true,
      "api_key": "sk-ant-...",
      "admin_api_key": "sk-ant-admin-...",
      "monthly_limit_usd": 100.0
    },
    "gemini": {
      "enabled": true,
      "api_key": "AIza...",
      "monthly_limit_usd": 50.0
    }
  }
}
```

### Getting API Keys

| Provider | Key type | Where to get |
|---|---|---|
| OpenAI | Standard or Admin | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic | Standard + Admin | [console.anthropic.com/settings/admin-keys](https://console.anthropic.com/settings/admin-keys) |
| Gemini | API key | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Groq | API key | [console.groq.com/keys](https://console.groq.com/keys) |
| Cohere | API key | [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys) |
| Mistral | API key | [console.mistral.ai/api-keys/](https://console.mistral.ai/api-keys/) |

---

## How the Menu Bar Works

The menu bar title shows:
```
🟢 ████████░░ 80%
```

- **Circle emoji**: 🟢 < 70% | 🟡 70-90% | 🔴 ≥ 90%
- **Progress bar**: weighted average across all enabled providers with limits set
- **Percentage**: of your total monthly budget used

---

## Auto-start on Login (optional)

To make QuotaBar start automatically:

1. Open **System Settings** → **General** → **Login Items**
2. Click **+** and add `/path/to/quotabar/run.sh`

Or create a Launch Agent:

```bash
cat > ~/Library/LaunchAgents/com.quotabar.app.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quotabar.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/YOUR_USERNAME/quotabar/app.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/com.quotabar.app.plist
```

---

## Project Structure

```
quotabar/
├── app.py               # Main rumps menu bar application
├── config.py            # Config loading/saving (~/.quotabar/config.json)
├── fetcher.py           # Concurrent provider data fetcher
├── settings_window.py   # Native macOS settings UI (PyObjC/AppKit)
├── requirements.txt
├── run.sh
└── providers/
    ├── __init__.py
    ├── base.py          # BaseProvider + UsageData dataclass
    ├── openai_provider.py
    ├── anthropic_provider.py
    ├── gemini_provider.py
    ├── groq_provider.py
    ├── cohere_provider.py
    └── mistral_provider.py
```

---

## Adding a New Provider

1. Create `providers/your_provider.py` extending `BaseProvider`
2. Implement `fetch_usage() -> UsageData`
3. Add it to `PROVIDER_MAP` in `fetcher.py`
4. Add default config in `config.py`'s `DEFAULT_CONFIG`
5. Add to `providers/__init__.py`

---

## License

MIT

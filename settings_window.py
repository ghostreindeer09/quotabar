"""
settings_window.py
Opens ~/.quotabar/config.json in the user's preferred editor.
Called as a subprocess by app.py when user clicks Settings.
"""

import subprocess
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CONFIG_FILE, load_config, save_config, DEFAULT_CONFIG


def open_config_in_editor():
    """Ensure the config file exists and open it in the best available editor."""
    # Make sure a well-commented config exists
    if not CONFIG_FILE.exists():
        save_config(load_config())  # write defaults

    # Annotate the file with key hints if it's never been edited
    _maybe_add_comments()

    # Try editors in order of developer-friendliness
    editors = [
        ["code",    str(CONFIG_FILE)],   # VS Code
        ["cursor",  str(CONFIG_FILE)],   # Cursor
        ["zed",     str(CONFIG_FILE)],   # Zed
        ["open", "-a", "TextEdit", str(CONFIG_FILE)],
        ["open",    str(CONFIG_FILE)],   # macOS default app for .json
    ]

    for cmd in editors:
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                return
        except FileNotFoundError:
            continue

    # Absolute last resort: print the path so the user can find it
    print(f"[QuotaBar] Please open this file manually: {CONFIG_FILE}", file=sys.stderr)


def _maybe_add_comments():
    """Write a clean, hint-annotated version of the config if keys look empty."""
    try:
        with open(CONFIG_FILE) as f:
            raw = f.read()
        data = json.loads(raw)
    except Exception:
        return

    providers = data.get("providers", {})
    all_empty = all(
        not p.get("api_key", "")
        for p in providers.values()
    )
    if not all_empty:
        return  # already has keys — don't touch it

    # Write a version with inline hints
    hint = {
        "refresh_interval": data.get("refresh_interval", 300),
        "alert_threshold":  data.get("alert_threshold", 80),
        "_hint": "Edit api_key values below, then save. The menu bar will refresh automatically.",
        "providers": {}
    }

    key_hints = {
        "openai":    "sk-proj-...  →  platform.openai.com/api-keys",
        "anthropic": "sk-ant-api03-...  →  console.anthropic.com/settings/api-keys",
        "gemini":    "AIzaSy...  →  aistudio.google.com/apikey",
        "groq":      "gsk_...  →  console.groq.com/keys",
        "cohere":    "...  →  dashboard.cohere.com/api-keys",
        "mistral":   "...  →  console.mistral.ai/api-keys",
    }
    admin_hints = {
        "anthropic": "sk-ant-admin-...  →  console.anthropic.com/settings/admin-keys  (optional, for usage data)",
    }

    for pid, pcfg in providers.items():
        entry = dict(pcfg)
        if not entry.get("api_key"):
            entry["_api_key_hint"] = key_hints.get(pid, "Paste your API key here")
        if pid == "anthropic" and not entry.get("admin_api_key"):
            entry["_admin_key_hint"] = admin_hints["anthropic"]
        hint["providers"][pid] = entry

    with open(CONFIG_FILE, "w") as f:
        json.dump(hint, f, indent=2)


if __name__ == "__main__":
    open_config_in_editor()

"""
QuotaBar Configuration Manager
Handles loading/saving of API keys, provider settings, and usage limits.
Config is stored at ~/.quotabar/config.json
"""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".quotabar"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "providers": {
        "openai": {
            "enabled": True,
            "api_key": "",
            "monthly_limit_usd": 100.0,
            "display_name": "OpenAI",
            "color": "#10a37f",
        },
        "anthropic": {
            "enabled": True,
            "api_key": "",
            "admin_api_key": "",
            "monthly_limit_usd": 100.0,
            "display_name": "Anthropic (Claude)",
            "color": "#d4722b",
        },
        "gemini": {
            "enabled": True,
            "api_key": "",
            "monthly_limit_usd": 50.0,
            "display_name": "Google Gemini",
            "color": "#4285F4",
        },
        "groq": {
            "enabled": False,
            "api_key": "",
            "monthly_limit_usd": 50.0,
            "display_name": "Groq",
            "color": "#f55036",
        },
        "cohere": {
            "enabled": False,
            "api_key": "",
            "monthly_limit_usd": 50.0,
            "display_name": "Cohere",
            "color": "#39594d",
        },
        "mistral": {
            "enabled": False,
            "api_key": "",
            "monthly_limit_usd": 50.0,
            "display_name": "Mistral AI",
            "color": "#ff7000",
        },
    },
    "refresh_interval": 300,  # seconds (5 minutes)
    "alert_threshold": 80,    # percent before warning notification
    "show_cost": True,
    "compact_menu": False,
}


def ensure_config_dir():
    """Create the config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load config from disk, merging with defaults for any missing keys."""
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        # Deep merge with defaults so new keys are always present
        merged = _deep_merge(DEFAULT_CONFIG, data)
        return merged
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Persist config to disk."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, preferring override values."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_provider_config(config: dict, provider_id: str) -> dict:
    """Get config for a specific provider."""
    return config["providers"].get(provider_id, {})


def update_provider(config: dict, provider_id: str, updates: dict) -> dict:
    """Update a provider's config and return the updated full config."""
    if provider_id not in config["providers"]:
        config["providers"][provider_id] = {}
    config["providers"][provider_id].update(updates)
    return config

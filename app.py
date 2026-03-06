"""
QuotaBar — macOS menu bar app for tracking AI API usage quotas.
Entry point: python app.py
"""

import os
import sys
import queue
import threading
from datetime import datetime
from typing import Dict, Optional

import AppKit
import rumps

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from config import load_config, save_config
from fetcher import build_providers, fetch_all_usage
from providers.base import UsageData

# Thread-safe queue: background threads post results here;
# a lightweight rumps.Timer drains it on the main thread.
_UI_QUEUE: queue.Queue = queue.Queue()

# Usage dashboard URLs — opened in browser when user clicks "View Dashboard →"
_DASHBOARD_URLS = {
    "openai":    "https://platform.openai.com/usage",
    "anthropic": "https://console.anthropic.com/settings/usage",
    "gemini":    "https://aistudio.google.com/",
    "groq":      "https://console.groq.com/",
    "cohere":    "https://dashboard.cohere.com/",
    "mistral":   "https://console.mistral.ai/",
}


def _open_url(url: str):
    """Open a URL in the default browser."""
    import subprocess
    subprocess.run(["open", url], check=False)

# Pre-load provider icons (32x32 → scaled to 16x16 in menu)
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_ICON_CACHE: Dict[str, object] = {}

def _load_icon(provider_id: str) -> Optional[object]:
    """Load and cache a 16x16 NSImage for the given provider, or None."""
    if provider_id in _ICON_CACHE:
        return _ICON_CACHE[provider_id]
    path = os.path.join(_ASSETS_DIR, f"{provider_id}.png")
    if not os.path.exists(path):
        _ICON_CACHE[provider_id] = None
        return None
    img = AppKit.NSImage.alloc().initWithContentsOfFile_(path)
    if img:
        img.setSize_(AppKit.NSMakeSize(16, 16))
    _ICON_CACHE[provider_id] = img
    return img


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _bar(fraction: float, width: int = 10) -> str:
    """Render a Unicode progress bar like ██████░░░░."""
    filled = int(round(fraction * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def _color_indicator(fraction: float) -> str:
    """Return a colored circle based on usage level."""
    if fraction >= 0.9:
        return "🔴"
    elif fraction >= 0.7:
        return "🟡"
    return "🟢"


def _format_cost(cost: float) -> str:
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def _compute_overall_fraction(usages: Dict[str, UsageData]) -> float:
    """Weighted average fraction across all providers that have a limit set."""
    total_limit = 0.0
    total_cost = 0.0
    for u in usages.values():
        if u.enabled and u.monthly_limit_usd > 0 and not u.error:
            total_limit += u.monthly_limit_usd
            total_cost += u.cost_usd
    if total_limit <= 0:
        return 0.0
    return min(total_cost / total_limit, 1.0)


def _menubar_title(overall: float, usages: Dict[str, UsageData]) -> str:
    """
    Build the compact menu bar title.
    Shows: ██░░░░░░░░ 12%  (or just the bar for very small screens)
    """
    bar = _bar(overall, width=8)
    pct = int(overall * 100)
    indicator = _color_indicator(overall)
    return f"{indicator} {bar} {pct}%"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main App
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class QuotaBarApp(rumps.App):

    def __init__(self):
        # Load config FIRST so we know the refresh interval
        self._config = load_config()
        self._usages: Dict[str, UsageData] = {}
        self._providers = build_providers(self._config)
        self._fetching = False
        self._settings_controller = None

        # Build the initial menu skeleton
        super().__init__(
            name="QuotaBar",
            title="⚡ Loading…",
            quit_button=None,
        )
        self._build_menu()
        self._start_refresh_timer()
        # Kick off an immediate fetch in the background
        self._trigger_fetch()

    # ─── Menu Construction ──────────────────────────────────

    def _build_menu(self):
        """Rebuild the full menu from scratch."""
        self.menu.clear()

        # ── Header ──────────────────────────────────────────
        header = rumps.MenuItem("QuotaBar  —  AI Usage Monitor")
        header.set_callback(None)
        self.menu.add(header)
        self.menu.add(rumps.separator)

        # ── Provider items ──────────────────────────────────
        config = self._config
        provider_order = [
            p for p in ["openai", "anthropic", "gemini", "groq", "cohere", "mistral"]
            if p in config.get("providers", {})
        ]

        for pid in provider_order:
            pcfg = config["providers"].get(pid, {})
            name = pcfg.get("display_name", pid)
            enabled = pcfg.get("enabled", False)

            if not enabled:
                off_item = rumps.MenuItem(f"○  {name}  [disabled]")
                off_item.set_callback(None)
                icon = _load_icon(pid)
                if icon:
                    off_item._menuitem.setImage_(icon)
                self.menu.add(off_item)
                continue

            usage = self._usages.get(pid)
            self.menu.add(self._make_provider_item(pid, name, usage, pcfg))

        self.menu.add(rumps.separator)

        # ── Controls ────────────────────────────────────────
        refresh_item = rumps.MenuItem("↻  Refresh Now", callback=self._menu_refresh)
        self.menu.add(refresh_item)

        settings_item = rumps.MenuItem("⚙️  Settings (opens config file)…", callback=self._open_settings)
        self.menu.add(settings_item)

        self.menu.add(rumps.separator)

        # ── Status line ──────────────────────────────────────
        if self._usages:
            ts = max(
                (u.last_updated for u in self._usages.values() if u.last_updated),
                default=None,
            )
            ts_str = ts.strftime("Updated %H:%M:%S") if ts else "Never updated"
        else:
            ts_str = "Not yet fetched"
        self.menu.add(rumps.MenuItem(ts_str))

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit QuotaBar", callback=self._quit))

    def _make_provider_item(
        self, pid: str, name: str, usage: Optional[UsageData], pcfg: dict
    ) -> rumps.MenuItem:
        """Create a rich menu item for one provider, with a submenu."""
        if usage is None:
            # Not yet fetched
            item = rumps.MenuItem(f"◌  {name}  —  fetching…")
            item.set_callback(None)
            icon = _load_icon(pid)
            if icon:
                item._menuitem.setImage_(icon)
            return item

        fraction = usage.usage_fraction
        indicator = _color_indicator(fraction)
        bar = _bar(fraction, width=12)
        pct = f"{usage.usage_percent:.0f}%"
        cost_str = _format_cost(usage.cost_usd)
        limit_str = _format_cost(usage.monthly_limit_usd)

        if usage.error and usage.cost_usd == 0:
            # Show a warning indicator but still let people toggle
            title = f"⚠️  {name}  —  no data"
        else:
            title = f"{indicator}  {name}  {bar}  {pct}"

        parent = rumps.MenuItem(title)

        # ── Submenu ────────────────────────────────────────
        cost_line = rumps.MenuItem(f"    💰 Used: {cost_str} / {limit_str} this month")
        cost_line.set_callback(None)
        parent.add(cost_line)

        if usage.total_tokens > 0:
            tok_line = rumps.MenuItem(
                f"    🔢 Tokens: {_format_tokens(usage.total_tokens)}"
                f"  (↑{_format_tokens(usage.prompt_tokens)} / ↓{_format_tokens(usage.completion_tokens)})"
            )
            tok_line.set_callback(None)
            parent.add(tok_line)

        if usage.request_count > 0:
            req_line = rumps.MenuItem(f"    📬 Requests: {usage.request_count:,}")
            req_line.set_callback(None)
            parent.add(req_line)

        if usage.error:
            err_line = rumps.MenuItem(f"    ℹ️  {usage.error}")
            err_line.set_callback(None)
            parent.add(err_line)

        parent.add(rumps.separator)

        # "View Dashboard" link — opens in browser
        dash_url = _DASHBOARD_URLS.get(pid)
        if dash_url:
            dash_item = rumps.MenuItem(
                f"    🌐 View {name} Dashboard →",
                callback=lambda _, url=dash_url: _open_url(url),
            )
            parent.add(dash_item)

        # Toggle enable/disable
        toggle_label = "✓ Enabled (click to disable)" if pcfg.get("enabled") else "✗ Disabled (click to enable)"
        toggle = rumps.MenuItem(toggle_label, callback=lambda _: self._toggle_provider(pid))
        parent.add(toggle)


        # Attach provider favicon to the NSMenuItem
        icon = _load_icon(pid)
        if icon:
            parent._menuitem.setImage_(icon)

        return parent

    # ─── Menu Bar Title Update ──────────────────────────────

    def _update_title(self):
        """Recompute and set the menu bar title string."""
        if not self._usages:
            self.title = "⚡ QuotaBar"
            return
        enabled = {pid: u for pid, u in self._usages.items() if u.enabled}
        overall = _compute_overall_fraction(enabled)
        self.title = _menubar_title(overall, enabled)

    # ─── Timers ─────────────────────────────────────────────

    def _start_refresh_timer(self):
        interval = self._config.get("refresh_interval", 300)
        self._timer = rumps.Timer(self._on_timer, interval)
        self._timer.start()
        # Poll the UI queue every 0.5 s — runs on the main thread via NSTimer
        self._poll_timer = rumps.Timer(self._poll_ui_queue, 0.5)
        self._poll_timer.start()

    def _on_timer(self, sender):
        self._trigger_fetch()

    def _poll_ui_queue(self, sender):
        """Drain the UI queue on the main thread (called by NSTimer)."""
        try:
            while True:
                fn = _UI_QUEUE.get_nowait()
                fn()
        except queue.Empty:
            pass

    def _trigger_fetch(self):
        """Kick off a background fetch, non-blocking."""
        if self._fetching:
            return
        self._fetching = True
        t = threading.Thread(target=self._fetch_worker, daemon=True)
        t.start()

    def _fetch_worker(self):
        """Background thread: fetch usage, then post UI update to main thread via queue."""
        try:
            providers = build_providers(self._config)
            usages = fetch_all_usage(providers)
            self._usages = usages
            self._check_alerts(usages)
            # Post UI refresh to the queue — drained by _poll_ui_queue on main thread
            _UI_QUEUE.put(self._refresh_ui)
        except Exception as e:
            print(f"[QuotaBar] fetch error: {e}", file=sys.stderr)
        finally:
            self._fetching = False

    # ─── UI Refresh (main thread) ────────────────────────────

    def _refresh_ui(self):
        """Rebuild menu and update title — must run on main thread."""
        self._build_menu()
        self._update_title()

    # ─── Alerts ─────────────────────────────────────────────

    def _check_alerts(self, usages: Dict[str, UsageData]):
        threshold = self._config.get("alert_threshold", 80) / 100.0
        for pid, usage in usages.items():
            if usage.enabled and usage.usage_fraction >= threshold and not usage.error:
                rumps.notification(
                    title="QuotaBar Warning",
                    subtitle=f"{usage.display_name}",
                    message=(
                        f"You've used {usage.usage_percent:.0f}% of your monthly "
                        f"${usage.monthly_limit_usd:.0f} budget!"
                    ),
                )

    # ─── Callbacks ──────────────────────────────────────────

    def _menu_refresh(self, _=None):
        self.title = "⏳ Refreshing…"
        # Reload config from disk so manually edited API keys take effect immediately
        self._config = load_config()
        self._providers = build_providers(self._config)
        self._trigger_fetch()

    def _toggle_provider(self, pid: str):
        pcfg = self._config["providers"].get(pid, {})
        pcfg["enabled"] = not pcfg.get("enabled", False)
        self._config["providers"][pid] = pcfg
        save_config(self._config)
        self._providers = build_providers(self._config)
        self._build_menu()
        self._trigger_fetch()

    def _open_settings(self, _=None):
        """Launch settings_window.py as a standalone subprocess.
        
        tkinter requires the main thread, but rumps already owns it.
        Running as a separate process sidesteps that entirely.
        """
        import subprocess
        import threading

        script = os.path.join(os.path.dirname(__file__), "settings_window.py")

        def _watch():
            try:
                subprocess.run([sys.executable, script], check=False)
            except Exception as e:
                print(f"[QuotaBar] settings error: {e}", file=sys.stderr)
                return
            # Settings window closed — reload config and refresh
            new_cfg = load_config()
            self._config = new_cfg
            self._providers = build_providers(new_cfg)
            self._timer.stop()
            self._start_refresh_timer()
            self._trigger_fetch()

        threading.Thread(target=_watch, daemon=True).start()

    def _on_settings_saved(self, new_config: dict):
        """Called when user saves settings."""
        self._config = new_config
        self._providers = build_providers(self._config)
        # Restart timer with new interval
        self._timer.stop()
        self._start_refresh_timer()
        self._trigger_fetch()

    def _quit(self, _=None):
        rumps.quit_application()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    QuotaBarApp().run()

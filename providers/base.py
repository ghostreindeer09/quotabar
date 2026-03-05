"""
Base provider interface for all AI service quota providers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import abc


@dataclass
class UsageData:
    """Standardized usage data returned by all providers."""
    provider_id: str
    display_name: str
    color: str

    # Cost-based tracking
    cost_usd: float = 0.0
    monthly_limit_usd: float = 0.0

    # Token-based tracking
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    # Request count
    request_count: int = 0

    # Period info
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    # Metadata
    last_updated: Optional[datetime] = None
    error: Optional[str] = None
    enabled: bool = True

    @property
    def usage_fraction(self) -> float:
        """0.0 to 1.0 fraction of monthly limit used."""
        if self.monthly_limit_usd <= 0:
            return 0.0
        return min(self.cost_usd / self.monthly_limit_usd, 1.0)

    @property
    def usage_percent(self) -> float:
        """0 to 100 percentage of monthly limit used."""
        return self.usage_fraction * 100.0

    @property
    def is_warning(self) -> bool:
        return 0.7 <= self.usage_fraction < 0.9

    @property
    def is_critical(self) -> bool:
        return self.usage_fraction >= 0.9

    @property
    def status_emoji(self) -> str:
        if self.error:
            return "⚠️"
        if self.is_critical:
            return "🔴"
        elif self.is_warning:
            return "🟡"
        return "🟢"


class BaseProvider(abc.ABC):
    """Abstract base class for all AI provider quota fetchers."""

    def __init__(self, provider_id: str, config: dict):
        self.provider_id = provider_id
        self.config = config
        self._cached_data: Optional[UsageData] = None

    @property
    def display_name(self) -> str:
        return self.config.get("display_name", self.provider_id)

    @property
    def color(self) -> str:
        return self.config.get("color", "#888888")

    @property
    def monthly_limit_usd(self) -> float:
        return float(self.config.get("monthly_limit_usd", 100.0))

    @property
    def is_enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    @property
    def api_key(self) -> str:
        return self.config.get("api_key", "")

    @abc.abstractmethod
    def fetch_usage(self) -> UsageData:
        """Fetch current usage data from the provider API or local storage."""
        ...

    def empty_usage(self, error: Optional[str] = None) -> UsageData:
        """Return an empty UsageData (e.g. when API key is missing)."""
        return UsageData(
            provider_id=self.provider_id,
            display_name=self.display_name,
            color=self.color,
            monthly_limit_usd=self.monthly_limit_usd,
            enabled=self.is_enabled,
            last_updated=datetime.now(),
            error=error,
        )

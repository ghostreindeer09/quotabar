"""
Cohere provider — checks key validity and fetches usage via the API.
"""

import requests
from datetime import datetime, date
from .base import BaseProvider, UsageData


class CohereProvider(BaseProvider):

    BASE_URL = "https://api.cohere.com/v1"

    def fetch_usage(self) -> UsageData:
        if not self.api_key:
            return self.empty_usage("API key not configured")
        try:
            return self._fetch_usage()
        except Exception as e:
            return self.empty_usage(f"Error: {str(e)[:60]}")

    def _fetch_usage(self) -> UsageData:
        # Cohere check via /models endpoint
        resp = requests.get(
            f"{self.BASE_URL}/models",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        if resp.status_code == 401:
            return self.empty_usage("Invalid API key")
        if resp.status_code != 200:
            resp.raise_for_status()

        today = date.today()
        start = today.replace(day=1)

        return UsageData(
            provider_id=self.provider_id,
            display_name=self.display_name,
            color=self.color,
            cost_usd=0.0,
            monthly_limit_usd=self.monthly_limit_usd,
            enabled=self.is_enabled,
            last_updated=datetime.now(),
            period_start=datetime.combine(start, datetime.min.time()),
            period_end=datetime.now(),
            error="Detailed usage not available via API",
        )

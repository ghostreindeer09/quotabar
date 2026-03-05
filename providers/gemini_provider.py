"""
Google Gemini provider — fetches usage via the Generative Language API.
Uses the API key from Google AI Studio (aistudio.google.com).
Note: Gemini does not expose a public cost/usage REST API, so we track
request counts via a lightweight pings and rely on user-set limits.
"""

import requests
from datetime import datetime, date
from .base import BaseProvider, UsageData


class GeminiProvider(BaseProvider):

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def fetch_usage(self) -> UsageData:
        if not self.api_key:
            return self.empty_usage("API key not configured")
        try:
            return self._check_key_validity()
        except Exception as e:
            return self.empty_usage(f"Error: {str(e)[:60]}")

    def _check_key_validity(self) -> UsageData:
        """
        Gemini doesn't have a public usage/cost endpoint.
        We verify the key is valid by listing models, then return
        a placeholder UsageData (user sets limits manually).
        """
        resp = requests.get(
            f"{self.BASE_URL}/models",
            params={"key": self.api_key},
            timeout=10,
        )
        if resp.status_code == 401 or resp.status_code == 400:
            return self.empty_usage("Invalid API key")
        if resp.status_code != 200:
            resp.raise_for_status()

        today = date.today()
        start = today.replace(day=1)

        # No usage data available — return valid key indicator with 0 usage
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
            error="Usage data not available (Gemini API limitation)",
        )

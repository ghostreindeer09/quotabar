"""
Anthropic (Claude) provider — fetches usage via the Anthropic Admin API.
Requires an Admin API key: https://console.anthropic.com/settings/admin-keys
Endpoint: GET /v1/organizations/usage_report/messages
"""

import requests
from datetime import datetime, date, timedelta
from .base import BaseProvider, UsageData


class AnthropicProvider(BaseProvider):

    BASE_URL = "https://api.anthropic.com"

    @property
    def admin_api_key(self) -> str:
        return self.config.get("admin_api_key", "")

    def fetch_usage(self) -> UsageData:
        key = self.admin_api_key or self.api_key
        if not key:
            return self.empty_usage("API key not configured")
        try:
            return self._fetch_usage_report(key)
        except Exception as e:
            return self.empty_usage(f"Error: {str(e)[:60]}")

    def _fetch_usage_report(self, key: str) -> UsageData:
        today = date.today()
        start = today.replace(day=1)

        resp = requests.get(
            f"{self.BASE_URL}/v1/organizations/usage_report/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            params={
                "starting_at": start.isoformat(),
                "limit": 31,
            },
            timeout=10,
        )

        if resp.status_code == 401:
            return self.empty_usage("Invalid API key")
        if resp.status_code == 403:
            return self.empty_usage("Admin key required for usage data")
        if resp.status_code == 422:
            return self._fetch_cost_report(key)
        resp.raise_for_status()

        payload = resp.json()
        total_input = 0
        total_output = 0
        total_requests = 0

        for item in payload.get("data", []):
            total_input += item.get("input_tokens", 0)
            total_output += item.get("output_tokens", 0)
            total_requests += item.get("request_count", 0)

        total_tokens = total_input + total_output
        # Claude pricing varies; use ~$0.000015/token blended estimate
        estimated_cost = total_tokens * 0.000015

        return UsageData(
            provider_id=self.provider_id,
            display_name=self.display_name,
            color=self.color,
            cost_usd=estimated_cost,
            monthly_limit_usd=self.monthly_limit_usd,
            total_tokens=total_tokens,
            prompt_tokens=total_input,
            completion_tokens=total_output,
            request_count=total_requests,
            enabled=self.is_enabled,
            last_updated=datetime.now(),
            period_start=datetime.combine(start, datetime.min.time()),
            period_end=datetime.now(),
        )

    def _fetch_cost_report(self, key: str) -> UsageData:
        """Try the cost_report endpoint as fallback."""
        today = date.today()
        start = today.replace(day=1)

        try:
            resp = requests.get(
                f"{self.BASE_URL}/v1/organizations/cost_report",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                },
                params={"starting_at": start.isoformat()},
                timeout=10,
            )
            if resp.status_code == 200:
                payload = resp.json()
                total_cost = sum(
                    item.get("cost_usd", 0) for item in payload.get("data", [])
                )
                return UsageData(
                    provider_id=self.provider_id,
                    display_name=self.display_name,
                    color=self.color,
                    cost_usd=total_cost,
                    monthly_limit_usd=self.monthly_limit_usd,
                    enabled=self.is_enabled,
                    last_updated=datetime.now(),
                )
        except Exception:
            pass

        return self.empty_usage("Admin key required — enable in Claude Console")

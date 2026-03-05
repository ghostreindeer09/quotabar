"""
OpenAI provider — fetches usage via the OpenAI Admin usage API.
Endpoint: GET https://api.openai.com/v1/organization/usage/completions
"""

import requests
from datetime import datetime, date, timedelta
from .base import BaseProvider, UsageData


class OpenAIProvider(BaseProvider):

    BASE_URL = "https://api.openai.com/v1"

    def fetch_usage(self) -> UsageData:
        if not self.api_key:
            return self.empty_usage("API key not configured")

        try:
            # First try to get costs from the costs API (newer Admin Key approach)
            data = self._fetch_costs()
            if data is not None:
                return data
            # Fall back to usage tokens endpoint
            return self._fetch_token_usage()
        except Exception as e:
            return self.empty_usage(f"Error: {str(e)[:60]}")

    def _fetch_costs(self) -> UsageData | None:
        """Fetch dollar costs via the newer /organization/costs endpoint."""
        today = date.today()
        start = today.replace(day=1)  # first of current month

        try:
            resp = requests.get(
                f"{self.BASE_URL}/organization/costs",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                params={
                    "start_time": int(datetime.combine(start, datetime.min.time()).timestamp()),
                    "limit": 1,
                    "bucket_width": "1d",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                payload = resp.json()
                total_cost = sum(
                    bucket.get("amount", {}).get("value", 0)
                    for bucket in payload.get("data", [])
                )
                return UsageData(
                    provider_id=self.provider_id,
                    display_name=self.display_name,
                    color=self.color,
                    cost_usd=total_cost,
                    monthly_limit_usd=self.monthly_limit_usd,
                    enabled=self.is_enabled,
                    last_updated=datetime.now(),
                    period_start=datetime.combine(start, datetime.min.time()),
                    period_end=datetime.now(),
                )
            elif resp.status_code == 403:
                # Not allowed — probably not an admin key, try usage endpoint
                return None
        except Exception:
            return None
        return None

    def _fetch_token_usage(self) -> UsageData:
        """Fetch token usage from the completions usage endpoint."""
        today = date.today()
        start = today.replace(day=1)

        resp = requests.get(
            f"{self.BASE_URL}/organization/usage/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            params={
                "start_time": int(datetime.combine(start, datetime.min.time()).timestamp()),
                "limit": 31,
                "bucket_width": "1d",
            },
            timeout=10,
        )

        if resp.status_code == 401:
            return self.empty_usage("Invalid API key")
        if resp.status_code == 403:
            return self.empty_usage("Admin key required for usage data")
        resp.raise_for_status()

        payload = resp.json()
        total_input = 0
        total_output = 0
        total_requests = 0
        for bucket in payload.get("data", []):
            for result in bucket.get("results", []):
                total_input += result.get("input_tokens", 0)
                total_output += result.get("output_tokens", 0)
                total_requests += result.get("num_model_requests", 0)

        total_tokens = total_input + total_output
        # Rough cost estimate: ~$0.000002 per token blended
        estimated_cost = total_tokens * 0.000002

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

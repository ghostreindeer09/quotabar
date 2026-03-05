"""
Usage fetcher — orchestrates all enabled providers concurrently.
"""

import concurrent.futures
import importlib
from typing import Dict, List
from datetime import datetime

from providers.base import UsageData, BaseProvider
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider
from providers.gemini_provider import GeminiProvider
from providers.groq_provider import GroqProvider
from providers.cohere_provider import CohereProvider
from providers.mistral_provider import MistralProvider

PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "cohere": CohereProvider,
    "mistral": MistralProvider,
}


def build_providers(config: dict) -> Dict[str, BaseProvider]:
    """Instantiate provider objects from config."""
    providers = {}
    for pid, pcfg in config.get("providers", {}).items():
        cls = PROVIDER_MAP.get(pid)
        if cls is not None:
            providers[pid] = cls(pid, pcfg)
    return providers


def fetch_all_usage(
    providers: Dict[str, BaseProvider],
    only_enabled: bool = True,
) -> Dict[str, UsageData]:
    """
    Fetch usage for all (or all enabled) providers concurrently.
    Returns a dict mapping provider_id -> UsageData.
    """
    targets = {
        pid: p for pid, p in providers.items()
        if (not only_enabled or p.is_enabled)
    }

    results: Dict[str, UsageData] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(targets) or 1)) as executor:
        future_to_pid = {
            executor.submit(_safe_fetch, p): pid
            for pid, p in targets.items()
        }
        for future in concurrent.futures.as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                results[pid] = future.result()
            except Exception as e:
                results[pid] = providers[pid].empty_usage(str(e))

    return results


def _safe_fetch(provider: BaseProvider) -> UsageData:
    """Wrapper that catches all exceptions and converts to error UsageData."""
    try:
        return provider.fetch_usage()
    except Exception as e:
        return provider.empty_usage(f"Unexpected error: {str(e)[:60]}")

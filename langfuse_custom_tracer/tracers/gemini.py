from typing import Any
from langfuse_custom_tracer.pricing_manager import pricing_manager
from .base import BaseTracer

class GeminiTracer(BaseTracer):
    """Langfuse tracer for Google Gemini models."""

    def extract_usage(self, response: Any, model: str) -> dict:
        _um = getattr(response, "usage_metadata", None)
        if not _um: return {}

        def _get_val(obj: Any, key: str) -> int:
            if hasattr(obj, key): return getattr(obj, key) or 0
            if isinstance(obj, dict): return obj.get(key) or 0
            return 0

        prompt_tokens = _get_val(_um, "prompt_token_count")
        completion_tokens = _get_val(_um, "candidates_token_count")
        cached_tokens = _get_val(_um, "cached_content_token_count")

        new_input_tokens = max(0, prompt_tokens - cached_tokens)
        total_tokens = prompt_tokens + completion_tokens

        pricing, version, source = pricing_manager.get_price(model)
        
        input_cost = (new_input_tokens * pricing.get("input", 0)) / 1_000_000
        output_cost = (completion_tokens * pricing.get("output", 0)) / 1_000_000
        cache_cost = (cached_tokens * pricing.get("cached", 0)) / 1_000_000 if cached_tokens else 0.0
        total_cost = input_cost + output_cost + cache_cost

        return {
            "input": new_input_tokens,
            "output": completion_tokens,
            "total": total_tokens,
            "unit": "TOKENS",
            "inputCost": input_cost,
            "outputCost": output_cost,
            "totalCost": total_cost,
            "_pricing_source": source,
            "_pricing_version": version,
        }
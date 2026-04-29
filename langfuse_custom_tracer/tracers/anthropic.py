from typing import Any, Dict
from langfuse_custom_tracer.pricing_manager import pricing_manager
from .base import BaseTracer

class AnthropicTracer(BaseTracer):
    """Tracer for Anthropic Claude models."""
    
    def extract_usage(self, response: Any, model: str) -> Dict[str, Any]:
        if isinstance(response, dict):
            usage_data = response.get("usage", response)
        else:
            usage_data = getattr(response, "usage", response)
            if not isinstance(usage_data, dict):
                usage_data = vars(usage_data) if hasattr(usage_data, "__dict__") else {}
        
        input_tokens = usage_data.get("input_tokens", 0) or 0
        output_tokens = usage_data.get("output_tokens", 0) or 0
        cache_read_tokens = usage_data.get("cache_read_input_tokens", 0) or 0
        cache_write_tokens = usage_data.get("cache_creation_input_tokens", 0) or 0
        
        total_tokens = input_tokens + output_tokens + cache_read_tokens + cache_write_tokens
        
        pricing, version, source = pricing_manager.get_price(model)
        
        input_cost = (input_tokens * pricing.get("input", 0)) / 1_000_000
        output_cost = (output_tokens * pricing.get("output", 0)) / 1_000_000
        cache_read_cost = (cache_read_tokens * pricing.get("cache_read", 0)) / 1_000_000
        cache_write_cost = (cache_write_tokens * pricing.get("cache_write", 0)) / 1_000_000
        
        return {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens,
            "unit": "TOKENS",
            "inputCost": input_cost,
            "outputCost": output_cost,
            "totalCost": input_cost + output_cost + cache_read_cost + cache_write_cost,
            "_pricing_source": source,
            "_pricing_version": version,
        }

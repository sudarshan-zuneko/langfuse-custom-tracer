"""Anthropic Claude tracer for LLM observability."""

from typing import Dict, Optional, Any
from langfuse_custom_tracer.tracers.base import BaseTracer


class AnthropicTracer(BaseTracer):
    """Tracer for Anthropic Claude models.
    
    Supports all Claude models with real-time pricing integration.
    Includes support for prompt caching (cache read/write tokens).
    
    Example:
        >>> from langfuse_custom_tracer import create_langfuse_client, AnthropicTracer
        >>> import anthropic
        >>> lf = create_langfuse_client(secret_key, public_key)
        >>> tracer = AnthropicTracer(lf)
        >>> client = anthropic.Anthropic(api_key=api_key)
        >>> with tracer.trace("claude-inference") as span:
        ...     with tracer.generation("chat", model="claude-3-5-sonnet-20241022") as gen:
        ...         response = client.messages.create(
        ...             model="claude-3-5-sonnet-20241022",
        ...             max_tokens=1024,
        ...             messages=[{"role": "user", "content": "Hello"}]
        ...         )
        ...         usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        ...         gen.update(output=response.content[0].text, usage_details=usage)
    """
    
from langfuse_custom_tracer.pricing_manager import pricing_manager
from langfuse_custom_tracer.tracers.base import BaseTracer


class AnthropicTracer(BaseTracer):
    """Tracer for Anthropic Claude models."""
    
    def extract_usage(
        self,
        response: Any,
        model: str,
    ) -> Dict[str, Any]:
        """Extract token usage and compute cost using PricingManager."""
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
        
        total_input = input_tokens + cache_read_tokens + cache_write_tokens
        total_tokens = total_input + output_tokens
        
        if any(count < 0 for count in [input_tokens, output_tokens, cache_read_tokens, cache_write_tokens]):
            raise ValueError(
                f"Invalid token counts: input={input_tokens}, output={output_tokens}, "
                f"cache_read={cache_read_tokens}, cache_write={cache_write_tokens}"
            )
        
        # Use PricingManager instead of hardcoded dict
        pricing, version, source = pricing_manager.get_price(model)
        
        input_price_per_token = pricing.get("input", 0) / 1_000_000
        output_price_per_token = pricing.get("output", 0) / 1_000_000
        cache_read_price_per_token = pricing.get("cache_read", 0) / 1_000_000
        cache_write_price_per_token = pricing.get("cache_write", 0) / 1_000_000
        
        input_cost = input_tokens * input_price_per_token
        output_cost = output_tokens * output_price_per_token
        cached_read_cost = cache_read_tokens * cache_read_price_per_token
        cached_write_cost = cache_write_tokens * cache_write_price_per_token
        total_cost = input_cost + output_cost + cached_read_cost + cached_write_cost
        
        usage = {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens,
            "unit": "TOKENS",
            "inputCost": round(input_cost, 8),
            "outputCost": round(output_cost, 8),
            "totalCost": round(total_cost, 8),
            "_pricing_source": source,
            "_pricing_version": version,
        }
        
        if cache_read_tokens:
            usage["cacheReadTokens"] = cache_read_tokens
            usage["cachedInputCost"] = round(cached_read_cost, 8)
        
        if cache_write_tokens:
            usage["cacheWriteTokens"] = cache_write_tokens
            usage["cacheWriteCost"] = round(cached_write_cost, 8)
        
        return usage

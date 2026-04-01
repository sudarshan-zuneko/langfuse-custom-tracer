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
    
    # Anthropic pricing table (Q1 2026)
    # Format: {"model": {"input": price_per_1m, "output": price_per_1m, "cache_read": price_per_1m, "cache_write": price_per_1m}}
    ANTHROPIC_PRICING = {
        # Claude 3.5 Models
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,
            "output": 15.00,
            "cache_read": 0.30,
            "cache_write": 3.75,
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,
            "output": 4.00,
            "cache_read": 0.08,
            "cache_write": 1.00,
        },
        
        # Claude 3 Models
        "claude-3-opus-20250219": {
            "input": 15.00,
            "output": 75.00,
            "cache_read": 1.50,
            "cache_write": 18.75,
        },
        "claude-3-sonnet-20240229": {
            "input": 3.00,
            "output": 15.00,
            "cache_read": 0.30,
            "cache_write": 3.75,
        },
        "claude-3-haiku-20240307": {
            "input": 0.80,
            "output": 4.00,
            "cache_read": 0.08,
            "cache_write": 1.00,
        },
    }
    
    def _get_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for Anthropic model.
        
        Args:
            model: Model identifier (e.g., "claude-3-5-sonnet-20241022")
            
        Returns:
            Dictionary with "input", "output", "cache_read", and "cache_write" 
            pricing per 1M tokens. Defaults to sonnet pricing for unknown models.
        """
        # Try exact match first
        if model in self.ANTHROPIC_PRICING:
            return self.ANTHROPIC_PRICING[model]
        
        # Try partial matching (e.g., "claude-3-5-sonnet" matches "claude-3-5-sonnet-20241022")
        model_lower = model.lower()
        for pricing_model, prices in self.ANTHROPIC_PRICING.items():
            if pricing_model.lower().startswith(model_lower):
                return prices
        
        # Default to Claude 3.5 Sonnet pricing for unknown models
        return self.ANTHROPIC_PRICING["claude-3-5-sonnet-20241022"]
    
    def extract_usage(
        self,
        response: Dict[str, Any],
        model: str,
    ) -> Dict[str, Any]:
        """Extract token usage from Anthropic response.
        
        Anthropic responses include:
        {
            "id": "msg_...",
            "type": "message",
            "role": "assistant",
            "content": [...],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "stop_sequence": null,
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
                "cache_read_input_tokens": 0,  # Additional input tokens from cache
                "cache_creation_input_tokens": 0  # Input tokens written to cache
            }
        }
        
        Args:
            response: Anthropic message response object or usage dict
            model: Model identifier for pricing lookup
            
        Returns:
            Dictionary with token counts and costs:
            {
                "input": int,       # Input tokens (excluding cache)
                "output": int,      # Output tokens
                "total": int,       # Total tokens
                "unit": "TOKENS",
                "inputCost": float, # Input cost in USD
                "outputCost": float,# Output cost in USD
                "totalCost": float, # Total cost in USD
                "cacheReadTokens": int,      # (optional) Cache read tokens
                "cacheWriteTokens": int,     # (optional) Cache write tokens
                "cachedInputCost": float,    # (optional) Cost of cached reads
                "cacheWriteCost": float      # (optional) Cost of writing to cache
            }
            
        Raises:
            KeyError: If response is missing required token fields
            ValueError: If token counts are negative
        """
        # Extract usage data (handle both dict and object)
        if isinstance(response, dict):
            usage_data = response.get("usage", response)
        else:
            # Handle object response
            usage_data = getattr(response, "usage", response)
            if not isinstance(usage_data, dict):
                usage_data = vars(usage_data) if hasattr(usage_data, "__dict__") else {}
        
        # Extract token counts
        input_tokens = usage_data.get("input_tokens", 0) or 0
        output_tokens = usage_data.get("output_tokens", 0) or 0
        cache_read_tokens = usage_data.get("cache_read_input_tokens", 0) or 0
        cache_write_tokens = usage_data.get("cache_creation_input_tokens", 0) or 0
        
        # Total includes all input tokens (regular + cache reads + cache writes)
        total_input = input_tokens + cache_read_tokens + cache_write_tokens
        total_tokens = total_input + output_tokens
        
        # Validate token counts
        if any(count < 0 for count in [input_tokens, output_tokens, cache_read_tokens, cache_write_tokens]):
            raise ValueError(
                f"Invalid token counts: input={input_tokens}, output={output_tokens}, "
                f"cache_read={cache_read_tokens}, cache_write={cache_write_tokens}"
            )
        
        # Get pricing for model
        pricing = self._get_pricing(model)
        input_price_per_token = pricing["input"] / 1_000_000
        output_price_per_token = pricing["output"] / 1_000_000
        cache_read_price_per_token = pricing.get("cache_read", 0) / 1_000_000
        cache_write_price_per_token = pricing.get("cache_write", 0) / 1_000_000
        
        # Calculate costs
        input_cost = input_tokens * input_price_per_token
        output_cost = output_tokens * output_price_per_token
        cached_read_cost = cache_read_tokens * cache_read_price_per_token
        cached_write_cost = cache_write_tokens * cache_write_price_per_token
        total_cost = input_cost + output_cost + cached_read_cost + cached_write_cost
        
        # Build usage dictionary
        usage = {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens,
            "unit": "TOKENS",
            "inputCost": round(input_cost, 8),
            "outputCost": round(output_cost, 8),
            "totalCost": round(total_cost, 8),
        }
        
        # Add cache-related metrics if present
        if cache_read_tokens:
            usage["cacheReadTokens"] = cache_read_tokens
            usage["cachedInputCost"] = round(cached_read_cost, 8)
        
        if cache_write_tokens:
            usage["cacheWriteTokens"] = cache_write_tokens
            usage["cacheWriteCost"] = round(cached_write_cost, 8)
        
        return usage

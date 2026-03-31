"""Unit tests for AnthropicTracer."""

import pytest
from unittest.mock import MagicMock
from langfuse_custom_tracer.tracers.anthropic import AnthropicTracer


@pytest.fixture
def mock_langfuse_client():
    """Create mock Langfuse client."""
    client = MagicMock()
    client.trace.return_value.__enter__ = MagicMock()
    client.trace.return_value.__exit__ = MagicMock(return_value=False)
    return client


@pytest.fixture
def tracer(mock_langfuse_client):
    """Create AnthropicTracer with mock client."""
    return AnthropicTracer(mock_langfuse_client)


class TestAnthropicTracerInitialization:
    """Test AnthropicTracer initialization."""
    
    def test_anthropic_tracer_creation(self, tracer):
        """Test that AnthropicTracer initializes correctly."""
        assert tracer is not None
        assert hasattr(tracer, 'extract_usage')
        assert hasattr(tracer, 'trace')
        assert hasattr(tracer, 'generation')
    
    def test_pricing_table_exists(self, tracer):
        """Test that pricing table is available."""
        assert hasattr(tracer, 'ANTHROPIC_PRICING')
        assert isinstance(tracer.ANTHROPIC_PRICING, dict)
        assert len(tracer.ANTHROPIC_PRICING) >= 5


class TestAnthropicPricingLookup:
    """Test Claude model pricing lookup."""
    
    def test_get_pricing_claude_3_5_sonnet(self, tracer):
        """Test pricing for Claude 3.5 Sonnet."""
        pricing = tracer._get_pricing("claude-3-5-sonnet-20241022")
        assert pricing["input"] == 3.00
        assert pricing["output"] == 15.00
        assert pricing["cache_read"] == 0.30
        assert pricing["cache_write"] == 3.75
    
    def test_get_pricing_claude_3_5_haiku(self, tracer):
        """Test pricing for Claude 3.5 Haiku."""
        pricing = tracer._get_pricing("claude-3-5-haiku-20241022")
        assert pricing["input"] == 0.80
        assert pricing["output"] == 4.00
        assert pricing["cache_read"] == 0.08
        assert pricing["cache_write"] == 1.00
    
    def test_get_pricing_claude_3_opus(self, tracer):
        """Test pricing for Claude 3 Opus."""
        pricing = tracer._get_pricing("claude-3-opus-20250219")
        assert pricing["input"] == 15.00
        assert pricing["output"] == 75.00
    
    def test_get_pricing_claude_3_sonnet(self, tracer):
        """Test pricing for Claude 3 Sonnet."""
        pricing = tracer._get_pricing("claude-3-sonnet-20240229")
        assert pricing["input"] == 3.00
        assert pricing["output"] == 15.00
    
    def test_get_pricing_claude_3_haiku(self, tracer):
        """Test pricing for Claude 3 Haiku."""
        pricing = tracer._get_pricing("claude-3-haiku-20240307")
        assert pricing["input"] == 0.80
        assert pricing["output"] == 4.00
    
    def test_get_pricing_partial_match(self, tracer):
        """Test pricing lookup with partial model name."""
        pricing = tracer._get_pricing("claude-3-5-sonnet")
        # Should match "claude-3-5-sonnet-20241022"
        assert pricing["input"] == 3.00
    
    def test_get_pricing_case_insensitive(self, tracer):
        """Test pricing lookup is case insensitive."""
        pricing_lower = tracer._get_pricing("claude-3-5-sonnet-20241022")
        pricing_upper = tracer._get_pricing("CLAUDE-3-5-SONNET-20241022")
        assert pricing_lower == pricing_upper
    
    def test_get_pricing_unknown_model_defaults(self, tracer):
        """Test pricing lookup for unknown model defaults to Sonnet."""
        pricing = tracer._get_pricing("unknown-claude-model")
        # Should default to Claude 3.5 Sonnet
        assert pricing["input"] == 3.00
        assert pricing["output"] == 15.00


class TestAnthropicExtractUsageBasic:
    """Test basic token extraction from Anthropic responses."""
    
    def test_extract_usage_basic(self, tracer):
        """Test basic usage extraction."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 42
        assert usage["output"] == 15
        assert usage["total"] == 57
        assert usage["unit"] == "TOKENS"
    
    def test_extract_usage_without_usage_wrapper(self, tracer):
        """Test extraction when response is the usage dict directly."""
        response = {
            "input_tokens": 42,
            "output_tokens": 15,
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 42
        assert usage["output"] == 15
    
    def test_extract_usage_zero_tokens(self, tracer):
        """Test extraction with zero tokens."""
        response = {
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 0
        assert usage["output"] == 0
        assert usage["total"] == 0
    
    def test_extract_usage_high_token_count(self, tracer):
        """Test extraction with high token count."""
        response = {
            "usage": {
                "input_tokens": 100000,
                "output_tokens": 50000,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 100000
        assert usage["output"] == 50000
        assert usage["total"] == 150000


class TestAnthropicExtractUsageCosts:
    """Test cost calculation for Anthropic responses."""
    
    def test_extract_usage_basic_cost_sonnet(self, tracer):
        """Test cost calculation for Claude 3.5 Sonnet."""
        response = {
            "usage": {
                "input_tokens": 1000000,  # 1M tokens
                "output_tokens": 1000000, # 1M tokens
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        # Input: 1M @ $3/1M = $3
        # Output: 1M @ $15/1M = $15
        # Total: $18
        assert usage["inputCost"] == pytest.approx(3.0, rel=0.01)
        assert usage["outputCost"] == pytest.approx(15.0, rel=0.01)
        assert usage["totalCost"] == pytest.approx(18.0, rel=0.01)
    
    def test_extract_usage_basic_cost_haiku(self, tracer):
        """Test cost calculation for Claude 3.5 Haiku."""
        response = {
            "usage": {
                "input_tokens": 1000,   # 1k tokens
                "output_tokens": 1000,  # 1k tokens
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-haiku-20241022")
        
        # Input: 1k @ $0.80/1M = $0.0008
        # Output: 1k @ $4.00/1M = $0.004
        # Total: $0.0048
        assert usage["inputCost"] == pytest.approx(0.0008, abs=0.00001)
        assert usage["outputCost"] == pytest.approx(0.004, abs=0.00001)
        assert usage["totalCost"] == pytest.approx(0.0048, abs=0.00001)
    
    def test_extract_usage_zero_cost(self, tracer):
        """Test cost is zero for zero tokens."""
        response = {
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["inputCost"] == 0.0
        assert usage["outputCost"] == 0.0
        assert usage["totalCost"] == 0.0


class TestAnthropicExtractUsageCache:
    """Test cache token handling."""
    
    def test_extract_usage_with_cache_read(self, tracer):
        """Test extraction with cache read tokens."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
                "cache_read_input_tokens": 100,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 42
        assert usage["output"] == 15
        assert usage["total"] == 157  # 42 + 100 + 15
        assert usage["cacheReadTokens"] == 100
    
    def test_extract_usage_with_cache_write(self, tracer):
        """Test extraction with cache write tokens."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
                "cache_creation_input_tokens": 200,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["cacheWriteTokens"] == 200
    
    def test_extract_usage_with_both_cache_types(self, tracer):
        """Test extraction with both cache read and write."""
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_input_tokens": 200,
                "cache_creation_input_tokens": 150,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 100
        assert usage["output"] == 50
        assert usage["total"] == 500  # 100 + 200 + 150 + 50
        assert usage["cacheReadTokens"] == 200
        assert usage["cacheWriteTokens"] == 150
    
    def test_extract_usage_cache_cost_sonnet(self, tracer):
        """Test cache token cost calculation."""
        response = {
            "usage": {
                "input_tokens": 1000000,    # 1M @ $3/1M = $3
                "output_tokens": 1000000,   # 1M @ $15/1M = $15
                "cache_read_input_tokens": 1000000,      # 1M @ $0.30/1M = $0.30
                "cache_creation_input_tokens": 1000000,  # 1M @ $3.75/1M = $3.75
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["inputCost"] == pytest.approx(3.0, rel=0.01)
        assert usage["outputCost"] == pytest.approx(15.0, rel=0.01)
        assert usage["cachedInputCost"] == pytest.approx(0.30, rel=0.01)
        assert usage["cacheWriteCost"] == pytest.approx(3.75, rel=0.01)
        assert usage["totalCost"] == pytest.approx(22.05, rel=0.01)


class TestAnthropicExtractUsageMissingFields:
    """Test handling of missing or None token fields."""
    
    def test_extract_usage_missing_tokens(self, tracer):
        """Test extraction when token fields are missing."""
        response = {
            "usage": {}
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 0
        assert usage["output"] == 0
        assert usage["total"] == 0
    
    def test_extract_usage_none_tokens(self, tracer):
        """Test extraction when tokens are None."""
        response = {
            "usage": {
                "input_tokens": None,
                "output_tokens": None,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 0
        assert usage["output"] == 0
    
    def test_extract_usage_missing_cache_tokens(self, tracer):
        """Test extraction without cache token fields."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert "cacheReadTokens" not in usage
        assert "cacheWriteTokens" not in usage


class TestAnthropicExtractUsageErrors:
    """Test error handling in usage extraction."""
    
    def test_extract_usage_negative_input_tokens(self, tracer):
        """Test error handling for negative input tokens."""
        response = {
            "usage": {
                "input_tokens": -5,
                "output_tokens": 50,
            }
        }
        
        with pytest.raises(ValueError, match="Invalid token counts"):
            tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
    
    def test_extract_usage_negative_output_tokens(self, tracer):
        """Test error handling for negative output tokens."""
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": -10,
            }
        }
        
        with pytest.raises(ValueError, match="Invalid token counts"):
            tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
    
    def test_extract_usage_negative_cache_tokens(self, tracer):
        """Test error handling for negative cache tokens."""
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_input_tokens": -10,
            }
        }
        
        with pytest.raises(ValueError, match="Invalid token counts"):
            tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")


class TestAnthropicExtractUsageDataStructure:
    """Test the structure of returned usage data."""
    
    def test_extract_usage_returns_dict(self, tracer):
        """Test that extract_usage returns a dictionary."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert isinstance(usage, dict)
    
    def test_extract_usage_required_fields(self, tracer):
        """Test that all required fields are present."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        required_fields = {
            "input", "output", "total", "unit",
            "inputCost", "outputCost", "totalCost"
        }
        assert required_fields.issubset(usage.keys())
    
    def test_extract_usage_field_types(self, tracer):
        """Test that fields have correct types."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert isinstance(usage["input"], int)
        assert isinstance(usage["output"], int)
        assert isinstance(usage["total"], int)
        assert isinstance(usage["unit"], str)
        assert isinstance(usage["inputCost"], float)
        assert isinstance(usage["outputCost"], float)
        assert isinstance(usage["totalCost"], float)
    
    def test_extract_usage_with_cache_field_types(self, tracer):
        """Test field types when cache tokens are present."""
        response = {
            "usage": {
                "input_tokens": 42,
                "output_tokens": 15,
                "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": 50,
            }
        }
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert isinstance(usage["cacheReadTokens"], int)
        assert isinstance(usage["cacheWriteTokens"], int)
        assert isinstance(usage["cachedInputCost"], float)
        assert isinstance(usage["cacheWriteCost"], float)


class TestAnthropicTracerIntegration:
    """Test AnthropicTracer integration with trace methods."""
    
    def test_anthropic_tracer_with_trace(self, tracer):
        """Test AnthropicTracer works with trace() context manager."""
        with tracer.trace("test-trace") as span:
            assert span is not None
    
    def test_anthropic_tracer_with_generation(self, tracer):
        """Test AnthropicTracer works with generation() context manager."""
        with tracer.generation("test-gen", model="claude-3-5-sonnet-20241022") as gen:
            assert gen is not None
    
    def test_anthropic_tracer_extract_usage_realistic(self, tracer):
        """Test extract_usage in realistic scenario."""
        # Typical Anthropic response structure
        response = {
            "id": "msg_13nxg2sq",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "The capital of France is Paris."}],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": 12,
                "output_tokens": 8,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            }
        }
        
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 12
        assert usage["output"] == 8
        assert usage["total"] == 20
        assert usage["totalCost"] > 0


class TestAnthropicTracerModelVariants:
    """Test handling of various Claude model naming conventions."""
    
    def test_extract_usage_all_claude_3_5_models(self, tracer):
        """Test all Claude 3.5 model variants are supported."""
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
        
        for model in ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]:
            usage = tracer.extract_usage(response, model=model)
            assert "inputCost" in usage
            assert "outputCost" in usage
    
    def test_extract_usage_all_claude_3_models(self, tracer):
        """Test all Claude 3 model variants are supported."""
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
        
        for model in ["claude-3-opus-20250219", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]:
            usage = tracer.extract_usage(response, model=model)
            assert "inputCost" in usage
            assert "outputCost" in usage


class TestAnthropicTracerForwardCompatibility:
    """Test forward compatibility with future Claude models."""
    
    def test_unknown_claude_model_uses_default(self, tracer):
        """Test unknown Claude models default gracefully."""
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
        usage = tracer.extract_usage(response, model="claude-4-future")
        
        # Should use default (Claude 3.5 Sonnet) pricing
        assert usage["inputCost"] > 0
        assert usage["outputCost"] > 0
    
    def test_claude_variant_partial_match(self, tracer):
        """Test partial matching for Claude model variants."""
        response = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
        # Just the base model name, no date
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet")
        
        # Should match "claude-3-5-sonnet-20241022"
        assert usage["inputCost"] == pytest.approx(3.0 * 100 / 1_000_000, rel=0.01)


class TestAnthropicTracerObjectResponse:
    """Test handling of object responses (not just dicts)."""
    
    @pytest.fixture
    def mock_langfuse_client(self):
        """Create mock Langfuse client."""
        client = MagicMock()
        client.trace.return_value.__enter__ = MagicMock()
        client.trace.return_value.__exit__ = MagicMock(return_value=False)
        return client
    
    @pytest.fixture
    def tracer(self, mock_langfuse_client):
        """Create AnthropicTracer with mock client."""
        return AnthropicTracer(mock_langfuse_client)
    
    def test_extract_usage_with_object_response(self, tracer):
        """Test extraction from object response (not dict)."""
        # Create a mock object that acts like an Anthropic response
        response = MagicMock()
        response.usage = {
            "input_tokens": 42,
            "output_tokens": 15,
        }
        
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 42
        assert usage["output"] == 15
        assert usage["total"] == 57
    
    def test_extract_usage_with_nested_object_response(self, tracer):
        """Test extraction from object with nested usage object."""
        # Create response object with object-based usage
        class UsageObject:
            def __init__(self):
                self.input_tokens = 100
                self.output_tokens = 50
        
        class ResponseObject:
            def __init__(self):
                self.usage = UsageObject()
        
        response = ResponseObject()
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        
        assert usage["input"] == 100
        assert usage["output"] == 50
        assert usage["total"] == 150

"""
Unit tests for GeminiTracer class.
"""

from unittest.mock import Mock
import pytest
from langfuse_custom_tracer.tracers.gemini import GeminiTracer, _get_pricing


class TestGeminiPricing:
    """Test pricing lookup function."""

    def test_exact_model_match(self):
        """Test exact model name match."""
        pricing = _get_pricing("gemini-2.0-flash")
        assert pricing["input"] == 0.15
        assert pricing["output"] == 0.60
        assert pricing["cached"] == 0.0375

    def test_case_insensitive_match(self):
        """Test case-insensitive model match."""
        pricing = _get_pricing("GEMINI-2.0-FLASH")
        assert pricing["input"] == 0.15
        assert pricing["output"] == 0.60

    def test_partial_model_match(self):
        """Test partial model name match."""
        pricing = _get_pricing("gemini-2.0-flash-lite")
        assert pricing["input"] == 0.075
        assert pricing["output"] == 0.30

    def test_default_pricing_fallback(self):
        """Test fallback to default pricing for unknown model."""
        pricing = _get_pricing("unknown-model-xyz")
        assert pricing["input"] == 0.15
        assert pricing["output"] == 0.60
        assert pricing["cached"] == 0.0375

    def test_all_gemini_models(self):
        """Test all known Gemini models have pricing."""
        models = [
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ]
        
        for model in models:
            pricing = _get_pricing(model)
            assert pricing["input"] > 0
            assert pricing["output"] > 0
            assert pricing["cached"] > 0


class TestGeminiTracer:
    """Test cases for GeminiTracer class."""

    def test_init(self, mock_langfuse_client):
        """Test GeminiTracer initialization."""
        tracer = GeminiTracer(mock_langfuse_client)
        assert tracer._lf == mock_langfuse_client

    def test_extract_usage_basic(self, mock_langfuse_client, gemini_response_with_usage):
        """Test extract_usage with basic response."""
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage,
                                     model="gemini-2.0-flash")
        
        assert usage["input"] == 90  # 100 - 10 cached
        assert usage["output"] == 50
        assert usage["total"] == 150
        assert usage["unit"] == "TOKENS"
        assert usage["cachedTokens"] == 10
        assert usage["inputCost"] > 0
        assert usage["outputCost"] > 0
        assert usage["totalCost"] > 0

    def test_extract_usage_no_response(self, mock_langfuse_client, gemini_response_without_usage):
        """Test extract_usage with response without usage metadata."""
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_without_usage,
                                     model="gemini-2.0-flash")
        
        assert usage == {}

    def test_extract_usage_cost_calculation(self, mock_langfuse_client, gemini_response_with_usage):
        """Test cost calculation in extract_usage."""
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage,
                                     model="gemini-2.0-flash")
        
        # Gemini 2.0 Flash: input=$0.15/1M, output=$0.60/1M, cached=$0.0375/1M
        expected_input_cost = (90 * 0.15) / 1_000_000
        expected_output_cost = (50 * 0.60) / 1_000_000
        expected_cache_cost = (10 * 0.0375) / 1_000_000
        expected_total = expected_input_cost + expected_output_cost + expected_cache_cost
        
        assert abs(usage["inputCost"] - expected_input_cost) < 0.00001
        assert abs(usage["outputCost"] - expected_output_cost) < 0.00001
        assert abs(usage["totalCost"] - expected_total) < 0.00001

    def test_extract_usage_different_models(self, mock_langfuse_client, gemini_response_with_usage):
        """Test extract_usage with different models."""
        tracer = GeminiTracer(mock_langfuse_client)
        
        # Test with gemini-2.5-pro (more expensive)
        usage_pro = tracer.extract_usage(gemini_response_with_usage,
                                         model="gemini-2.5-pro")
        
        # Test with gemini-2.0-flash-lite (cheaper)
        usage_lite = tracer.extract_usage(gemini_response_with_usage,
                                          model="gemini-2.0-flash-lite")
        
        # Pro should be more expensive than lite
        assert usage_pro["inputCost"] > usage_lite["inputCost"]
        assert usage_pro["outputCost"] > usage_lite["outputCost"]

    def test_extract_usage_no_cached_tokens(self, mock_langfuse_client):
        """Test extract_usage when there are no cached tokens."""
        response = Mock()
        usage_metadata = Mock()
        usage_metadata.prompt_token_count = 100
        usage_metadata.candidates_token_count = 50
        usage_metadata.total_token_count = 150
        usage_metadata.cached_content_token_count = 0
        
        response.usage_metadata = usage_metadata
        
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(response, model="gemini-2.0-flash")
        
        assert usage["input"] == 100
        assert "cachedTokens" not in usage

    def test_extract_usage_zero_cached_tokens(self, mock_langfuse_client):
        """Test extract_usage with None cached_content_token_count."""
        response = Mock()
        usage_metadata = Mock()
        usage_metadata.prompt_token_count = 100
        usage_metadata.candidates_token_count = 50
        usage_metadata.total_token_count = 150
        usage_metadata.cached_content_token_count = None
        
        response.usage_metadata = usage_metadata
        
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(response, model="gemini-2.0-flash")
        
        assert usage["input"] == 100

    def test_extract_usage_missing_fields(self, mock_langfuse_client):
        """Test extract_usage with missing usage fields."""
        response = Mock()
        usage_metadata = Mock()
        # Only set some fields
        usage_metadata.prompt_token_count = None
        usage_metadata.candidates_token_count = 50
        usage_metadata.total_token_count = 50
        usage_metadata.cached_content_token_count = None
        
        response.usage_metadata = usage_metadata
        
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(response, model="gemini-2.0-flash")
        
        assert usage["input"] == 0
        assert usage["output"] == 50

    def test_extract_usage_high_token_count(self, mock_langfuse_client):
        """Test extract_usage with high token counts."""
        response = Mock()
        usage_metadata = Mock()
        usage_metadata.prompt_token_count = 1_000_000
        usage_metadata.candidates_token_count = 500_000
        usage_metadata.total_token_count = 1_500_000
        usage_metadata.cached_content_token_count = 100_000
        
        response.usage_metadata = usage_metadata
        
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(response, model="gemini-2.0-flash")
        
        assert usage["input"] == 900_000  # 1M - 100K
        assert usage["output"] == 500_000
        assert usage["total"] == 1_500_000
        # Should calculate significant costs
        assert usage["inputCost"] > 0.1
        assert usage["outputCost"] > 0.25

    def test_extract_usage_default_model(self, mock_langfuse_client, gemini_response_with_usage):
        """Test extract_usage uses default model."""
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage)  # No model specified
        
        assert "inputCost" in usage
        assert usage["input"] == 90

    def test_extract_usage_returns_dict(self, mock_langfuse_client, gemini_response_with_usage):
        """Test extract_usage returns proper dict structure."""
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage,
                                     model="gemini-2.0-flash")
        
        required_keys = ["input", "output", "total", "unit", "inputCost", "outputCost", "totalCost"]
        for key in required_keys:
            assert key in usage

    def test_inherits_from_base_tracer(self, mock_langfuse_client):
        """Test GeminiTracer inherits from BaseTracer."""
        tracer = GeminiTracer(mock_langfuse_client)
        
        # Should have BaseTracer methods
        assert hasattr(tracer, "trace")
        assert hasattr(tracer, "generation")
        assert hasattr(tracer, "flush")

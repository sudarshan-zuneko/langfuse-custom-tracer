"""
Unit tests for GeminiTracer class.
"""

import time
from unittest.mock import Mock
import pytest
from langfuse_custom_tracer.tracers.gemini import GeminiTracer
from langfuse_custom_tracer.pricing_manager import get_pricing_manager, reset_pricing_manager


# ─── Fixtures ────────────────────────────────────────────────────

SAMPLE_PRICING = {
    "gemini-2.5-pro":        {"input": 1.25,  "output": 10.00, "cached": 0.3125},
    "gemini-2.5-flash":      {"input": 0.30,  "output": 2.50,  "cached": 0.075},
    "gemini-2.0-flash":      {"input": 0.15,  "output": 0.60,  "cached": 0.0375},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30,  "cached": 0.01875},
    "gemini-1.5-pro":        {"input": 1.25,  "output": 5.00,  "cached": 0.3125},
    "gemini-1.5-flash":      {"input": 0.075, "output": 0.30,  "cached": 0.01875},
    "gemini-1.5-flash-8b":   {"input": 0.0375,"output": 0.15,  "cached": 0.01},
}


@pytest.fixture(autouse=True)
def seed_pricing():
    """Seed PricingManager with known pricing for deterministic tests."""
    reset_pricing_manager()
    pm = get_pricing_manager()
    pm._cache = dict(SAMPLE_PRICING)
    pm._version = "test-gemini"
    pm._last_fetch = time.monotonic()
    yield
    reset_pricing_manager()


# ─── Pricing lookup tests ────────────────────────────────────────

class TestGeminiPricing:
    """Test pricing lookup via PricingManager."""

    def test_exact_model_match(self):
        pm = get_pricing_manager()
        price, _, source = pm.get_price("gemini-2.0-flash")
        assert price["input"] == 0.15
        assert price["output"] == 0.60
        assert price["cached"] == 0.0375
        assert source == "json"

    def test_case_insensitive_match(self):
        pm = get_pricing_manager()
        price, _, source = pm.get_price("GEMINI-2.0-FLASH")
        assert price["input"] == 0.15
        assert source == "json"

    def test_partial_model_match(self):
        pm = get_pricing_manager()
        price, _, source = pm.get_price("gemini-2.0-flash-lite")
        assert price["input"] == 0.075
        assert price["output"] == 0.30

    def test_default_pricing_fallback(self):
        pm = get_pricing_manager()
        price, _, source = pm.get_price("unknown-model-xyz")
        assert price["input"] == 0.0
        assert price["output"] == 0.0
        assert source == "default"

    def test_all_gemini_models(self):
        models = [
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ]
        pm = get_pricing_manager()
        for model in models:
            price, _, source = pm.get_price(model)
            assert price["input"] > 0
            assert price["output"] > 0
            assert source == "json"


# ─── Tracer tests ────────────────────────────────────────────────

class TestGeminiTracer:
    """Test cases for GeminiTracer class."""

    def test_init(self, mock_langfuse_client):
        tracer = GeminiTracer(mock_langfuse_client)
        assert tracer._lf == mock_langfuse_client

    def test_extract_usage_basic(self, mock_langfuse_client, gemini_response_with_usage):
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
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_without_usage,
                                     model="gemini-2.0-flash")
        assert usage == {}

    def test_extract_usage_cost_calculation(self, mock_langfuse_client, gemini_response_with_usage):
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage,
                                     model="gemini-2.0-flash")
        
        expected_input_cost = (90 * 0.15) / 1_000_000
        expected_output_cost = (50 * 0.60) / 1_000_000
        expected_cache_cost = (10 * 0.0375) / 1_000_000
        expected_total = expected_input_cost + expected_output_cost + expected_cache_cost
        
        assert abs(usage["inputCost"] - expected_input_cost) < 0.00001
        assert abs(usage["outputCost"] - expected_output_cost) < 0.00001
        assert abs(usage["totalCost"] - expected_total) < 0.00001

    def test_extract_usage_different_models(self, mock_langfuse_client, gemini_response_with_usage):
        tracer = GeminiTracer(mock_langfuse_client)
        
        usage_pro = tracer.extract_usage(gemini_response_with_usage,
                                         model="gemini-2.5-pro")
        usage_lite = tracer.extract_usage(gemini_response_with_usage,
                                          model="gemini-2.0-flash-lite")
        
        assert usage_pro["inputCost"] > usage_lite["inputCost"]
        assert usage_pro["outputCost"] > usage_lite["outputCost"]

    def test_extract_usage_gemini_2_5_flash(self, mock_langfuse_client, gemini_response_with_usage):
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage,
                                     model="gemini-2.5-flash")
        
        expected_total = (90 * 0.30 + 50 * 2.50 + 10 * 0.075) / 1_000_000
        assert abs(usage["totalCost"] - expected_total) < 1e-9

    def test_extract_usage_no_cached_tokens(self, mock_langfuse_client):
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
        response = Mock()
        usage_metadata = Mock()
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
        response = Mock()
        usage_metadata = Mock()
        usage_metadata.prompt_token_count = 1_000_000
        usage_metadata.candidates_token_count = 500_000
        usage_metadata.total_token_count = 1_500_000
        usage_metadata.cached_content_token_count = 100_000
        response.usage_metadata = usage_metadata
        
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(response, model="gemini-2.0-flash")
        
        assert usage["input"] == 900_000
        assert usage["output"] == 500_000
        assert usage["total"] == 1_500_000
        assert usage["inputCost"] > 0.1
        assert usage["outputCost"] > 0.25

    def test_extract_usage_requires_model(self, mock_langfuse_client, gemini_response_with_usage):
        tracer = GeminiTracer(mock_langfuse_client)
        with pytest.raises(TypeError):
            tracer.extract_usage(gemini_response_with_usage)

    def test_extract_usage_returns_dict(self, mock_langfuse_client, gemini_response_with_usage):
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage,
                                     model="gemini-2.0-flash")
        
        required_keys = ["input", "output", "total", "unit", "inputCost", "outputCost", "totalCost"]
        for key in required_keys:
            assert key in usage

    def test_extract_usage_includes_pricing_metadata(self, mock_langfuse_client, gemini_response_with_usage):
        tracer = GeminiTracer(mock_langfuse_client)
        usage = tracer.extract_usage(gemini_response_with_usage,
                                     model="gemini-2.0-flash")
        assert usage["pricing_source"] == "json"
        assert usage["pricing_version"] == "test-gemini"

    def test_inherits_from_base_tracer(self, mock_langfuse_client):
        tracer = GeminiTracer(mock_langfuse_client)
        assert hasattr(tracer, "trace")
        assert hasattr(tracer, "generation")
        assert hasattr(tracer, "flush")

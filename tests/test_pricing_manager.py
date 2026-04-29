import pytest
from unittest.mock import patch, MagicMock
from langfuse_custom_tracer.pricing_manager import PricingManager

@pytest.fixture
def manager():
    return PricingManager(url="http://mock.url", ttl=60)

def test_pricing_manager_fetch_success(manager):
    mock_data = {
        "version": "v123",
        "models": {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gemini-pro": {"input": 0.01, "output": 0.02}
        }
    }
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        manager._fetch_remote()
        
        price, version, source = manager.get_price("gpt-4")
        assert price["input"] == 0.03
        assert version == "v123"
        assert source == "json"

def test_pricing_manager_fallback_to_langfuse(manager):
    # No fetch done yet, so cache is empty
    price, version, source = manager.get_price("unknown-model")
    assert price["input"] == 0.0
    assert source == "langfuse"

def test_pricing_manager_partial_match(manager):
    manager._cache = {"gemini-1.5": {"input": 0.5, "output": 1.0}}
    manager._version = "v1"
    
    price, version, source = manager.get_price("gemini-1.5-flash")
    assert price["input"] == 0.5
    assert source == "json"

def test_pricing_manager_timeout_silent_failure(manager):
    with patch("requests.get", side_effect=Exception("Timeout")):
        # Should not raise
        manager._fetch_remote()
        assert manager._cache == {}
        
def test_pricing_manager_ttl(manager):
    manager._last_fetch = 0 # force expire
    with patch.object(manager, "_fetch_remote") as mock_fetch:
        manager.get_price("any")
        mock_fetch.assert_called_once()

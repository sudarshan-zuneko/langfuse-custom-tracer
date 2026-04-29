import pytest
from unittest.mock import MagicMock, patch
import os
import sys

# Mock dependencies
sys.modules["google.generativeai"] = MagicMock()
sys.modules["anthropic"] = MagicMock()
sys.modules["anthropic.resources"] = MagicMock()
sys.modules["anthropic.resources.messages"] = MagicMock()

from langfuse_custom_tracer import observe, set_user, set_session, score, get_trace_id

@pytest.fixture(autouse=True)
def reset_auto_client():
    """Reset the global _client in auto.py before each test."""
    from langfuse_custom_tracer import auto
    auto._client = None
    yield
    auto._client = None

@pytest.fixture
def mock_langfuse():
    with patch("langfuse_custom_tracer.auto.get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client

def test_auto_patch_observes(mock_langfuse):
    with patch.dict(os.environ, {"LANGFUSE_SECRET_KEY": "sk-test", "LANGFUSE_PUBLIC_KEY": "pk-test"}):
        observe()
        from langfuse_custom_tracer.auto import _get_langfuse
        client = _get_langfuse()
        assert client is not None

def test_context_propagation():
    set_user("user123")
    set_session("sess456")
    from langfuse_custom_tracer.context import get_user, get_session
    assert get_user() == "user123"
    assert get_session() == "sess456"

def test_scoring_success(mock_langfuse):
    with patch.dict(os.environ, {"LANGFUSE_SECRET_KEY": "sk-test", "LANGFUSE_PUBLIC_KEY": "pk-test"}):
        from langfuse_custom_tracer.context import _set_trace_id
        _set_trace_id("trace_abc")
        score("relevance", 0.9)
        mock_langfuse.score.assert_called_once()

def test_score_clamping(mock_langfuse):
    with patch.dict(os.environ, {"LANGFUSE_SECRET_KEY": "sk-test", "LANGFUSE_PUBLIC_KEY": "pk-test"}):
        from langfuse_custom_tracer.context import _set_trace_id
        _set_trace_id("trace_abc")
        score("helpfulness", 1.5)
        # Value is the 3rd positional arg or 'value' kwarg
        args, kwargs = mock_langfuse.score.call_args
        assert kwargs.get("value") == 1.0 or args[2] == 1.0

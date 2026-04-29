import pytest
from unittest.mock import MagicMock, patch
import os

# Mock dependencies before importing langfuse_custom_tracer.auto
import sys
sys.modules["google.generativeai"] = MagicMock()
sys.modules["anthropic"] = MagicMock()

from langfuse_custom_tracer import observe, set_user, set_session, score, get_trace_id

@pytest.fixture
def mock_langfuse():
    with patch("langfuse_custom_tracer.auto.get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client

def test_auto_patch_observes(mock_langfuse):
    observe()
    # verify patching logic called (hard to check exact wrapt state but can check if client was initialized)
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
    # Mock a trace ID in context
    from langfuse_custom_tracer.context import _set_trace_id
    _set_trace_id("trace_abc")
    
    score("relevance", 0.9)
    
    mock_langfuse.score.assert_called_once_with(
        trace_id="trace_abc",
        name="relevance",
        value=0.9,
        comment=None,
        data_type="NUMERIC"
    )

def test_score_clamping(mock_langfuse):
    from langfuse_custom_tracer.context import _set_trace_id
    _set_trace_id("trace_abc")
    
    score("helpfulness", 1.5) # Should clamp to 1.0
    
    mock_langfuse.score.assert_called_with(
        trace_id="trace_abc",
        name="helpfulness",
        value=1.0,
        comment=None,
        data_type="NUMERIC"
    )

def test_score_no_trace_raises():
    from langfuse_custom_tracer.context import _set_trace_id
    from langfuse_custom_tracer.context import _trace_id
    _trace_id.set(None)
    
    with pytest.raises(RuntimeError, match="no active trace_id found"):
        score("test", 1.0)

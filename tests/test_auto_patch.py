import pytest
from unittest.mock import MagicMock, patch
import os
import sys

# Mock dependencies before importing langfuse_custom_tracer.auto
sys.modules["google.generativeai"] = MagicMock()
sys.modules["anthropic"] = MagicMock()

from langfuse_custom_tracer import observe, set_user, set_session, score, get_trace_id

@pytest.fixture
def mock_langfuse():
    with patch("langfuse_custom_tracer.auto._client", new_callable=MagicMock) as mock_client:
        yield mock_client

@pytest.fixture(autouse=True)
def reset_context_vars():
    from langfuse_custom_tracer.context import _trace_id, _user_id, _session_id
    _trace_id.set(None)
    _user_id.set(None)
    _session_id.set(None)
    yield

def test_auto_patch_observes():
    # Temporarily set environment variables for the test
    os.environ["LANGFUSE_SECRET_KEY"] = "dummy_secret"
    os.environ["LANGFUSE_PUBLIC_KEY"] = "dummy_public"
    
    observe()
    
    from langfuse_custom_tracer.auto import _get_langfuse
    client = _get_langfuse()
    assert client is not None
    
    # Clean up environment variables
    del os.environ["LANGFUSE_SECRET_KEY"]
    del os.environ["LANGFUSE_PUBLIC_KEY"]

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

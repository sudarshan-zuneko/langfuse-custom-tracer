"""
Unit tests for BaseTracer class.
"""

from unittest.mock import Mock, patch, call
import pytest
from langfuse_custom_tracer.tracers.base import BaseTracer


class TestBaseTracer:
    """Test cases for BaseTracer class."""

    def test_init(self, mock_langfuse_client):
        """Test BaseTracer initialization."""
        tracer = BaseTracer(mock_langfuse_client)
        assert tracer._lf == mock_langfuse_client

    def test_init_with_none(self):
        """Test BaseTracer initialization with None client."""
        tracer = BaseTracer(None)
        assert tracer._lf is None

    def test_trace_context_manager(self, mock_langfuse_client):
        """Test trace() context manager creates observation."""
        tracer = BaseTracer(mock_langfuse_client)
        
        with tracer.trace("test-trace", input={"file": "test.txt"}) as span:
            assert span is not None
        
        # Verify start_as_current_observation was called with correct params
        mock_langfuse_client.start_as_current_observation.assert_called_once()
        call_kwargs = mock_langfuse_client.start_as_current_observation.call_args[1]
        assert call_kwargs["as_type"] == "span"
        assert call_kwargs["name"] == "test-trace"
        assert call_kwargs["input"] == {"file": "test.txt"}

    def test_trace_with_metadata(self, mock_langfuse_client):
        """Test trace() with metadata."""
        tracer = BaseTracer(mock_langfuse_client)
        
        metadata = {"version": "1.0", "env": "test"}
        with tracer.trace("test", metadata=metadata) as span:
            pass
        
        call_kwargs = mock_langfuse_client.start_as_current_observation.call_args[1]
        assert call_kwargs["metadata"] == metadata

    def test_trace_with_user_id(self, mock_langfuse_client):
        """Test trace() with user_id."""
        tracer = BaseTracer(mock_langfuse_client)
        
        with tracer.trace("test", user_id="user123") as span:
            pass
        
        call_kwargs = mock_langfuse_client.start_as_current_observation.call_args[1]
        assert call_kwargs["user_id"] == "user123"

    def test_trace_with_session_id(self, mock_langfuse_client):
        """Test trace() with session_id."""
        tracer = BaseTracer(mock_langfuse_client)
        
        with tracer.trace("test", session_id="session456") as span:
            pass
        
        call_kwargs = mock_langfuse_client.start_as_current_observation.call_args[1]
        assert call_kwargs["session_id"] == "session456"

    def test_trace_with_tags(self, mock_langfuse_client):
        """Test trace() with tags."""
        tracer = BaseTracer(mock_langfuse_client)
        
        tags = ["production", "important"]
        with tracer.trace("test", tags=tags) as span:
            pass
        
        call_kwargs = mock_langfuse_client.start_as_current_observation.call_args[1]
        assert call_kwargs["tags"] == tags

    def test_trace_with_none_client(self):
        """Test trace() with None client yields None."""
        tracer = BaseTracer(None)
        
        with tracer.trace("test") as span:
            assert span is None

    def test_trace_exception_handling(self, mock_langfuse_client):
        """Test trace() exception handling."""
        mock_langfuse_client.start_as_current_observation.side_effect = Exception("Test error")
        tracer = BaseTracer(mock_langfuse_client)
        
        # Should not raise, yields None on exception
        with tracer.trace("test") as span:
            assert span is None

    def test_generation_context_manager(self, mock_langfuse_client):
        """Test generation() context manager."""
        tracer = BaseTracer(mock_langfuse_client)
        
        with tracer.generation("test-gen", model="gemini-2.0-flash",
                              input="prompt text") as gen:
            assert gen is not None
        
        call_kwargs = mock_langfuse_client.start_as_current_observation.call_args[1]
        assert call_kwargs["as_type"] == "generation"
        assert call_kwargs["name"] == "test-gen"
        assert call_kwargs["model"] == "gemini-2.0-flash"
        assert call_kwargs["input"] == "prompt text"

    def test_generation_with_metadata(self, mock_langfuse_client):
        """Test generation() with metadata."""
        tracer = BaseTracer(mock_langfuse_client)
        
        metadata = {"temperature": 0.7}
        with tracer.generation("test", model="gpt-4", metadata=metadata) as gen:
            pass
        
        call_kwargs = mock_langfuse_client.start_as_current_observation.call_args[1]
        assert call_kwargs["metadata"] == metadata

    def test_generation_with_none_client(self):
        """Test generation() with None client yields None."""
        tracer = BaseTracer(None)
        
        with tracer.generation("test", model="gpt-4") as gen:
            assert gen is None

    def test_generation_exception_handling(self, mock_langfuse_client):
        """Test generation() exception handling."""
        mock_langfuse_client.start_as_current_observation.side_effect = Exception("Test error")
        tracer = BaseTracer(mock_langfuse_client)
        
        with tracer.generation("test", model="gpt-4") as gen:
            assert gen is None

    def test_flush(self, mock_langfuse_client):
        """Test flush() method."""
        tracer = BaseTracer(mock_langfuse_client)
        tracer.flush()
        
        mock_langfuse_client.flush.assert_called_once()

    def test_flush_with_none_client(self):
        """Test flush() with None client."""
        tracer = BaseTracer(None)
        # Should not raise
        tracer.flush()

    def test_flush_exception_handling(self, mock_langfuse_client):
        """Test flush() exception handling."""
        mock_langfuse_client.flush.side_effect = Exception("Flush failed")
        tracer = BaseTracer(mock_langfuse_client)
        
        # Should not raise
        tracer.flush()

    def test_extract_usage_not_implemented(self, mock_langfuse_client):
        """Test extract_usage() raises NotImplementedError."""
        tracer = BaseTracer(mock_langfuse_client)
        
        with pytest.raises(NotImplementedError):
            tracer.extract_usage(Mock())

    def test_trace_and_generation_nesting(self, mock_langfuse_client):
        """Test trace() and generation() working together."""
        tracer = BaseTracer(mock_langfuse_client)
        
        with tracer.trace("pipeline") as span:
            with tracer.generation("step1", model="gpt-4") as gen:
                pass
        
        # Both should have been called
        assert mock_langfuse_client.start_as_current_observation.call_count == 2

    def test_generation_user_exception_propagation(self, mock_langfuse_client):
        """Test that exceptions from user code inside generation() propagate correctly."""
        tracer = BaseTracer(mock_langfuse_client)
        
        # This is where the fix is tested: a user exception should NOT causes a RuntimeError
        # in the context manager, but should propagate normally to the caller.
        with pytest.raises(ValueError, match="User error"):
            with tracer.generation("test", model="gpt-4") as gen:
                raise ValueError("User error")
                
        # The internal span should still have been opened
        assert mock_langfuse_client.start_as_current_observation.call_count == 1

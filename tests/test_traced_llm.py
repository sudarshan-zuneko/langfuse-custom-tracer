"""
Unit tests for TracedLLMClient and LLMResponse.
"""

import time
from unittest.mock import Mock, MagicMock, patch
import pytest
from langfuse_custom_tracer.clients.traced_llm import TracedLLMClient, LLMResponse


# ─── LLMResponse tests ──────────────────────────────────────────────


class TestLLMResponse:
    """Test cases for LLMResponse dataclass."""

    def test_basic_creation(self):
        resp = LLMResponse(text="Hello world", model="gemini-2.0-flash", provider="gemini")
        assert resp.text == "Hello world"
        assert resp.model == "gemini-2.0-flash"
        assert resp.provider == "gemini"
        assert resp.usage == {}
        assert resp.latency_ms == 0.0
        assert resp.raw_response is None

    def test_str_returns_text(self):
        resp = LLMResponse(text="Hello")
        assert str(resp) == "Hello"

    def test_repr(self):
        resp = LLMResponse(
            text="Hello world",
            model="gemini-2.0-flash",
            provider="gemini",
            usage={"total": 42},
            latency_ms=123.45,
        )
        r = repr(resp)
        assert "gemini-2.0-flash" in r
        assert "gemini" in r
        assert "42" in r
        assert "123ms" in r

    def test_with_usage(self):
        usage = {"input": 10, "output": 20, "total": 30, "inputCost": 0.001}
        resp = LLMResponse(text="Hi", usage=usage)
        assert resp.usage["total"] == 30
        assert resp.usage["inputCost"] == 0.001

    def test_with_raw_response(self):
        raw = Mock()
        resp = LLMResponse(text="Hi", raw_response=raw)
        assert resp.raw_response is raw


# ─── TracedLLMClient tests ───────────────────────────────────────────


class TestTracedLLMClient:
    """Test cases for TracedLLMClient."""

    def _make_client(self, provider="gemini"):
        """Helper to create a TracedLLMClient with mocks."""
        provider_client = MagicMock()
        tracer = MagicMock()
        
        # Mock trace context manager
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        tracer.trace.return_value = mock_span

        # Mock generation context manager
        mock_gen = MagicMock()
        mock_gen.__enter__ = Mock(return_value=mock_gen)
        mock_gen.__exit__ = Mock(return_value=None)
        tracer.generation.return_value = mock_gen

        tracer.extract_usage.return_value = {
            "input": 10, "output": 20, "total": 30,
            "inputCost": 0.001, "outputCost": 0.002, "totalCost": 0.003,
        }

        return TracedLLMClient(
            provider_client=provider_client,
            tracer=tracer,
            model="test-model",
            provider=provider,
        ), provider_client, tracer, mock_span, mock_gen

    # ─── Gemini tests ────────────────────────────────────────────

    def test_gemini_generate(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        
        mock_response = MagicMock()
        mock_response.text = "Gemini says hello"
        provider.generate_content.return_value = mock_response

        resp = client.generate("Hello")

        assert isinstance(resp, LLMResponse)
        assert resp.text == "Gemini says hello"
        assert resp.provider == "gemini"
        assert resp.model == "test-model"
        assert resp.usage["total"] == 30
        assert resp.latency_ms > 0
        assert resp.raw_response is mock_response
        provider.generate_content.assert_called_once_with("Hello")

    def test_gemini_multimodal(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        
        mock_response = MagicMock()
        mock_response.text = "Image data extracted"
        provider.generate_content.return_value = mock_response

        image_part = {"inline_data": {"mime_type": "image/jpeg", "data": "base64..."}}
        content = [image_part, "Extract data from this image"]

        resp = client.generate(content)
        assert resp.text == "Image data extracted"
        provider.generate_content.assert_called_once_with(content)

    # ─── Anthropic tests ─────────────────────────────────────────

    def test_anthropic_generate(self):
        client, provider, tracer, span, gen = self._make_client("anthropic")

        mock_block = MagicMock()
        mock_block.text = "Claude says hello"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider.messages.create.return_value = mock_response

        resp = client.generate("Hello")

        assert isinstance(resp, LLMResponse)
        assert resp.text == "Claude says hello"
        assert resp.provider == "anthropic"
        provider.messages.create.assert_called_once()

    def test_anthropic_default_max_tokens(self):
        client, provider, tracer, span, gen = self._make_client("anthropic")

        mock_block = MagicMock()
        mock_block.text = "Response"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider.messages.create.return_value = mock_response

        client.generate("Hello")

        call_kwargs = provider.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 8192

    def test_anthropic_custom_max_tokens(self):
        client, provider, tracer, span, gen = self._make_client("anthropic")

        mock_block = MagicMock()
        mock_block.text = "Response"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider.messages.create.return_value = mock_response

        client.generate("Hello", max_tokens=16384)

        call_kwargs = provider.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 16384

    # ─── Tracing tests ───────────────────────────────────────────

    def test_trace_created(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        provider.generate_content.return_value = MagicMock(text="Hi")

        client.generate("Hello", trace_name="my-trace")

        tracer.trace.assert_called_once()
        call_kwargs = tracer.trace.call_args[1]
        assert "my-trace" in tracer.trace.call_args[0]

    def test_generation_span_created(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        provider.generate_content.return_value = MagicMock(text="Hi")

        client.generate("Hello")

        tracer.generation.assert_called_once()

    def test_usage_extracted(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        mock_resp = MagicMock(text="Hi")
        provider.generate_content.return_value = mock_resp

        resp = client.generate("Hello")

        tracer.extract_usage.assert_called_once_with(mock_resp, model="test-model")
        assert resp.usage["total"] == 30

    def test_generation_updated_with_usage_details(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        provider.generate_content.return_value = MagicMock(text="Hi")

        client.generate("Hello")

        gen.update.assert_called_once()
        call_kwargs = gen.update.call_args[1]
        assert "usage_details" in call_kwargs
        assert call_kwargs["usage_details"]["total"] == 30

    # ─── Output truncation ───────────────────────────────────────

    def test_output_truncation(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        long_text = "x" * 5000
        provider.generate_content.return_value = MagicMock(text=long_text)

        resp = client.generate("Hello")

        # Full text returned to caller
        assert len(resp.text) == 5000

        # Truncated text logged to Langfuse
        logged_output = gen.update.call_args[1]["output"]
        assert len(logged_output) <= 2100  # 2000 + truncation message

    def test_short_output_not_truncated(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        provider.generate_content.return_value = MagicMock(text="short")

        client.generate("Hello")

        logged_output = gen.update.call_args[1]["output"]
        assert logged_output == "short"

    # ─── Error handling ──────────────────────────────────────────

    def test_error_logged_and_reraised(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        provider.generate_content.side_effect = RuntimeError("API failed")

        with pytest.raises(RuntimeError, match="API failed"):
            client.generate("Hello")

        # Error should be logged to generation
        gen.update.assert_called_once()
        call_kwargs = gen.update.call_args[1]
        assert call_kwargs["output"] == "error"
        assert "API failed" in call_kwargs["metadata"]["error"]

    # ─── Unknown provider ────────────────────────────────────────

    def test_unknown_provider_raises(self):
        client = TracedLLMClient(
            provider_client=MagicMock(),
            tracer=MagicMock(),
            model="test",
            provider="openai",
        )
        # Mock trace/gen context managers
        client._tracer.trace.return_value.__enter__ = Mock(return_value=MagicMock())
        client._tracer.trace.return_value.__exit__ = Mock(return_value=None)
        client._tracer.generation.return_value.__enter__ = Mock(return_value=MagicMock())
        client._tracer.generation.return_value.__exit__ = Mock(return_value=None)

        with pytest.raises(ValueError, match="Unknown provider"):
            client.generate("Hello")

    # ─── Properties ──────────────────────────────────────────────

    def test_model_property(self):
        client, _, _, _, _ = self._make_client("gemini")
        assert client.model == "test-model"

    def test_provider_property(self):
        client, _, _, _, _ = self._make_client("gemini")
        assert client.provider == "gemini"

    # ─── Input summary ───────────────────────────────────────────

    def test_input_summary_string(self):
        result = TracedLLMClient._summarize_input("Hello world")
        assert result == "Hello world"

    def test_input_summary_long_string(self):
        long_input = "x" * 1000
        result = TracedLLMClient._summarize_input(long_input)
        assert len(result) == 500

    def test_input_summary_image_list(self):
        parts = [
            {"inline_data": {"mime_type": "image/jpeg", "data": "..."}},
            "Extract data",
        ]
        result = TracedLLMClient._summarize_input(parts)
        assert result[0] == "[image: image/jpeg]"
        assert result[1] == "Extract data"

    # ─── Session/user/tags ───────────────────────────────────────

    def test_session_and_user_passed(self):
        client, provider, tracer, span, gen = self._make_client("gemini")
        provider.generate_content.return_value = MagicMock(text="Hi")

        client.generate("Hello", session_id="sess-1", user_id="user-1", tags=["prod"])

        call_kwargs = tracer.trace.call_args[1]
        assert call_kwargs["session_id"] == "sess-1"
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["tags"] == ["prod"]

"""
Unit tests for create_traced_client factory.
"""

from unittest.mock import patch, MagicMock, Mock
import pytest
from langfuse_custom_tracer.factory import create_traced_client
from langfuse_custom_tracer.clients.traced_llm import TracedLLMClient


class TestCreateTracedClient:
    """Test cases for the create_traced_client factory."""

    @patch("langfuse_custom_tracer.factory._init_gemini")
    def test_gemini_provider(self, mock_init):
        mock_model = MagicMock()
        mock_init.return_value = mock_model
        tracer = MagicMock()

        client = create_traced_client(
            provider="gemini",
            api_key="test-key",
            tracer=tracer,
            model="gemini-2.0-flash",
        )

        assert isinstance(client, TracedLLMClient)
        assert client.provider == "gemini"
        assert client.model == "gemini-2.0-flash"
        mock_init.assert_called_once_with("test-key", "gemini-2.0-flash")

    @patch("langfuse_custom_tracer.factory._init_anthropic")
    def test_anthropic_provider(self, mock_init):
        mock_client = MagicMock()
        mock_init.return_value = mock_client
        tracer = MagicMock()

        client = create_traced_client(
            provider="anthropic",
            api_key="test-key",
            tracer=tracer,
            model="claude-3-5-sonnet-20241022",
        )

        assert isinstance(client, TracedLLMClient)
        assert client.provider == "anthropic"
        assert client.model == "claude-3-5-sonnet-20241022"
        mock_init.assert_called_once_with("test-key")

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_traced_client(
                provider="openai",
                api_key="test-key",
                tracer=MagicMock(),
                model="gpt-4",
            )

    @patch("langfuse_custom_tracer.factory._init_gemini")
    def test_case_insensitive_provider(self, mock_init):
        mock_init.return_value = MagicMock()

        client = create_traced_client(
            provider="GEMINI",
            api_key="test-key",
            tracer=MagicMock(),
            model="gemini-2.0-flash",
        )

        assert client.provider == "gemini"

    @patch("langfuse_custom_tracer.factory._init_anthropic")
    def test_custom_max_tokens(self, mock_init):
        mock_init.return_value = MagicMock()

        client = create_traced_client(
            provider="anthropic",
            api_key="test-key",
            tracer=MagicMock(),
            model="claude-3-5-sonnet-20241022",
            default_max_tokens=16384,
        )

        assert client._default_max_tokens == 16384


class TestInitGemini:
    """Test lazy Gemini initialization."""

    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_init_gemini(self, mock_model_cls, mock_configure):
        from langfuse_custom_tracer.factory import _init_gemini

        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        result = _init_gemini("test-key", "gemini-2.0-flash")

        mock_configure.assert_called_once_with(api_key="test-key")
        mock_model_cls.assert_called_once_with("gemini-2.0-flash")
        assert result is mock_model


class TestInitAnthropic:
    """Test lazy Anthropic initialization."""

    @patch("anthropic.Anthropic")
    def test_init_anthropic(self, mock_anthropic_cls):
        from langfuse_custom_tracer.factory import _init_anthropic

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        result = _init_anthropic("test-key")

        mock_anthropic_cls.assert_called_once_with(api_key="test-key")
        assert result is mock_client

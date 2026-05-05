"""
Pytest configuration and shared fixtures.
"""

import os
from unittest.mock import Mock, MagicMock
import pytest

@pytest.fixture(autouse=True)
def mock_requests_get():
    from unittest.mock import patch # Move import here
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": {
                "claude-3-5-haiku": {"cache_read": 0.08, "cache_write": 1, "input": 0.8, "output": 4},
                "claude-3-5-sonnet": {"cache_read": 0.3, "cache_write": 3.75, "input": 3, "output": 15},
                "claude-3-haiku": {"cache_read": 0.08, "cache_write": 1, "input": 0.8, "output": 4},
                "claude-3-opus": {"cache_read": 1.5, "cache_write": 18.75, "input": 15, "output": 75},
                "claude-3-sonnet": {"cache_read": 0.3, "cache_write": 3.75, "input": 3, "output": 15},
                "claude-4-5-haiku": {"cache_read": 0.1, "cache_write": 1.25, "input": 1, "output": 5},
                "claude-4-6-opus": {"cache_read": 0.5, "cache_write": 6.25, "input": 5, "output": 25},
                "claude-4-6-sonnet": {"cache_read": 0.3, "cache_write": 3.75, "input": 3, "output": 15},
                "gemini-1.5-flash": {"cached": 0.01875, "input": 0.075, "output": 0.3},
                "gemini-1.5-flash-8b": {"cached": 0.01, "input": 0.0375, "output": 0.15},
                "gemini-1.5-pro": {"cached": 0.3125, "input": 1.25, "output": 5},
                "gemini-2.0-flash": {"cached": 0.0375, "input": 0.15, "output": 0.6},
                "gemini-2.0-flash-lite": {"cached": 0.01875, "input": 0.075, "output": 0.3},
                "gemini-2.5-flash": {"cached": 0.075, "input": 0.3, "output": 2.5},
                "gemini-2.5-flash-lite": {"cached": 0.025, "input": 0.1, "output": 0.4},
                "gemini-2.5-pro": {"cached": 0.3125, "input": 1.25, "output": 10},
                "gpt-4-turbo": {"input": 10, "output": 30},
                "gpt-4o": {"input": 5, "output": 15},
                "gpt-4o-mini": {"input": 0.15, "output": 0.6}
            },
            "version": "2026-04-29-v1"
        }
        mock_get.return_value = mock_response
        yield mock_get

@pytest.fixture(autouse=True)
def initialize_pricing_manager(mock_requests_get):
    from langfuse_custom_tracer.pricing_manager import get_pricing_manager, reset_pricing_manager
    reset_pricing_manager()
    pm = get_pricing_manager()
    pm._fetch_remote()
    yield

@pytest.fixture
def mock_langfuse_client(mock_requests_get): # Inject the mock_requests_get fixture
    """Create a mock Langfuse v4 client for testing."""
    client = MagicMock()
    
    # Mock observation context manager
    mock_observation = MagicMock()
    mock_observation.__enter__ = Mock(return_value=mock_observation)
    mock_observation.__exit__ = Mock(return_value=None)
    mock_observation.update = Mock()
    
    client.start_as_current_observation = Mock(return_value=mock_observation)
    client.flush = Mock()
    
    return client


@pytest.fixture
def gemini_response_with_usage():
    """Create a mock Gemini response with usage metadata."""
    response = MagicMock()
    
    # Mock usage_metadata
    usage_metadata = MagicMock()
    usage_metadata.prompt_token_count = 100
    usage_metadata.candidates_token_count = 50
    usage_metadata.total_token_count = 150
    usage_metadata.cached_content_token_count = 10
    
    response.usage_metadata = usage_metadata
    response.text = "This is a test response"
    
    return response


@pytest.fixture
def gemini_response_without_usage():
    """Create a mock Gemini response without usage metadata."""
    response = MagicMock()
    response.usage_metadata = None
    response.text = "This is a test response"
    
    return response


@pytest.fixture
def env_file(tmp_path):
    """Create a temporary .env file for testing."""
    env_path = tmp_path / ".env"
    env_content = """
LANGFUSE_SECRET_KEY=""
LANGFUSE_PUBLIC_KEY=""
LANGFUSE_BASE_URL="https://cloud.langfuse.com"
GEMINI_API_KEY=
"""
    env_path.write_text(env_content)
    return env_path


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before and after each test."""
    # Store original env
    original_env = os.environ.copy()
    
    # Clean ALL Langfuse and LLM-related env vars (be more aggressive)
    keys_to_remove = [
        key for key in os.environ.keys()
        if any(prefix in key for prefix in [
            "LANGFUSE_", "GEMINI_", "GROQ_", "OLLAMA_", 
            "ANTHROPIC_", "AZURE_", "OPENAI_"
        ])
    ]
    
    for key in keys_to_remove:
        del os.environ[key]
    
    yield
    
    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)

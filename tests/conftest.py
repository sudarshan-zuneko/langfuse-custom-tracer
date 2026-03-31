"""
Pytest configuration and shared fixtures.
"""

import os
from unittest.mock import Mock, MagicMock
import pytest


@pytest.fixture
def mock_langfuse_client():
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

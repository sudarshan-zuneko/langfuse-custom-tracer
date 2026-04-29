"""
Unit tests for client setup functions.
"""

import os
from unittest.mock import patch, Mock
import pytest
from langfuse_custom_tracer.client import create_langfuse_client, load_env


class TestCreateLangfuseClient:
    """Test cases for create_langfuse_client function."""

    @patch("langfuse.get_client")
    def test_basic_client_creation(self, mock_get_client):
        """Test basic client creation with credentials."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        lf = create_langfuse_client(
            secret_key="sk-lf-test-secret",
            public_key="pk-lf-test-public"
        )
        
        assert lf == mock_client
        assert os.environ["LANGFUSE_SECRET_KEY"] == "sk-lf-test-secret"
        assert os.environ["LANGFUSE_PUBLIC_KEY"] == "pk-lf-test-public"
        assert os.environ["LANGFUSE_BASE_URL"] == "https://cloud.langfuse.com"

    @patch("langfuse.get_client")
    def test_custom_host(self, mock_get_client):
        """Test client creation with custom host."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        lf = create_langfuse_client(
            secret_key="sk-lf-test",
            public_key="pk-lf-test",
            host="https://us.cloud.langfuse.com"
        )
        
        assert os.environ["LANGFUSE_BASE_URL"] == "https://us.cloud.langfuse.com"

    @patch("langfuse.get_client")
    def test_env_variables_set(self, mock_get_client):
        """Test that environment variables are properly set."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        create_langfuse_client(
            secret_key="sk-lf-secret123",
            public_key="pk-lf-public456"
        )
        
        # Variables should be set in environment
        assert os.environ.get("LANGFUSE_SECRET_KEY") == "sk-lf-secret123"
        assert os.environ.get("LANGFUSE_PUBLIC_KEY") == "pk-lf-public456"

    @patch("langfuse.get_client")
    def test_get_client_called(self, mock_get_client):
        """Test that get_client() is called to return singleton."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        lf = create_langfuse_client(
            secret_key="sk-lf-test",
            public_key="pk-lf-test"
        )
        
        mock_get_client.assert_called_once()
        assert lf == mock_client

    @patch("langfuse.get_client", side_effect=ImportError("No module named langfuse"))
    def test_missing_langfuse_import(self, mock_get_client):
        """Test ImportError when langfuse is not installed."""
        with pytest.raises(ImportError, match="langfuse"):
            create_langfuse_client("sk-lf-test", "pk-lf-test")

    @patch("langfuse.get_client")
    def test_overrides_existing_env_vars(self, mock_get_client):
        """Test that function overrides existing environment variables."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        os.environ["LANGFUSE_SECRET_KEY"] = "sk-old"
        os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-old"
        
        create_langfuse_client(
            secret_key="sk-new",
            public_key="pk-new"
        )
        
        assert os.environ["LANGFUSE_SECRET_KEY"] == "sk-new"
        assert os.environ["LANGFUSE_PUBLIC_KEY"] == "pk-new"

    @patch("langfuse.get_client")
    def test_docstring_example(self, mock_get_client):
        """Test example from docstring works."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # This should match the docstring example
        lf = create_langfuse_client("sk-lf-...", "pk-lf-...")
        assert lf == mock_client


class TestLoadEnv:
    """Test cases for load_env function."""

    def test_load_env_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file does not raise."""
        nonexistent_path = tmp_path / "nonexistent.env"
        
        # load_dotenv should not raise, just silently ignore
        load_env(nonexistent_path)

    @patch("dotenv.load_dotenv")
    def test_load_env_calls_load_dotenv(self, mock_load_dotenv, env_file):
        """Test that load_env calls load_dotenv with correct file."""
        load_env(env_file)
        
        mock_load_dotenv.assert_called_once()
        # Check the file path was passed
        call_args = mock_load_dotenv.call_args[0]
        assert str(call_args[0]).endswith(".env")

    def test_load_env_with_custom_env_file(self, tmp_path):
        """Test load_env loads values into os.environ."""
        custom_env = tmp_path / ".env.custom"
        custom_env.write_text("TEST_VAR=custom_value\nANOTHER=test")
        
        load_env(custom_env)
        
        # Should have loaded the custom values
        assert os.environ.get("TEST_VAR") == "custom_value"
        assert os.environ.get("ANOTHER") == "test"


class TestEnvironmentIntegration:
    """Test integration between client setup and environment variables."""

    @patch("langfuse.get_client")
    def test_client_uses_env_vars(self, mock_get_client):
        """Test that create_langfuse_client uses environment variables."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Set environment variables
        test_secret = "sk-lf-integration-test-secret"
        test_public = "pk-lf-integration-test-public"
        
        create_langfuse_client(test_secret, test_public)
        
        # Verify environment variables were set
        assert os.environ["LANGFUSE_SECRET_KEY"] == test_secret
        assert os.environ["LANGFUSE_PUBLIC_KEY"] == test_public
        # Verify get_client was called
        mock_get_client.assert_called_once()

    @patch("langfuse.get_client")
    def test_env_vars_persist_after_create_client(self, mock_get_client):
        """Test that env vars persist after creating client."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        create_langfuse_client("sk-integration", "pk-integration")
        
        # Variables should still be set
        assert os.environ["LANGFUSE_SECRET_KEY"] == "sk-integration"
        assert os.environ["LANGFUSE_PUBLIC_KEY"] == "pk-integration"

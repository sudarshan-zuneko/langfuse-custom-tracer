"""
Langfuse v4 client setup.

In v4, credentials are set via environment variables and the client is
obtained via get_client() — a singleton that reads the env vars once.
"""

import os
from pathlib import Path
from typing import Any


def create_langfuse_client(
    secret_key: str,
    public_key: str,
    host: str = "https://cloud.langfuse.com",
) -> Any:
    """Configure Langfuse credentials and return the v4 singleton client.

    In Langfuse v4 the recommended pattern is environment variables +
    ``get_client()``. This helper sets those variables for you so callers
    don't need to touch ``os.environ`` manually.

    Args:
        secret_key: Your Langfuse secret key  (starts with ``sk-lf-...``).
        public_key: Your Langfuse public key  (starts with ``pk-lf-...``).
        host:       Langfuse server URL.  Defaults to EU cloud.
                    US cloud: ``https://us.cloud.langfuse.com``

    Returns:
        The initialised ``Langfuse`` v4 singleton client.

    Raises:
        ImportError: If ``langfuse`` ≥ 3.0 is not installed.

    Example::

        from langfuse_custom_tracer import create_langfuse_client, GeminiTracer

        lf     = create_langfuse_client("sk-lf-...", "pk-lf-...")
        tracer = GeminiTracer(lf)
    """
    try:
        from langfuse import get_client  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "langfuse >= 3.0 is required. Install it with:\n"
            "  pip install 'langfuse>=3.0'"
        ) from exc

    os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
    os.environ.setdefault("LANGFUSE_BASE_URL",   host)

    # Override even if already set — caller is explicit
    os.environ["LANGFUSE_SECRET_KEY"] = secret_key
    os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
    os.environ["LANGFUSE_BASE_URL"]   = host

    return get_client()


def load_env(env_file: str | Path = ".env") -> None:
    """Load environment variables from a .env file.

    Uses python-dotenv to load environment variables. Call this before
    ``create_langfuse_client()`` if loading credentials from a .env file.

    Args:
        env_file: Path to the .env file. Defaults to ``.env`` in the
                  current working directory.

    Raises:
        ImportError: If ``python-dotenv`` is not installed.

    Example::

        from langfuse_custom_tracer import load_env, create_langfuse_client

        load_env()  # Loads from .env
        lf = create_langfuse_client(
            os.getenv("LANGFUSE_SECRET_KEY"),
            os.getenv("LANGFUSE_PUBLIC_KEY"),
        )
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "python-dotenv is required for load_env(). Install it with:\n"
            "  pip install python-dotenv"
        ) from exc

    load_dotenv(env_file)
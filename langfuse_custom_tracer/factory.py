"""
Factory for creating traced LLM clients.

Provides a one-liner setup for automatic LLM tracing::

    from langfuse_custom_tracer import (
        create_langfuse_client, create_traced_client, GeminiTracer,
    )

    lf  = create_langfuse_client(secret_key, public_key)
    llm = create_traced_client(
        provider="gemini",
        api_key="...",
        tracer=GeminiTracer(lf),
        model="gemini-2.0-flash",
    )

    response = llm.generate("Explain quantum computing")
    print(response.text)
    print(response.usage)
"""

from __future__ import annotations

from typing import Any

from langfuse_custom_tracer.clients.traced_llm import TracedLLMClient


def create_traced_client(
    provider: str,
    api_key: str,
    tracer: Any,
    model: str,
    *,
    default_max_tokens: int = 8192,
    **provider_kwargs: Any,
) -> TracedLLMClient:
    """Create a traced LLM client with automatic observability.

    Initializes the provider SDK, wraps it with ``TracedLLMClient``,
    and returns a unified interface. Provider SDKs are lazily imported
    so users only need the SDK for their chosen provider.

    Args:
        provider:           ``"gemini"`` or ``"anthropic"``.
        api_key:            API key for the provider.
        tracer:             A tracer instance (``GeminiTracer`` or ``AnthropicTracer``).
        model:              Model name (e.g. ``"gemini-2.0-flash"``).
        default_max_tokens: Default max tokens for Anthropic calls.
                            Defaults to 8192 (suitable for large bank
                            statement / document processing).
        **provider_kwargs:  Extra kwargs passed to the provider SDK init.

    Returns:
        A ``TracedLLMClient`` ready for use.

    Raises:
        ValueError:  If ``provider`` is not ``"gemini"`` or ``"anthropic"``.
        ImportError: If the required provider SDK is not installed.

    Example — Gemini::

        llm = create_traced_client(
            provider="gemini",
            api_key=os.getenv("GEMINI_API_KEY"),
            tracer=GeminiTracer(lf),
            model="gemini-2.0-flash",
        )
        resp = llm.generate("Hello!")

    Example — Anthropic::

        llm = create_traced_client(
            provider="anthropic",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            tracer=AnthropicTracer(lf),
            model="claude-3-5-sonnet-20241022",
        )
        resp = llm.generate("Hello!")
    """
    provider_lower = provider.lower()

    if provider_lower == "gemini":
        client = _init_gemini(api_key, model, **provider_kwargs)
    elif provider_lower == "anthropic":
        client = _init_anthropic(api_key, **provider_kwargs)
    else:
        raise ValueError(
            f"Unknown provider: {provider!r}. "
            f"Supported providers: 'gemini', 'anthropic'"
        )

    return TracedLLMClient(
        provider_client=client,
        tracer=tracer,
        model=model,
        provider=provider_lower,
        default_max_tokens=default_max_tokens,
    )


def _init_gemini(api_key: str, model: str, **kwargs: Any) -> Any:
    """Initialize a Gemini GenerativeModel."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "google-generativeai is required for Gemini support. "
            "Install it with:\n  pip install 'langfuse-custom-tracer[gemini]'"
        ) from exc

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model, **kwargs)


def _init_anthropic(api_key: str, **kwargs: Any) -> Any:
    """Initialize an Anthropic client."""
    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "anthropic is required for Anthropic support. "
            "Install it with:\n  pip install 'langfuse-custom-tracer[anthropic]'"
        ) from exc

    return anthropic.Anthropic(api_key=api_key, **kwargs)

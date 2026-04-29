"""
TracedLLMClient — automatic LLM tracing with zero boilerplate.

Wraps any LLM provider SDK and automatically creates Langfuse traces
with usage extraction, cost tracking, and error logging.

Supports:
  - Google Gemini (google-generativeai)
  - Anthropic Claude (anthropic)

Example::

    from langfuse_custom_tracer import create_traced_client, GeminiTracer

    llm = create_traced_client(
        provider="gemini",
        api_key="...",
        tracer=GeminiTracer(lf),
        model="gemini-2.0-flash",
    )

    response = llm.generate("Extract data from this invoice")
    print(response.text)
    print(response.usage)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


# ─── Output truncation limit for Langfuse logging ───────────────────
MAX_LOG_OUTPUT = 2000


@dataclass
class LLMResponse:
    """Standardized response wrapper returned by TracedLLMClient.

    Attributes:
        text:         The generated text content.
        usage:        Token usage dict (input, output, total, costs).
        model:        Model name that produced this response.
        provider:     Provider identifier ("gemini" or "anthropic").
        latency_ms:   Wall-clock time of the API call in milliseconds.
        raw_response: The original SDK response object for power users.
    """

    text: str
    usage: dict = field(default_factory=dict)
    model: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    raw_response: Any = None

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return (
            f"LLMResponse(model={self.model!r}, provider={self.provider!r}, "
            f"tokens={self.usage.get('total', '?')}, "
            f"latency={self.latency_ms:.0f}ms, "
            f"text={self.text[:80]!r}{'...' if len(self.text) > 80 else ''})"
        )


class TracedLLMClient:
    """Automatically traced LLM client.

    Wraps a provider SDK client and adds Langfuse tracing to every call.
    Each ``generate()`` / ``agenerate()`` call creates:

    1. A root trace (span)
    2. A nested generation span with model, input, output, and usage

    Args:
        provider_client: The initialized provider SDK client.
                         - Gemini: ``genai.GenerativeModel`` instance
                         - Anthropic: ``anthropic.Anthropic`` instance
        tracer:          A ``BaseTracer`` subclass (GeminiTracer / AnthropicTracer).
        model:           Model name (e.g. ``"gemini-2.0-flash"``).
        provider:        Provider identifier (``"gemini"`` or ``"anthropic"``).
        default_max_tokens: Default max tokens for Anthropic calls. Defaults to
                            8192 (suitable for large bank statement processing).

    Example::

        llm = TracedLLMClient(
            provider_client=model,
            tracer=GeminiTracer(lf),
            model="gemini-2.0-flash",
            provider="gemini",
        )

        # Simple text prompt
        resp = llm.generate("Summarize this document")

        # With images / multimodal content
        resp = llm.generate([image_part, "Extract all data from this image"])
    """

    def __init__(
        self,
        provider_client: Any,
        tracer: Any,
        model: str,
        provider: str,
        *,
        default_max_tokens: int = 8192,
    ) -> None:
        self._client = provider_client
        self._tracer = tracer
        self._model = model
        self._provider = provider.lower()
        self._default_max_tokens = default_max_tokens

    # ─── Provider dispatch ───────────────────────────────────────────

    def _call_gemini(self, prompt: Any, **kwargs: Any) -> tuple[Any, str]:
        """Call Gemini SDK and return (raw_response, text)."""
        response = self._client.generate_content(prompt, **kwargs)
        text = response.text or ""
        return response, text

    def _call_anthropic(self, prompt: Any, **kwargs: Any) -> tuple[Any, str]:
        """Call Anthropic SDK and return (raw_response, text)."""
        # Build messages from prompt
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            # Support pre-built message lists
            if prompt and isinstance(prompt[0], dict) and "role" in prompt[0]:
                messages = prompt
            else:
                # Treat as multimodal content parts
                messages = [{"role": "user", "content": prompt}]
        else:
            messages = [{"role": "user", "content": str(prompt)}]

        # Apply default max_tokens if not overridden
        if "max_tokens" not in kwargs:
            kwargs["max_tokens"] = self._default_max_tokens

        response = self._client.messages.create(
            model=self._model,
            messages=messages,
            **kwargs,
        )

        # Extract text from content blocks
        text = ""
        if hasattr(response, "content") and response.content:
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
            text = "\n".join(text_parts)

        return response, text

    def _dispatch(self, prompt: Any, **kwargs: Any) -> tuple[Any, str]:
        """Route to the correct provider."""
        if self._provider == "gemini":
            return self._call_gemini(prompt, **kwargs)
        elif self._provider == "anthropic":
            return self._call_anthropic(prompt, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {self._provider!r}")

    # ─── Truncation ──────────────────────────────────────────────────

    @staticmethod
    def _truncate(text: str, limit: int = MAX_LOG_OUTPUT) -> str:
        """Truncate text for Langfuse logging (never log full responses)."""
        if len(text) <= limit:
            return text
        return text[:limit] + f"... [truncated, {len(text)} total chars]"

    # ─── Input summary for logging ───────────────────────────────────

    @staticmethod
    def _summarize_input(prompt: Any) -> Any:
        """Create a loggable summary of the input prompt."""
        if isinstance(prompt, str):
            return prompt[:500] if len(prompt) > 500 else prompt
        if isinstance(prompt, list):
            summary = []
            for item in prompt:
                if isinstance(item, str):
                    summary.append(item[:200] if len(item) > 200 else item)
                elif isinstance(item, dict):
                    if "inline_data" in item:
                        mime = item.get("inline_data", {}).get("mime_type", "unknown")
                        summary.append(f"[image: {mime}]")
                    elif "role" in item:
                        summary.append(item)
                    else:
                        summary.append("[binary content]")
                else:
                    summary.append(f"[{type(item).__name__}]")
            return summary
        return str(prompt)[:500]

    # ─── Sync generate ───────────────────────────────────────────────

    def generate(
        self,
        prompt: Any,
        *,
        trace_name: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response with automatic Langfuse tracing.

        Args:
            prompt:      Text string, list of content parts (multimodal),
                         or pre-built message list.
            trace_name:  Custom trace name. Defaults to ``"{provider}-call"``.
            session_id:  Langfuse session ID for grouping traces.
            user_id:     Langfuse user ID.
            tags:        Tags for filtering in Langfuse dashboard.
            metadata:    Extra metadata dict.
            **kwargs:    Passed through to the provider SDK call.

        Returns:
            ``LLMResponse`` with text, usage, latency, and raw response.

        Raises:
            Exception: Any provider API error is logged to Langfuse
                       and then re-raised.
        """
        _trace_name = trace_name or f"{self._provider}-call"
        _gen_name = f"{self._provider}-generation"
        input_summary = self._summarize_input(prompt)

        # Fallback to context-based tracking if not explicitly provided
        from langfuse_custom_tracer.context import get_user, get_session, _set_trace_id
        
        _user_id = user_id or get_user()
        _session_id = session_id or get_session()

        with self._tracer.trace(
            _trace_name,
            input={"prompt": input_summary, "model": self._model},
            session_id=_session_id,
            user_id=_user_id,
            tags=tags,
            metadata=metadata,
        ) as span:
            if span:
                _set_trace_id(span.id)
                
            with self._tracer.generation(
                _gen_name,
                model=self._model,
                input=input_summary,
                metadata={"provider": self._provider},
            ) as gen:
                start = time.perf_counter()
                try:
                    raw_response, text = self._dispatch(prompt, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000

                    usage = self._tracer.extract_usage(
                        raw_response, model=self._model
                    )
                    
                    # Extract pricing metadata
                    pricing_source = usage.pop("_pricing_source", "unknown")
                    pricing_version = usage.pop("_pricing_version", "unknown")

                    if gen:
                        gen.update(
                            output=self._truncate(text),
                            usage_details=usage,
                            metadata={
                                "provider": self._provider,
                                "latency_ms": round(elapsed_ms, 2),
                                "pricing_source": pricing_source,
                                "pricing_version": pricing_version,
                            },
                        )

                    if span:
                        span.update(output="completed")

                    return LLMResponse(
                        text=text,
                        usage=usage,
                        model=self._model,
                        provider=self._provider,
                        latency_ms=round(elapsed_ms, 2),
                        raw_response=raw_response,
                    )

                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    if gen:
                        gen.update(
                            output="error",
                            metadata={
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "provider": self._provider,
                                "latency_ms": round(elapsed_ms, 2),
                            },
                        )
                    if span:
                        span.update(
                            output="error",
                            metadata={"error": str(e)},
                        )
                    raise

    # ─── Async generate ──────────────────────────────────────────────

    async def agenerate(
        self,
        prompt: Any,
        *,
        trace_name: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Async version of ``generate()``.

        Wraps the sync provider SDK call in ``asyncio.to_thread()``
        so it doesn't block the event loop. Safe for use with
        ``asyncio.gather()`` for parallel execution.

        Each call creates its own independent trace.
        """
        return await asyncio.to_thread(
            self.generate,
            prompt,
            trace_name=trace_name,
            session_id=session_id,
            user_id=user_id,
            tags=tags,
            metadata=metadata,
            **kwargs,
        )

    # ─── Properties ──────────────────────────────────────────────────

    @property
    def model(self) -> str:
        """The model name this client is configured for."""
        return self._model

    @property
    def provider(self) -> str:
        """The provider identifier."""
        return self._provider

    def flush(self) -> None:
        """Flush pending Langfuse events."""
        self._tracer.flush()

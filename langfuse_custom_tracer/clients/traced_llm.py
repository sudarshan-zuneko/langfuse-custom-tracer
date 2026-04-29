from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any
from ..context import get_user, get_session, _set_trace_id

MAX_LOG_OUTPUT = 2000

@dataclass
class LLMResponse:
    text: str
    usage: dict = field(default_factory=dict)
    model: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    raw_response: Any = None

    def __str__(self) -> str: return self.text

class TracedLLMClient:
    def __init__(self, provider_client, tracer, model, provider, *, default_max_tokens=8192):
        self._client = provider_client
        self._tracer = tracer
        self._model = model
        self._provider = provider.lower()
        self._default_max_tokens = default_max_tokens

    def _dispatch(self, prompt, **kwargs):
        if self._provider == "gemini":
            res = self._client.generate_content(prompt, **kwargs)
            return res, getattr(res, "text", "")
        elif self._provider == "anthropic":
            res = self._client.messages.create(model=self._model, messages=[{"role": "user", "content": prompt}], max_tokens=self._default_max_tokens, **kwargs)
            text = "".join(b.text for b in res.content if hasattr(b, "text"))
            return res, text
        raise ValueError(f"Unknown provider: {self._provider}")

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
                    if gen: gen.update(output="error", metadata={"error": str(e)})
                    raise

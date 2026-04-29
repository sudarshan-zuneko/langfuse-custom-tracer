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

    def generate(self, prompt, *, trace_name=None, session_id=None, user_id=None, tags=None, metadata=None, **kwargs):
        _user_id = user_id or get_user()
        _session_id = session_id or get_session()

        with self._tracer.trace(trace_name or f"{self._provider}-call", session_id=_session_id, user_id=_user_id, tags=tags, metadata=metadata) as span:
            if span: _set_trace_id(span.id)
            with self._tracer.generation(f"{self._provider}-gen", model=self._model, input=str(prompt)) as gen:
                start = time.perf_counter()
                try:
                    raw, text = self._dispatch(prompt, **kwargs)
                    ms = (time.perf_counter() - start) * 1000
                    usage = self._tracer.extract_usage(raw, self._model)
                    pricing_source = usage.pop("_pricing_source", "unknown")
                    pricing_version = usage.pop("_pricing_version", "unknown")
                    if gen:
                        gen.update(output=text[:MAX_LOG_OUTPUT], usage_details=usage, metadata={"latency_ms": round(ms, 2), "pricing_source": pricing_source, "pricing_version": pricing_version})
                    return LLMResponse(text=text, usage=usage, model=self._model, provider=self._provider, latency_ms=round(ms, 2), raw_response=raw)
                except Exception as e:
                    if gen: gen.update(output="error", metadata={"error": str(e)})
                    raise

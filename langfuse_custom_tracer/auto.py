import os
import time
import wrapt
import warnings
import asyncio
from typing import Any, Dict, List, Optional, Callable
from langfuse import get_client

from .context import get_user, get_session, _set_trace_id
from .tracers.gemini import GeminiTracer
from .tracers.anthropic import AnthropicTracer

# Global Langfuse client for auto-tracing
_client = None
_already_patched = set()

def _get_langfuse():
    global _client
    if _client is None:
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        if not secret_key or not public_key:
            warnings.warn("langfuse-custom-tracer: Credentials not found. Auto-tracing disabled.")
            return None
        _client = get_client()
    return _client

def _build_wrapper(provider: str, tracer_cls: type):
    def wrapper(wrapped, instance, args, kwargs):
        client = _get_langfuse()
        if client is None:
            return wrapped(*args, **kwargs)

        user_id = get_user()
        session_id = get_session()
        
        # Determine model name from instance or args
        model = getattr(instance, "model_name", "unknown")
        if provider == "anthropic" and "model" in kwargs:
            model = kwargs["model"]
        elif provider == "gemini" and hasattr(instance, "model_name"):
            model = instance.model_name

        trace = client.trace(
            name=f"{provider}-auto-trace",
            user_id=user_id,
            session_id=session_id,
            input={"args": str(args), "kwargs": str(kwargs)}
        )
        _set_trace_id(trace.id)
        
        tracer = tracer_cls(client)
        
        # We start a generation but we don't have the response yet
        # Langfuse v4 start_as_current_observation handles nesting
        with client.start_as_current_observation(
            as_type="generation",
            name=f"{provider}-generation",
            model=model,
            input=str(args[0]) if args else str(kwargs.get("messages", kwargs.get("contents", ""))),
            metadata={"auto_traced": True, "provider": provider}
        ) as gen:
            start_time = time.perf_counter()
            try:
                result = wrapped(*args, **kwargs)
                latency = (time.perf_counter() - start_time) * 1000
                
                usage = tracer.extract_usage(result, model=model)
                
                # Extract pricing metadata if present
                pricing_meta = {
                    "latency_ms": round(latency, 2),
                    "pricing_source": usage.pop("_pricing_source", "unknown"),
                    "pricing_version": usage.pop("_pricing_version", "unknown")
                }
                
                gen.update(
                    output=str(result),
                    usage_details=usage,
                    metadata=pricing_meta
                )
                trace.update(output="SUCCESS")
                return result
            except Exception as e:
                gen.update(status_message=str(e), metadata={"error": True})
                trace.update(output=f"ERROR: {str(e)}")
                raise
    return wrapper

def _build_async_wrapper(provider: str, tracer_cls: type):
    async def wrapper(wrapped, instance, args, kwargs):
        client = _get_langfuse()
        if client is None:
            return await wrapped(*args, **kwargs)

        user_id = get_user()
        session_id = get_session()
        
        model = "unknown"
        if provider == "anthropic" and "model" in kwargs:
            model = kwargs["model"]
        elif provider == "gemini" and hasattr(instance, "model_name"):
            model = instance.model_name

        trace = client.trace(
            name=f"{provider}-auto-trace-async",
            user_id=user_id,
            session_id=session_id
        )
        _set_trace_id(trace.id)
        
        tracer = tracer_cls(client)
        
        with client.start_as_current_observation(
            as_type="generation",
            name=f"{provider}-generation-async",
            model=model,
            metadata={"auto_traced": True, "provider": provider}
        ) as gen:
            start_time = time.perf_counter()
            try:
                result = await wrapped(*args, **kwargs)
                latency = (time.perf_counter() - start_time) * 1000
                
                usage = tracer.extract_usage(result, model=model)
                pricing_meta = {
                    "latency_ms": round(latency, 2),
                    "pricing_source": usage.pop("_pricing_source", "unknown"),
                    "pricing_version": usage.pop("_pricing_version", "unknown")
                }
                
                gen.update(
                    output=str(result),
                    usage_details=usage,
                    metadata=pricing_meta
                )
                trace.update(output="SUCCESS")
                return result
            except Exception as e:
                gen.update(status_message=str(e), metadata={"error": True})
                trace.update(output=f"ERROR: {str(e)}")
                raise
    return wrapper

def observe():
    """Enable automatic tracing by patching LLM SDKs."""
    # Patch Gemini
    try:
        import google.generativeai as genai
        if "gemini" not in _already_patched:
            wrapt.wrap_function_wrapper(
                "google.generativeai.generative_models", 
                "GenerativeModel.generate_content", 
                _build_wrapper("gemini", GeminiTracer)
            )
            wrapt.wrap_function_wrapper(
                "google.generativeai.generative_models", 
                "GenerativeModel.generate_content_async", 
                _build_async_wrapper("gemini", GeminiTracer)
            )
            _already_patched.add("gemini")
    except ImportError:
        pass

    # Patch Anthropic
    try:
        import anthropic
        if "anthropic" not in _already_patched:
            # Note: In newer anthropic SDK, it's resources.messages.Messages.create
            wrapt.wrap_function_wrapper(
                "anthropic.resources.messages", 
                "Messages.create", 
                _build_wrapper("anthropic", AnthropicTracer)
            )
            # Async variant
            wrapt.wrap_function_wrapper(
                "anthropic.resources.messages", 
                "AsyncMessages.create", 
                _build_async_wrapper("anthropic", AnthropicTracer)
            )
            _already_patched.add("anthropic")
    except ImportError:
        pass

def unpatch():
    """Restore original SDK methods. (Mainly for testing)"""
    # Note: wrapt doesn't provide a simple global unpatch easily if we used wrap_function_wrapper
    # but we can implement it by keeping track of original methods if needed.
    # For now, we'll leave it as is or advise process restart for tests.
    pass

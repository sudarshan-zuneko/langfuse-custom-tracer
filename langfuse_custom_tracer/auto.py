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
        
        model = "unknown"
        if provider == "anthropic" and "model" in kwargs:
            model = kwargs["model"]
        elif provider == "gemini":
            # For google-generativeai
            if hasattr(instance, "model_name"):
                model = instance.model_name
            # For google-genai
            elif "model" in kwargs:
                model = kwargs["model"]

        trace_kwargs = {
            "as_type": "span",
            "name": f"{provider}-auto-trace",
            "metadata": {"auto_traced": True}
        }

        try:
            from langfuse import propagate_attributes
            prop_kwargs = {}
            if user_id is not None: prop_kwargs["user_id"] = user_id
            if session_id is not None: prop_kwargs["session_id"] = session_id
            
            with client.start_as_current_observation(**trace_kwargs) as trace:
                if prop_kwargs:
                    # We enter the context to propagate attributes to the generation span
                    prop_cm = propagate_attributes(**prop_kwargs)
                    prop_cm.__enter__()
                try:
                    _set_trace_id(trace.id)
                    tracer = tracer_cls(client)
                    
                    gen_kwargs = {
                        "as_type": "generation",
                        "name": f"{provider}-generation",
                        "model": model,
                        "metadata": {"auto_traced": True}
                    }

                    with client.start_as_current_observation(**gen_kwargs) as gen:
                        start_time = time.perf_counter()
                        try:
                            result = wrapped(*args, **kwargs)
                            latency = (time.perf_counter() - start_time) * 1000
                            usage = tracer.extract_usage(result, model=model)
                            
                            pricing_source = usage.pop("pricingSource", "unknown")
                            pricing_version = usage.pop("pricingVersion", "unknown")
                            
                            usage_details = {
                                "input": usage.get("input", 0),
                                "output": usage.get("output", 0),
                                "total": usage.get("total", 0)
                            }
                            
                            cost_details = {
                                "input": usage.get("inputCost", 0.0),
                                "output": usage.get("outputCost", 0.0),
                                "total": usage.get("totalCost", 0.0),
                                "inputCost": usage.get("inputCost", 0.0),
                                "outputCost": usage.get("outputCost", 0.0),
                                "totalCost": usage.get("totalCost", 0.0)
                            }
                            
                            gen.update(
                                output=str(getattr(result, "text", result)),
                                usage_details=usage_details,
                                cost_details=cost_details,
                                metadata={
                                    "latency_ms": round(latency, 2),
                                    "pricing_source": pricing_source,
                                    "pricing_version": pricing_version
                                }
                            )
                            
                            # Force standard OTEL cost attribute so Langfuse backend definitely picks it up
                            try:
                                import opentelemetry.trace as otel_trace
                                current_span = otel_trace.get_current_span()
                                if current_span and current_span.is_recording():
                                    current_span.set_attribute("gen_ai.usage.input_cost", usage.get("inputCost", 0.0))
                                    current_span.set_attribute("gen_ai.usage.output_cost", usage.get("outputCost", 0.0))
                                    current_span.set_attribute("gen_ai.usage.cost", usage.get("totalCost", 0.0))
                            except ImportError:
                                pass
                            trace.update(output="SUCCESS")
                            return result
                        except Exception as e:
                            gen.update(status_message=str(e), metadata={"error": True})
                            trace.update(output=f"ERROR: {str(e)}")
                            raise
                finally:
                    if prop_kwargs:
                        prop_cm.__exit__(None, None, None)
        except ImportError:
            # Fallback if propagate_attributes is not available
            with client.start_as_current_observation(**trace_kwargs) as trace:
                _set_trace_id(trace.id)
                tracer = tracer_cls(client)
                
                gen_kwargs = {
                    "as_type": "generation",
                    "name": f"{provider}-generation",
                    "model": model,
                    "metadata": {"auto_traced": True}
                }

                with client.start_as_current_observation(**gen_kwargs) as gen:
                    start_time = time.perf_counter()
                    try:
                        result = wrapped(*args, **kwargs)
                        latency = (time.perf_counter() - start_time) * 1000
                        usage = tracer.extract_usage(result, model=model)
                        
                        pricing_source = usage.pop("pricingSource", "unknown")
                        pricing_version = usage.pop("pricingVersion", "unknown")
                        
                        usage_details = {
                            "input": usage.get("input", 0),
                            "output": usage.get("output", 0),
                            "total": usage.get("total", 0)
                        }
                        
                        cost_details = {
                            "input": usage.get("inputCost", 0.0),
                            "output": usage.get("outputCost", 0.0),
                            "total": usage.get("totalCost", 0.0),
                            "inputCost": usage.get("inputCost", 0.0),
                            "outputCost": usage.get("outputCost", 0.0),
                            "totalCost": usage.get("totalCost", 0.0)
                        }
                        
                        gen.update(
                            output=str(getattr(result, "text", result)),
                            usage_details=usage_details,
                            cost_details=cost_details,
                            metadata={
                                "latency_ms": round(latency, 2),
                                "pricing_source": pricing_source,
                                "pricing_version": pricing_version
                            }
                        )
                        
                        # Force standard OTEL cost attribute so Langfuse backend definitely picks it up
                        try:
                            import opentelemetry.trace as otel_trace
                            current_span = otel_trace.get_current_span()
                            if current_span and current_span.is_recording():
                                current_span.set_attribute("gen_ai.usage.input_cost", usage.get("inputCost", 0.0))
                                current_span.set_attribute("gen_ai.usage.output_cost", usage.get("outputCost", 0.0))
                                current_span.set_attribute("gen_ai.usage.cost", usage.get("totalCost", 0.0))
                        except ImportError:
                            pass
                        trace.update(output="SUCCESS")
                        return result
                    except Exception as e:
                        gen.update(status_message=str(e), metadata={"error": True})
                        trace.update(output=f"ERROR: {str(e)}")
                        raise
    return wrapper

def observe():
    # Legacy Gemini SDK (google-generativeai)
    try:
        import google.generativeai as genai
        if "gemini_legacy" not in _already_patched:
            wrapt.wrap_function_wrapper(
                "google.generativeai.generative_models", 
                "GenerativeModel.generate_content", 
                _build_wrapper("gemini", GeminiTracer)
            )
            _already_patched.add("gemini_legacy")
    except ImportError: pass

    # New Gemini SDK (google-genai)
    try:
        # The new SDK is often imported from google.genai
        from google import genai as new_genai
        if "gemini_new" not in _already_patched:
            # Models.generate_content is the main call
            wrapt.wrap_function_wrapper(
                "google.genai.models", 
                "Models.generate_content", 
                _build_wrapper("gemini", GeminiTracer)
            )
            _already_patched.add("gemini_new")
    except ImportError: pass

    # Anthropic
    try:
        import anthropic
        if "anthropic" not in _already_patched:
            wrapt.wrap_function_wrapper(
                "anthropic.resources.messages", 
                "Messages.create", 
                _build_wrapper("anthropic", AnthropicTracer)
            )
            _already_patched.add("anthropic")
    except ImportError: pass

def unpatch(): pass

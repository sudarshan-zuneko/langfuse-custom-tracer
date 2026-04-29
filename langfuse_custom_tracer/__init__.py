from langfuse_custom_tracer.client import create_langfuse_client, load_env
from langfuse_custom_tracer.tracers.base import BaseTracer
from langfuse_custom_tracer.tracers.gemini import GeminiTracer
from langfuse_custom_tracer.tracers.anthropic import AnthropicTracer
from langfuse_custom_tracer.clients.traced_llm import TracedLLMClient, LLMResponse
from langfuse_custom_tracer.factory import create_traced_client
from langfuse_custom_tracer.auto import observe, unpatch
from langfuse_custom_tracer.context import set_user, set_session, end_session, get_trace_id
from langfuse_custom_tracer.scoring import score

__version__ = "1.1.1"
__author__  = "Sudarshan Rawate"
__email__   = "sudarshan.r@zuneko.in"

__all__ = [
    "create_langfuse_client",
    "load_env",
    # Manual tracers
    "BaseTracer",
    "GeminiTracer",
    "AnthropicTracer",
    # Traced Client
    "TracedLLMClient",
    "LLMResponse",
    "create_traced_client",
    # Automatic Tracing (v3)
    "observe",
    "unpatch",
    "set_user",
    "set_session",
    "end_session",
    "get_trace_id",
    "score",
]

"""
langfuse_custom_tracer — Langfuse v4 compatible tracers + automatic tracing
"""

from langfuse_custom_tracer.client import create_langfuse_client, load_env
from langfuse_custom_tracer.tracers.base import BaseTracer
from langfuse_custom_tracer.tracers.gemini import GeminiTracer
from langfuse_custom_tracer.tracers.anthropic import AnthropicTracer
from langfuse_custom_tracer.clients.traced_llm import TracedLLMClient, LLMResponse
from langfuse_custom_tracer.factory import create_traced_client

__version__ = "1.0.2"
__author__  = "Sudarshan Rawate"
__email__   = "sudarshan.r@zuneko.in"

__all__ = [
    # Client setup
    "create_langfuse_client",
    "load_env",
    # Manual tracers (Tier 1)
    "BaseTracer",
    "GeminiTracer",
    "AnthropicTracer",
    # Automatic tracing (Tier 2 — new in v1.0.0)
    "TracedLLMClient",
    "LLMResponse",
    "create_traced_client",
]

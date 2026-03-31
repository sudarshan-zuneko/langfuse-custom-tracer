"""
langfuse_custom_tracer — Langfuse v4 compatible tracers
"""

from langfuse_custom_tracer.client import create_langfuse_client, load_env
from langfuse_custom_tracer.tracers.base import BaseTracer
from langfuse_custom_tracer.tracers.gemini import GeminiTracer
from langfuse_custom_tracer.tracers.anthropic import AnthropicTracer

__version__ = "0.2.0"
__author__  = "Sudarshan Rawate"
__email__   = "sudarshan.r@zuneko.in"

__all__ = [
    "create_langfuse_client",
    "load_env",
    "BaseTracer",
    "GeminiTracer",
    "AnthropicTracer",
]

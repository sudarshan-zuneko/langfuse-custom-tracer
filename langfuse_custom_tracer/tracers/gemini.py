"""
Gemini tracer for Langfuse v4.

Pricing reference (USD per 1M tokens, as of Q1 2026):
  https://ai.google.dev/pricing
"""

from typing import Any

from .base import BaseTracer

GEMINI_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-pro":       {"input": 1.25,  "output": 10.00, "cached": 0.3125},
    "gemini-2.5-flash":     {"input": 0.30,  "output": 2.50,  "cached": 0.075},
    "gemini-2.5-flash-lite":{"input": 0.10,  "output": 0.40,  "cached": 0.025},
    "gemini-2.0-flash":     {"input": 0.15,  "output": 0.60,  "cached": 0.0375},
    "gemini-2.0-flash-lite":{"input": 0.075, "output": 0.30,  "cached": 0.01875},
    "gemini-1.5-pro":       {"input": 1.25,  "output": 5.00,  "cached": 0.3125},
    "gemini-1.5-flash":     {"input": 0.075, "output": 0.30,  "cached": 0.01875},
    "gemini-1.5-flash-8b":  {"input": 0.0375,"output": 0.15,  "cached": 0.01},
}
_DEFAULT_PRICING = {"input": 0.15, "output": 0.60, "cached": 0.0375}


def _get_pricing(model: str) -> dict[str, float]:
    model_lower = model.lower()
    for key in sorted(GEMINI_PRICING, key=len, reverse=True):
        if model_lower.startswith(key):
            return GEMINI_PRICING[key]
    return _DEFAULT_PRICING


class GeminiTracer(BaseTracer):
    """
    Langfuse v4 tracer for Google Gemini models.

    Usage::

        from langfuse_custom_tracer import create_langfuse_client, GeminiTracer
        import google.generativeai as genai

        lf     = create_langfuse_client("sk-lf-...", "pk-lf-...")
        tracer = GeminiTracer(lf)

        genai.configure(api_key="YOUR_GEMINI_KEY")
        model = genai.GenerativeModel("gemini-2.0-flash")

        with tracer.trace("invoice-pipeline", input={"file": "invoice.pdf"}) as span:
            with tracer.generation("extract", model="gemini-2.0-flash",
                                   input=prompt) as gen:
                response = model.generate_content(prompt)
                usage = tracer.extract_usage(response, model="gemini-2.0-flash")
                gen.update(output=response.text, usage_details=usage)
            span.update(output="done")

        tracer.flush()
    """

    def extract_usage(self, response: Any, model: str) -> dict:
        """
        Extract token usage from a Gemini response.

        Gemini ``usage_metadata`` field mapping:

        ================================  ========================
        Gemini field                      Langfuse v4 key
        ================================  ========================
        ``prompt_token_count``            ``input``
        ``candidates_token_count``        ``output``
        ``total_token_count``             ``total``
        ``cached_content_token_count``    subtracted from input,
                                          reported separately
        ================================  ========================

        Args:
            response: Raw Gemini SDK response object.
            model:    Model name for pricing lookup (e.g. "gemini-2.0-flash").

        Returns:
            Usage dict with at least keys input/output/total for Langfuse.
            Cost fields are included for convenience but should be passed in metadata.
        """
        _um = getattr(response, "usage_metadata", None)
        if not _um:
            # Return empty dict so Langfuse handles it as 'unknown' rather than zero
            return {}

        def _get_val(obj: Any, key: str) -> int:
            """Safe extraction from object or dict."""
            if hasattr(obj, key):
                return getattr(obj, key) or 0
            if isinstance(obj, dict):
                return obj.get(key) or 0
            # Try to get from protobuf-like object if it has .get()
            if hasattr(obj, "get"):
                try:
                    return obj.get(key) or 0
                except:
                    pass
            return 0

        prompt_tokens     = _get_val(_um, "prompt_token_count")
        completion_tokens = _get_val(_um, "candidates_token_count")
        total_tokens      = _get_val(_um, "total_token_count")
        cached_tokens     = _get_val(_um, "cached_content_token_count")

        new_input_tokens = max(0, prompt_tokens - cached_tokens)

        pricing = _get_pricing(model)
        input_cost  = (new_input_tokens  * pricing["input"])  / 1_000_000
        output_cost = (completion_tokens * pricing["output"]) / 1_000_000
        cache_cost  = (cached_tokens     * pricing["cached"]) / 1_000_000 if cached_tokens else 0.0
        total_cost  = input_cost + output_cost + cache_cost

        usage: dict[str, Any] = {
            "input":      new_input_tokens,
            "output":     completion_tokens,
            "total":      total_tokens,
            "unit":       "TOKENS",
            # Cost fields are included for convenience, but Langfuse expects only input/output/total in usage
            "inputCost":  input_cost,
            "outputCost": output_cost,
            "totalCost":  total_cost,
        }

        if cached_tokens:
            usage["cachedTokens"] = cached_tokens

        return usage
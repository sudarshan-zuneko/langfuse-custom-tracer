"""
Base tracer for Langfuse v4 custom LLM tracing.

Langfuse v4 (released March 2026) is built on OpenTelemetry.
Key API changes from v2/v3:
  - Langfuse() constructor  →  get_client() singleton
  - start_observation()     →  start_as_current_observation() context manager
  - usage_details / cost    →  single usage={} dict with inputCost/outputCost
  - Parent-child nesting is handled automatically by OTEL context propagation
"""

from contextlib import contextmanager
from typing import Any, Generator


class BaseTracer:
    """
    Base class for all LLM tracers. Compatible with Langfuse v4.

    Uses ``start_as_current_observation()`` context managers so that
    parent-child nesting is handled automatically by the OpenTelemetry
    context — no manual parent passing required.

    Subclasses must implement ``extract_usage()``.
    """

    def __init__(self, langfuse_client: Any) -> None:
        """
        Args:
            langfuse_client: A Langfuse v4 client from ``get_client()``
                             or ``create_langfuse_client()``.
        """
        self._lf = langfuse_client

    # ------------------------------------------------------------------ #
    #  Context-manager based API  (recommended — v4 native)               #
    # ------------------------------------------------------------------ #

    @contextmanager
    def trace(
        self,
        name: str,
        *,
        input: Any = None,
        metadata: dict | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
    ) -> Generator[Any, None, None]:
        """Context manager that opens a root span (trace).

        All ``generation()`` calls made inside this block are automatically
        nested as children via OpenTelemetry context propagation.

        Example::

            with tracer.trace("my-pipeline", input={"file": "doc.pdf"}) as span:
                with tracer.generation("gemini-call", model="gemini-2.0-flash",
                                       input=prompt) as gen:
                    response = gemini_model.generate_content(prompt)
                    usage = tracer.extract_usage(response, model="gemini-2.0-flash")
                    gen.update(output=response.text, usage=usage)
                span.update(output="done")
        """
        if not self._lf:
            yield None
            return

        kwargs: dict[str, Any] = {"as_type": "span", "name": name}
        if input      is not None: kwargs["input"]      = input
        if metadata   is not None: kwargs["metadata"]   = metadata
        if user_id    is not None: kwargs["user_id"]    = user_id
        if session_id is not None: kwargs["session_id"] = session_id
        if tags       is not None: kwargs["tags"]       = tags

        try:
            with self._lf.start_as_current_observation(**kwargs) as span:
                yield span
        except Exception as e:
            print(f"[LangfuseTracer] trace failed: {e}")
            yield None

    @contextmanager
    def generation(
        self,
        name: str,
        *,
        model: str,
        input: Any = None,
        metadata: dict | None = None,
    ) -> Generator[Any, None, None]:
        """Context manager that opens a generation span.

        Must be called *inside* a ``trace()`` block so it is automatically
        nested as a child.

        Example::

            with tracer.generation("extract", model="gemini-2.0-flash",
                                   input=prompt) as gen:
                response = model.generate_content(prompt)
                usage = tracer.extract_usage(response, model="gemini-2.0-flash")
                gen.update(output=response.text, usage=usage)
        """
        if not self._lf:
            yield None
            return

        kwargs: dict[str, Any] = {
            "as_type": "generation",
            "name":    name,
            "model":   model,
        }
        if input    is not None: kwargs["input"]    = input
        if metadata is not None: kwargs["metadata"] = metadata

        try:
            with self._lf.start_as_current_observation(**kwargs) as gen:
                yield gen
        except Exception as e:
            print(f"[LangfuseTracer] generation failed: {e}")
            yield None

    # ------------------------------------------------------------------ #
    #  Flush                                                               #
    # ------------------------------------------------------------------ #

    def flush(self) -> None:
        """Flush pending Langfuse events. Call this in short-lived scripts."""
        if self._lf:
            try:
                self._lf.flush()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  To be overridden by subclasses                                     #
    # ------------------------------------------------------------------ #

    def extract_usage(self, response: Any, **kwargs: Any) -> dict:
        """Parse token counts + compute cost from an LLM response.

        Subclasses MUST implement this.

        The returned dict is passed directly to ``gen.update(usage=...)``.
        Required keys for Langfuse v4 cost tracking:

        .. code-block:: python

            {
                "input":       <int>,    # prompt tokens
                "output":      <int>,    # completion tokens
                "total":       <int>,    # total tokens
                "unit":        "TOKENS",
                "inputCost":   <float>,  # USD
                "outputCost":  <float>,  # USD
                "totalCost":   <float>,  # USD
            }
        """
        raise NotImplementedError("Subclasses must implement extract_usage()")
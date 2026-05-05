"""
Base tracer for Langfuse v4 custom LLM tracing.

Langfuse v4 (released March 2026) is built on OpenTelemetry.
Key API changes from v2/v3:
  - Langfuse() constructor  →  get_client() singleton
  - start_observation()     →  start_as_current_observation()
  - usage_details / cost    →  single usage={} dict with inputCost/outputCost
  - Parent-child nesting is handled automatically by OTEL context propagation
"""

from contextlib import contextmanager
from typing import Any, Generator
from langfuse_custom_tracer.pricing_manager import pricing_manager
from langfuse_custom_tracer.context import get_user, get_session


class BaseTracer:
    """
    Base class for all LLM tracers. Compatible with Langfuse v4.

    Uses ``start_as_current_observation()`` context managers so that
    parent-child nesting is handled automatically by the OpenTelemetry
    context — no manual parent passing required.

    Subclasses must implement ``extract_usage()``.
    """

    def __init__(self, langfuse_client: Any) -> None:
        self._lf = langfuse_client

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
        """
        if not self._lf:
            yield None
            return

        # If user_id/session_id not provided, try to get from context
        _user_id = user_id or get_user()
        _session_id = session_id or get_session()

        kwargs: dict[str, Any] = {"as_type": "span", "name": name}
        if input is not None: kwargs["input"] = input
        if metadata is not None: kwargs["metadata"] = metadata

        try:
            obs_cm = self._lf.start_as_current_observation(**kwargs)
        except Exception as e:
            print(f"[LangfuseTracer] trace failed to start: {e}")
            yield None
            return

        try:
            from langfuse import propagate_attributes
            prop_kwargs = {}
            if _user_id is not None: prop_kwargs["user_id"] = _user_id
            if _session_id is not None: prop_kwargs["session_id"] = _session_id
            if tags is not None: prop_kwargs["tags"] = tags
            
            if prop_kwargs:
                with obs_cm as span, propagate_attributes(**prop_kwargs):
                    yield span
            else:
                with obs_cm as span:
                    yield span
        except ImportError:
            # Fallback if langfuse < 3.0 or propagate_attributes not available
            with obs_cm as span:
                yield span

    @contextmanager
    def generation(
        self,
        name: str,
        *,
        model: str,
        input: Any = None,
        metadata: dict | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Generator[Any, None, None]:
        """Context manager that opens a generation span.

        Must be called *inside* a ``trace()`` block so it is automatically
        nested as a child.

        Example::

            with tracer.generation("extract", model="gemini-2.0-flash",
                                   input=prompt) as gen:
                response = model.generate_content(prompt)
                usage = tracer.extract_usage(response, model="gemini-2.0-flash")
                gen.update(output=response.text, usage_details=usage)
        """
        if not self._lf:
            yield None
            return

        # If user_id/session_id not provided, try to get from context
        _user_id = user_id or get_user()
        _session_id = session_id or get_session()

        kwargs: dict[str, Any] = {
            "as_type": "generation",
            "name":    name,
            "model":   model,
        }
        if input    is not None: kwargs["input"]    = input
        if metadata is not None: kwargs["metadata"] = metadata

        try:
            obs_cm = self._lf.start_as_current_observation(**kwargs)
        except Exception as e:
            print(f"[LangfuseTracer] generation failed to start: {e}")
            yield None
            return

        try:
            from langfuse import propagate_attributes
            prop_kwargs = {}
            if _user_id is not None: prop_kwargs["user_id"] = _user_id
            if _session_id is not None: prop_kwargs["session_id"] = _session_id
            
            if prop_kwargs:
                with obs_cm as gen, propagate_attributes(**prop_kwargs):
                    yield gen
            else:
                with obs_cm as gen:
                    yield gen
        except ImportError:
            with obs_cm as gen:
                yield gen

    def flush(self) -> None:
        """Flush pending Langfuse events. Call this in short-lived scripts."""
        if self._lf:
            try:
                self._lf.flush()
            except Exception:
                pass

    def extract_usage(self, response: Any, **kwargs: Any) -> dict:
        """Parse token counts + compute cost from an LLM response.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement extract_usage()")

    def _get_pricing(self, model: str) -> tuple[dict[str, float], str, str]:
        """Get pricing for a model using the pricing manager.
        
        Returns:
            (price_dict, version, source)
        """
        return pricing_manager.get_price(model)
import warnings
from typing import Optional, Union, Literal
from .context import get_trace_id
from .auto import _get_langfuse

def score(
    name: str,
    value: Union[float, bool, str],
    trace_id: Optional[str] = None,
    comment: Optional[str] = None,
    data_type: Literal["NUMERIC", "BOOLEAN", "CATEGORICAL"] = "NUMERIC",
) -> None:
    """
    Attach a quality score to a trace.
    
    - If trace_id is not provided, it automatically targets the most recent 
      LLM call in the current context.
    - value: 0.0-1.0 (NUMERIC), True/False (BOOLEAN), or label (CATEGORICAL).
    """
    client = _get_langfuse()
    if client is None:
        return

    tid = trace_id or get_trace_id()
    if tid is None:
        raise RuntimeError(
            "score() called but no active trace_id found in context. "
            "Ensure auto-tracing is enabled and an LLM call has been made."
        )

    # Basic validation/clamping for numeric
    if data_type == "NUMERIC":
        try:
            val = float(value)
            if not (0.0 <= val <= 1.0):
                warnings.warn(f"langfuse-custom-tracer: NUMERIC score {val} clamped to [0,1]")
                val = max(0.0, min(1.0, val))
            value = val
        except (ValueError, TypeError):
            raise ValueError(f"NUMERIC score must be a number, got {type(value)}")

    try:
        client.score(
            trace_id=tid,
            name=name,
            value=value,
            comment=comment,
            data_type=data_type
        )
    except Exception as e:
        warnings.warn(f"langfuse-custom-tracer: Failed to send score - {e}")

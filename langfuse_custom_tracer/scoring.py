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
    """Send a score/feedback to Langfuse.
    
    In Langfuse v4, this uses the create_score() or score_current_trace() API.
    If no trace_id is provided, it tries to score the currently active trace.
    """
    client = _get_langfuse()
    if client is None: return

    # Validation
    if data_type == "NUMERIC":
        try:
            val = float(value)
            value = max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            raise ValueError(f"NUMERIC score must be a number, got {type(value)}")

    # Get trace ID from context if not provided
    tid = trace_id or get_trace_id()

    try:
        if tid:
            # Score a specific trace by ID (even if not active anymore)
            client.create_score(
                name=name, 
                value=value, 
                trace_id=tid, 
                comment=comment, 
                data_type=data_type
            )
        else:
            # Fallback to active trace in context (OTEL)
            client.score_current_trace(
                name=name, 
                value=value, 
                comment=comment, 
                data_type=data_type
            )
    except Exception as e:
        warnings.warn(f"langfuse-custom-tracer: Failed to send score - {e}")

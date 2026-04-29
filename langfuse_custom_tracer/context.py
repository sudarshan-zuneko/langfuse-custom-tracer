import contextvars
import uuid
from typing import Optional

# Context store for tracking identities across async tasks and threads
_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)
_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("session_id", default=None)
_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)

def set_user(user_id: str) -> None:
    """Attach a user identity to all subsequent LLM calls in this context."""
    if not user_id:
        _user_id.set(None)
    else:
        _user_id.set(str(user_id))

def set_session(session_id: Optional[str] = None) -> str:
    """
    Start a session. All subsequent calls in this context belong to this session.
    If no session_id is provided, a UUID is auto-generated.
    Returns the session_id.
    """
    sid = session_id or str(uuid.uuid4())
    _session_id.set(sid)
    return sid

def end_session() -> None:
    """Clear the current session."""
    _session_id.set(None)

def get_user() -> Optional[str]:
    """Get the current user_id from the context."""
    return _user_id.get()

def get_session() -> Optional[str]:
    """Get the current session_id from the context."""
    return _session_id.get()

def get_trace_id() -> Optional[str]:
    """Returns the trace_id of the most recent LLM call in this context."""
    return _trace_id.get()

def _set_trace_id(trace_id: str) -> None:
    """Internal use only: set the most recent trace ID."""
    _trace_id.set(trace_id)

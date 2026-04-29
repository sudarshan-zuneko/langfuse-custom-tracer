import contextvars
import uuid
from typing import Optional

_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)
_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("session_id", default=None)
_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)

def set_user(user_id: str) -> None:
    if not user_id:
        _user_id.set(None)
    else:
        _user_id.set(str(user_id))

def set_session(session_id: Optional[str] = None) -> str:
    sid = session_id or str(uuid.uuid4())
    _session_id.set(sid)
    return sid

def end_session() -> None:
    _session_id.set(None)

def get_user() -> Optional[str]:
    return _user_id.get()

def get_session() -> Optional[str]:
    return _session_id.get()

def get_trace_id() -> Optional[str]:
    return _trace_id.get()

def _set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)

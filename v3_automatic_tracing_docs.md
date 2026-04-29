# Automatic Tracing Implementation Plan — v3

> **Goal:** Zero-boilerplate tracing. Install the library, add one import, and every Gemini
> and Anthropic call is automatically tracked in Langfuse — with user identity, session
> grouping, and quality scoring — no manual wrapping required.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Core Library Changes](#core-library-changes)
3. [User Tracking](#user-tracking)
4. [Session Tracking](#session-tracking)
5. [Scoring](#scoring)
6. [Edge Cases & Failure Handling](#edge-cases--failure-handling)
7. [Extra Features](#extra-features)
8. [Verification Plan](#verification-plan)
9. [Performance Impact](#performance-impact)

---

## How It Works

```
User app
  └─ import langfuse_custom_tracer.auto
        └─ reads env vars → creates Langfuse singleton client
        └─ wrapt patches 4 SDK methods globally
              └─ every generate_content() / messages.create() call
                    ├─ reads user_id + session_id from context store (ContextVar)
                    ├─ opens Langfuse trace (tagged with user_id, session_id)
                    ├─ opens generation span inside the trace
                    ├─ calls real SDK
                    ├─ extracts usage via GeminiTracer / AnthropicTracer
                    ├─ closes span → sends to Langfuse async (background thread)
                    └─ score() can be called anytime after to rate the trace
```

**What Langfuse receives per call:**

| Field | Source |
|-------|--------|
| `trace_id` | Auto-generated UUID |
| `user_id` | Set via `set_user()` |
| `session_id` | Set via `set_session()` or auto-generated per thread/task |
| `model` | Extracted from SDK call args |
| `input` | Prompt text |
| `output` | Response text |
| `input_tokens` | SDK usage object |
| `output_tokens` | SDK usage object |
| `latency_ms` | Measured by wrapper |
| `cost` | Estimated from pricing table |
| `status` | `SUCCESS` or `ERROR` |
| `score` | Attached via `score()` after the call |
| `metadata` | Custom dict from `metadata_fn` |

---

## Core Library Changes

### 1. `pyproject.toml` — dependencies

```toml
[project]
dependencies = [
  "wrapt>=1.14",
  "langfuse>=2.0",
]
```

`wrapt` is a C extension (~50 ns dispatch overhead). It handles descriptors,
classmethods, and `__wrapped__` correctly — things naive `functools.wraps` misses.

---

### 2. `context.py` — new file (context store)

This is the backbone of user tracking, session tracking, and scoring.
It uses `contextvars.ContextVar` so values are isolated per async task / thread.

```python
# langfuse_custom_tracer/context.py

import contextvars
import uuid

_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)
_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("session_id", default=None)
_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

def set_user(user_id: str) -> None:
    """Attach a user identity to all subsequent LLM calls in this context."""
    _user_id.set(user_id)

def set_session(session_id: str | None = None) -> str:
    """
    Start a session. All subsequent calls in this context belong to this session.
    If no session_id is provided, a UUID is auto-generated.
    Returns the session_id so the caller can store it if needed.
    """
    sid = session_id or str(uuid.uuid4())
    _session_id.set(sid)
    return sid

def end_session() -> None:
    """Clear the current session. Next call starts a fresh session."""
    _session_id.set(None)

def get_user() -> str | None:
    return _user_id.get()

def get_session() -> str | None:
    return _session_id.get()

def get_trace_id() -> str | None:
    """Returns the trace_id of the most recent LLM call in this context."""
    return _trace_id.get()

def _set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)
```

**Why `contextvars` and not `threading.local`?**
`threading.local` works for sync code but breaks with `asyncio` — two coroutines
on the same thread share the same `local`. `contextvars.ContextVar` is
async-safe: each `asyncio` Task gets its own copy automatically.

---

### 3. `auto.py` — updated

Reads `user_id` and `session_id` from the context store on every call and
attaches them to the Langfuse trace.

```python
from .context import get_user, get_session, _set_trace_id

def _build_wrapper(tracer_cls):
    def wrapper(wrapped, instance, args, kwargs):
        if _client is None:
            return wrapped(*args, **kwargs)

        user_id   = get_user()
        session_id = get_session()

        trace = _client.trace(
            user_id=user_id,       # appears in Langfuse "Users" tab
            session_id=session_id, # groups calls in Langfuse "Sessions" tab
        )
        _set_trace_id(trace.id)    # expose trace_id for scoring

        gen = trace.generation(input=..., model=..., start_time=now())

        try:
            result = wrapped(*args, **kwargs)
            gen.update(output=..., usage=..., status="SUCCESS")
            return result
        except Exception as e:
            gen.update(status="ERROR", error=str(e))
            raise
    return wrapper
```

---

### 4. `scoring.py` — new file

```python
# langfuse_custom_tracer/scoring.py

from .context import get_trace_id
from .auto import _client

def score(
    name: str,
    value: float,
    trace_id: str | None = None,
    comment: str | None = None,
    data_type: str = "NUMERIC",   # "NUMERIC" | "BOOLEAN" | "CATEGORICAL"
) -> None:
    """
    Attach a score to a trace.

    - If trace_id is not provided, scores the most recent call in this context.
    - value: 0.0–1.0 for NUMERIC, True/False for BOOLEAN, a label for CATEGORICAL.
    - name: any string label e.g. "helpfulness", "thumbs_up", "relevance".
    """
    if _client is None:
        return

    tid = trace_id or get_trace_id()
    if tid is None:
        raise RuntimeError(
            "score() called but no trace_id found. "
            "Make sure auto tracing is enabled and at least one LLM call has been made."
        )

    _client.score(
        trace_id=tid,
        name=name,
        value=value,
        comment=comment,
        data_type=data_type,
    )
```

---

### 5. `__init__.py` — updated exports

```python
from .auto import observe, unpatch
from .context import set_user, set_session, end_session, get_trace_id
from .scoring import score

__all__ = [
    "observe",
    "unpatch",
    "set_user",
    "set_session",
    "end_session",
    "get_trace_id",
    "score",
]
```

---

## User Tracking

### What it does

Every Langfuse trace is tagged with a `user_id`. This populates the **Users** tab
in Langfuse, where you can see:
- Total calls per user
- Total tokens consumed per user
- Total estimated cost per user
- All traces for a specific user
- Error rate per user

### How to use it

Call `set_user()` once when you know who the user is — at login, at the start of a
request handler, or anywhere before the first LLM call. All subsequent calls in that
context are tagged automatically.

```python
from langfuse_custom_tracer import set_user
import langfuse_custom_tracer.auto

# In a web framework (FastAPI example)
@app.post("/chat")
async def chat_endpoint(request: ChatRequest, user: User = Depends(get_current_user)):
    set_user(user.id)                          # tag once
    response = await model.generate_content_async(request.message)  # auto-tagged
    return {"reply": response.text}
```

```python
# In a script / CLI
from langfuse_custom_tracer import set_user

set_user("user_abc123")
result = model.generate_content("Hello")   # tagged to user_abc123
result2 = client.messages.create(...)     # also tagged to user_abc123
```

### What Langfuse shows

```
Users tab
├── user_abc123
│     ├── 42 traces
│     ├── 18,400 input tokens
│     ├── 9,200 output tokens
│     └── $0.34 estimated cost
└── user_xyz789
      └── ...
```

### Edge cases

| Scenario | Behaviour |
|----------|-----------|
| `set_user()` never called | `user_id=None` — trace appears in Langfuse without user tag |
| Multiple users in same process | Each request handler calls `set_user()` — `ContextVar` isolates per task |
| `set_user("")` | Treated as no user — warn and set `None` |
| `set_user()` called mid-session | All calls after the set are tagged to new user; prior calls unchanged |

---

## Session Tracking

### What it does

Groups multiple LLM calls into a **session** — a conversation, a pipeline run, or
any logical unit of work. Langfuse shows all calls in a session as a timeline,
making it easy to debug multi-turn conversations and pipelines.

### How to use it

```python
from langfuse_custom_tracer import set_user, set_session, end_session

set_user("user_abc123")
session_id = set_session()          # auto-generates a UUID session ID
# OR: set_session("my-session-42") # use your own ID

# All calls below belong to this session
turn1 = model.generate_content("What is RAG?")
turn2 = model.generate_content("Give me an example")
turn3 = client.messages.create(model="claude-sonnet-4-20250514", messages=[...])

end_session()                       # optional: close the session explicitly
# Next call will either have no session or start a new one
```

### Auto-session mode

If you never call `set_session()`, the library can optionally auto-generate a session
ID per thread/async task. Enable it at observe time:

```python
observe(auto_session=True)
```

Each new thread or async Task gets its own session UUID automatically.
This is useful for web servers where each request is its own task.

### What Langfuse shows

```
Sessions tab
└── session: a1b2c3d4
      ├── [0.0s]  generate_content("What is RAG?")          → 142 tokens
      ├── [1.4s]  generate_content("Give me an example")    → 89 tokens
      └── [3.1s]  messages.create(model=claude-sonnet-4...) → 210 tokens
                  Total session: 441 tokens | $0.008 | 3.1s
```

### Session ID propagation strategies

| Strategy | When to use |
|----------|-------------|
| `set_session()` manual | Web apps where you control the request lifecycle |
| `observe(auto_session=True)` | Scripts, CLIs, background workers |
| Pass `session_id` from frontend | Mobile/web apps that generate session IDs client-side |
| Use request ID as session ID | API services — one session per HTTP request |

```python
# FastAPI: use request ID as session
@app.post("/chat")
async def chat(request: Request, body: ChatRequest):
    set_user(get_current_user(request).id)
    set_session(request.headers.get("X-Request-ID") or str(uuid.uuid4()))
    response = await model.generate_content_async(body.message)
    return {"reply": response.text}
```

### Edge cases

| Scenario | Behaviour |
|----------|-----------|
| `end_session()` not called | Session stays open — acceptable for short-lived processes |
| Same session ID used across requests | Calls are grouped — useful for persistent conversations |
| Session ID collision | Langfuse groups them — ensure IDs are unique per logical session |
| `set_session()` inside an `@observe` decorated function | Nested session IDs — the decorator's session takes priority |

---

## Scoring

### What it does

Attaches a quality score to a trace after the LLM call completes. Scores appear in
Langfuse's **Scores** tab and can be used to:
- Track response quality over time
- Compare models (A/B testing)
- Flag low-quality responses for review
- Train reward models

### Score types

| Type | Value | Example use case |
|------|-------|-----------------|
| `NUMERIC` | `0.0` – `1.0` | Automated relevance score, BLEU, cosine similarity |
| `BOOLEAN` | `True` / `False` | Thumbs up / thumbs down from user |
| `CATEGORICAL` | Any string | `"good"`, `"bad"`, `"needs_review"` |

### How to use it

#### User feedback (thumbs up/down)

```python
from langfuse_custom_tracer import score, get_trace_id

# After the LLM call
response = model.generate_content("Summarise this document")
trace_id = get_trace_id()                      # capture trace ID immediately

# Later — when user clicks thumbs up or down
@app.post("/feedback")
async def feedback(payload: FeedbackPayload):
    score(
        name="user_feedback",
        value=1.0 if payload.thumbs_up else 0.0,
        trace_id=payload.trace_id,             # ID returned to frontend
        data_type="BOOLEAN",
        comment=payload.comment,               # optional free-text
    )
```

#### Automated scoring (LLM-as-judge)

```python
from langfuse_custom_tracer import score

response = model.generate_content(user_prompt)

# Score automatically using another LLM call
judge_prompt = f"""
Rate the following response for helpfulness from 0.0 to 1.0.
Response: {response.text}
Return only a float.
"""
judge_response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    messages=[{"role": "user", "content": judge_prompt}],
    max_tokens=10,
)
helpfulness = float(judge_response.content[0].text.strip())

score(name="helpfulness", value=helpfulness, data_type="NUMERIC")
# Scores the most recent call automatically — no trace_id needed
```

#### Multi-dimension scoring

```python
response = model.generate_content(user_prompt)

score(name="relevance",   value=0.9)
score(name="accuracy",    value=0.8)
score(name="tone",        value=1.0)
score(name="safe",        value=True,   data_type="BOOLEAN")
score(name="category",    value="good", data_type="CATEGORICAL")
```

#### Scoring a specific past trace

```python
# Store trace_id when the call is made
response = model.generate_content(prompt)
trace_id = get_trace_id()
store_in_db(response_id=my_id, trace_id=trace_id)

# Score it later (e.g. from a review queue)
row = db.get(response_id=my_id)
score(name="reviewed", value=True, trace_id=row.trace_id, data_type="BOOLEAN")
```

### Returning `trace_id` to the frontend

To let the frontend send feedback, return the `trace_id` with the response.

```python
@app.post("/chat")
async def chat(body: ChatRequest):
    response = model.generate_content(body.message)
    return {
        "reply": response.text,
        "trace_id": get_trace_id(),   # frontend stores this for feedback
    }

@app.post("/feedback")
async def feedback(body: FeedbackPayload):
    score(
        name="user_thumbs",
        value=body.liked,
        trace_id=body.trace_id,
        data_type="BOOLEAN",
    )
    return {"ok": True}
```

### What Langfuse shows

```
Scores tab
├── helpfulness   avg: 0.82   p50: 0.85   p10: 0.60   trend: ↑
├── user_feedback avg: 0.74   (74% thumbs up)
└── safe          100% True

Trace detail: a1b2c3
  ├── user_id:    user_abc123
  ├── session_id: sess_xyz
  ├── model:      gemini-1.5-pro
  ├── tokens:     142 in / 89 out
  ├── cost:       $0.0008
  └── scores:
        helpfulness: 0.9
        user_feedback: 1.0 (thumbs up)
        comment: "Really clear explanation"
```

### Edge cases

| Scenario | Behaviour |
|----------|-----------|
| `score()` called before any LLM call | Raises `RuntimeError` with clear message |
| `score()` with invalid `value` type | Raises `ValueError` — validate before sending to Langfuse |
| `score()` with unknown `trace_id` | Langfuse returns 404 — catch and log, do not crash |
| Tracing disabled (no env vars) | `score()` is a no-op silently |
| `value` outside 0.0–1.0 for NUMERIC | Clamp to range with a warning |

```python
def score(name, value, trace_id=None, comment=None, data_type="NUMERIC"):
    if _client is None:
        return  # tracing disabled — no-op

    if data_type == "NUMERIC":
        if not isinstance(value, (int, float)):
            raise ValueError(f"NUMERIC score value must be a number, got {type(value)}")
        value = max(0.0, min(1.0, float(value)))  # clamp

    tid = trace_id or get_trace_id()
    if tid is None:
        raise RuntimeError("score() called but no active trace found.")

    try:
        _client.score(trace_id=tid, name=name, value=value,
                      comment=comment, data_type=data_type)
    except Exception as e:
        warnings.warn(f"langfuse-custom-tracer: score() failed — {e}")
        # never crash the caller
```

---

## Edge Cases & Failure Handling

### EC-1 — Missing environment variables

**Problem:** `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, or `LANGFUSE_BASE_URL` not set.

**Behaviour:** Fail-open. Single warning at import time. Tracing, user tracking, session
tracking, and scoring are all no-ops. App runs normally.

```python
if not all([secret_key, public_key]):
    warnings.warn(
        "langfuse-custom-tracer: credentials not set — tracing disabled.",
        RuntimeWarning, stacklevel=2,
    )
    return
```

---

### EC-2 — Double patching

**Fix:** `_already_patched` dict sentinel per provider. Second call to `observe()` is a no-op.

---

### EC-3 — SDK not installed

**Fix:** `try/except ImportError` per provider. Missing SDK → skip silently.

---

### EC-4 — SDK call raises an exception

**Fix:** Log `status="ERROR"` to Langfuse, then `raise` unchanged.

---

### EC-5 — Streaming responses

**Fix:** Generator wrapper accumulates chunks, flushes to Langfuse on exhaustion.
Works for both sync (`for chunk in stream`) and async (`async for chunk in stream`).

---

### EC-6 — Langfuse server unreachable

**Fix:** Client init wrapped in `try/except`. Main thread never blocked.
All operations (`score`, `set_user`, etc.) are no-ops when `_client is None`.

---

### EC-7 — Async / event loop safety

**Fix:** `contextvars.ContextVar` used throughout — async-safe by design.
Pin `langfuse>=2.0` which uses a thread-safe background queue.

---

### EC-8 — Context nesting (auto + manual tracing)

**Fix:** Check for active trace context before creating a new root trace.
Auto-trace nests as a child generation under an existing manual trace.

---

### EC-9 — Very large prompts / responses

**Fix:** Optional truncation + `redact_inputs=True` / `redact_outputs=True` flags.

---

### EC-10 — `unpatch()` for test isolation

**Fix:** `unpatch()` restores original SDK methods. Call in `teardown()` between tests.

---

### EC-11 — `set_user()` / `set_session()` called from wrong context

**Problem:** In an async web server, a developer calls `set_user()` at module level
(not inside a request handler). Because `ContextVar` values are per-task, module-level
values are not propagated into request handlers.

**Fix:** Document clearly that `set_user()` and `set_session()` must be called inside
the request handler, not at module/startup level. Add a debug mode that warns when
`get_user()` returns `None` on a traced call.

```python
if _debug and get_user() is None:
    warnings.warn(
        "langfuse-custom-tracer: LLM call made without a user_id set. "
        "Call set_user() inside your request handler.",
        stacklevel=3,
    )
```

---

### EC-12 — Score sent before trace is flushed

**Problem:** `score()` is called immediately after an LLM call. The trace may not yet
have been delivered to Langfuse (it's in the async background queue). Langfuse returns
a 404 for the `trace_id`.

**Fix:** Langfuse SDK v2+ queues scores and retries. Additionally, expose
`flush()` for cases where the caller wants to guarantee delivery before scoring.

```python
from langfuse_custom_tracer import flush, score

response = model.generate_content(prompt)
flush()      # ensure trace is delivered
score(name="relevance", value=0.9)
```

---

### EC-13 — User ID contains PII

**Problem:** Developer passes an email or full name as `user_id`. This is stored in
Langfuse and may violate GDPR / privacy requirements.

**Fix:** Document that `user_id` should be an opaque internal ID (UUID, hashed ID),
never a name or email. Optionally add a `hash_user_id=True` flag that SHA-256 hashes
the value before sending.

```python
observe(hash_user_id=True)
# set_user("alice@example.com") → stored as sha256("alice@example.com")
```

---

## Extra Features

### F-1 — `@observe` decorator — pipeline grouping

```python
@observe(name="summarise_pipeline")
def run_pipeline(text):
    draft = model.generate_content(text)
    refined = client.messages.create(...)
    return refined
```

All SDK calls inside are nested under one named root trace.

---

### F-2 — Sampling rate

```python
observe(sample_rate=0.1)  # trace 10% of calls
```

---

### F-3 — Input/output redaction

```python
observe(redact_inputs=True, redact_outputs=True)
```

---

### F-4 — Custom metadata hook

```python
observe(metadata_fn=lambda req, res: {"feature": "chat", "ab_variant": "B"})
```

---

### F-5 — Auto session grouping

```python
observe(auto_session=True)  # new UUID session per thread / async task
```

---

### F-6 — Selective provider patching

```python
observe(providers=["anthropic"])
```

---

### F-7 — Cost estimation

Pricing table built into the library. Cost attached to every generation automatically.

---

### F-8 — Structured logging

```python
observe(log_calls=True)
# emits JSON log line per call to stdout / any configured handler
```

---

### F-9 — `flush()` utility

```python
from langfuse_custom_tracer import flush
flush()  # block until all buffered spans/scores are delivered
```

Useful before process exit in scripts, or before scoring a trace.

---

### F-10 — Debug mode

```python
observe(debug=True)
# Warns when:
# - LLM call made without user_id
# - LLM call made without session_id
# - score() called with no active trace
# - double-patch attempted
```

---

## Verification Plan

### Automated tests (`tests/test_auto_patch.py`)

| Test | What it checks |
|------|---------------|
| `test_gemini_sync_traced` | `generate_content()` → Langfuse generation with correct tokens |
| `test_anthropic_sync_traced` | `messages.create()` → Langfuse generation |
| `test_gemini_async_traced` | Async variant captured |
| `test_anthropic_async_traced` | Async variant captured |
| `test_streaming_captured` | Generator wrapper flushes on exhaustion |
| `test_no_env_vars_no_crash` | Missing credentials → no exception |
| `test_double_patch_safe` | `observe()` twice → exactly one span |
| `test_sdk_exception_reraised` | Error logged to Langfuse AND re-raised |
| `test_unpatch_restores` | After `unpatch()` → no interception |
| `test_sample_rate_zero` | `sample_rate=0.0` → no spans, calls still work |
| `test_redact_inputs` | `redact_inputs=True` → Langfuse gets `"[redacted]"` |
| `test_cost_estimation` | Known model + token count → correct cost |
| `test_context_nesting` | Auto trace nests under active manual trace |
| `test_set_user_tags_trace` | `set_user("u1")` → trace has `user_id="u1"` |
| `test_user_isolation_async` | Two async tasks → each has independent `user_id` |
| `test_set_session_groups_calls` | `set_session("s1")` → all calls share `session_id="s1"` |
| `test_auto_session_per_task` | `auto_session=True` → each async task gets unique session |
| `test_end_session_clears` | `end_session()` → next call has no session |
| `test_score_numeric` | `score("q", 0.9)` → Langfuse score attached to last trace |
| `test_score_boolean` | `score("ok", True, data_type="BOOLEAN")` works |
| `test_score_categorical` | `score("label", "good", data_type="CATEGORICAL")` works |
| `test_score_explicit_trace_id` | `score(..., trace_id="abc")` targets specific trace |
| `test_score_before_call_raises` | `score()` with no prior call → `RuntimeError` |
| `test_score_no_client_noop` | Tracing disabled → `score()` is silent no-op |
| `test_score_clamped` | `value=1.5` → clamped to `1.0` with warning |
| `test_hash_user_id` | `hash_user_id=True` → email is hashed before sending |
| `test_debug_warns_no_user` | `debug=True` + no `set_user()` → warning emitted |
| `test_flush_blocks` | `flush()` returns only after background queue is empty |

---

### Manual verification (`examples/auto_trace_demo.py`)

```python
import os
os.environ["LANGFUSE_SECRET_KEY"] = "sk-..."
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-..."
os.environ["LANGFUSE_BASE_URL"]   = "https://cloud.langfuse.com"

import langfuse_custom_tracer.auto
from langfuse_custom_tracer import set_user, set_session, score, get_trace_id, flush

import google.generativeai as genai
import anthropic

model  = genai.GenerativeModel("gemini-1.5-pro")
client = anthropic.Anthropic()

# ── Identify the user ──────────────────────────────────────────────────
set_user("user_demo_001")
session_id = set_session()
print(f"Session: {session_id}")

# ── Turn 1 ────────────────────────────────────────────────────────────
r1 = model.generate_content("What is retrieval-augmented generation?")
print("Gemini:", r1.text)
score(name="helpfulness", value=0.95)              # auto scores last trace

# ── Turn 2 ────────────────────────────────────────────────────────────
r2 = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=150,
    messages=[{"role": "user", "content": "Give me a Python example of RAG"}],
)
print("Anthropic:", r2.content[0].text)
trace_id = get_trace_id()                          # save for later feedback
score(name="user_feedback", value=True, data_type="BOOLEAN", comment="Very clear")

# ── Flush before exit ─────────────────────────────────────────────────
flush()
print("Done. Open Langfuse → Users → Sessions → Scores to see all data.")
```

---

## Performance Impact

| Concern | Impact | Mitigation |
|---------|--------|-----------|
| wrapt wrapper dispatch | ~50 ns per call | None needed |
| Span open/close | ~0.1–0.3 ms per call | None needed |
| `ContextVar` read (user/session) | ~10 ns per call | None needed |
| Usage extraction | ~0.05 ms | None needed |
| Langfuse network send | 0 ms blocking (background thread) | None needed |
| Score delivery | 0 ms blocking (background thread) | Use `flush()` if ordering matters |
| Memory for span buffer | Grows at high call rates | `sample_rate=0.1` in prod |
| Large prompt storage | Memory + bandwidth | `redact_inputs=True` or truncate |
| Langfuse server down | Never blocks main thread | `try/except` on client init |

**Rule of thumb:** A typical LLM API call takes 800 ms – 3 s.
The tracer adds < 0.5 ms total. Users, sessions, and scores add < 0.1 ms combined.
The overhead is unmeasurable in practice.

---

*Plan version 3 — adds user tracking (`set_user`), session tracking (`set_session`,
`end_session`, `auto_session`), quality scoring (`score`, `get_trace_id`, `flush`),
privacy controls (`hash_user_id`), debug mode, and 15 new tests covering all new
behaviour.*
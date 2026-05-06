# Langfuse Custom Tracer

<div align="center">

**Langfuse v4 tracing for Google Gemini and Anthropic Claude with automatic cost tracking**

![Tests](https://img.shields.io/badge/tests-81%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-64%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

## 🎯 What is This?

A lightweight Python library that adds **observability and cost tracking** to your LLM applications using [Langfuse](https://langfuse.com).

- **Automatic token counting** for all supported LLM providers
- **Dynamic cost calculation** with real-time pricing from remote JSON (no redeploy needed!)
- **Nested trace visualization** in Langfuse
- **Simple context manager API** built on OpenTelemetry
- **Zero setup** - works with just API keys
- **TTL-based caching** for optimal performance
- **Graceful degradation** - never crashes on network failures

## 🚀 Quick Start

### 1. Install

```bash
# Basic installation
pip install langfuse-custom-tracer

# With environment variable support
pip install langfuse-custom-tracer[env]

# With Gemini support
pip install langfuse-custom-tracer[gemini]

# With Anthropic support
pip install langfuse-custom-tracer[anthropic]

# Everything (all providers)
pip install langfuse-custom-tracer[all]
```

### 2. Get API Keys

- **Langfuse**: Sign up at [cloud.langfuse.com](https://cloud.langfuse.com)
- **Gemini**: Get key from [ai.google.dev](https://ai.google.dev) (optional)
- **Anthropic**: Get key from [console.anthropic.com](https://console.anthropic.com) (optional)

### 3. Set Environment Variables

Create a `.env` file:

```env
# Langfuse (get from your dashboard)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...

# Gemini API (optional)
GEMINI_API_KEY=...

# Anthropic API (optional)
ANTHROPIC_API_KEY=...
```

### 4. Use It (Gemini Example)

```python
import os
from langfuse_custom_tracer import load_env, create_langfuse_client, GeminiTracer
import google.generativeai as genai

# Load environment variables
load_env()

# Initialize
lf = create_langfuse_client(
    os.getenv("LANGFUSE_SECRET_KEY"),
    os.getenv("LANGFUSE_PUBLIC_KEY")
)
tracer = GeminiTracer(lf)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# Use with tracing
with tracer.trace("invoice-processing", input={"file": "invoice.pdf"}) as span:
    with tracer.generation("extract-data", model="gemini-2.0-flash",
                          input="Extract name, amount, date") as gen:
        response = model.generate_content("Extract name, amount, date from invoice")
        usage = tracer.extract_usage(response, model="gemini-2.0-flash")
        # usage now includes pricing_source and pricing_version (automatically tracked)
        gen.update(output=response.text, usage_details=usage)
    span.update(output="Extraction complete")

tracer.flush()  # Send to Langfuse
```

### 4b. Use It (Anthropic Example)

```python
import os
from langfuse_custom_tracer import load_env, create_langfuse_client, AnthropicTracer
from anthropic import Anthropic

# Load environment variables
load_env()

# Initialize
lf = create_langfuse_client(
    os.getenv("LANGFUSE_SECRET_KEY"),
    os.getenv("LANGFUSE_PUBLIC_KEY")
)
tracer = AnthropicTracer(lf)

# Create Anthropic client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Use with tracing
with tracer.trace("invoice-processing", input={"file": "invoice.pdf"}) as span:
    with tracer.generation("extract-data", model="claude-3-5-sonnet-20241022",
                          input="Extract name, amount, date") as gen:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": "Extract name, amount, date from invoice"}]
        )
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        # usage now includes pricing_source and pricing_version (automatically tracked)
        gen.update(output=response.content[0].text, usage_details=usage)
    span.update(output="Extraction complete")

tracer.flush()  # Send to Langfuse
```

## 📊 What You'll See in Langfuse

### Dashboard View

```
📈 Trace: invoice-processing (ID: trace-123)
├─ ⏱ Duration: 2.3s
├─ 👤 User: (none set)
├─ 🏷️ Tags: [production, batch]
│
└─📝 Generation: extract-data
   ├─ Model: gemini-2.0-flash
   ├─ Status: ✅ Success
   ├─ Tokens: Input 156 | Output 89 | Total 245
   ├─ Cost: $0.000287 (auto-calculated from dynamic pricing)
   │  ├─ Input: $0.000234 (156 tokens @ $0.15/1M)
   │  ├─ Output: $0.000053 (89 tokens @ $0.60/1M)
   │  ├─ Pricing Source: json
   │  └─ Pricing Version: 2026-04-22-v1
   ├─ Latency: 1.8s
   └─ Output: "Name: John Doe, Amount: $500, Date: 2025-03-31"
```

### Cost Aggregation

All calls are automatically aggregated on the dashboard:
- **Total tokens**: 245,300 across all traces
- **Total cost**: $0.18 for the day
- **By model**: Gemini 2.0 Flash: $0.15, Gemini 1.5 Pro: $0.03

### Nested Traces

Langfuse automatically detects nesting via OpenTelemetry context:

```python
with tracer.trace("main-pipeline"):        # Parent span
    with tracer.trace("step-1"):           # Child span 1
        with tracer.generation(...):       # Grandchild span
            ...
    with tracer.trace("step-2"):           # Child span 2
        ...
```

Result in Langfuse: Clean hierarchical tree

## 🎮 Full API Reference

### `create_langfuse_client()`

```python
lf = create_langfuse_client(
    secret_key="sk-lf-...",                # Required
    public_key="pk-lf-...",                # Required
    host="https://cloud.langfuse.com"      # Optional, default EU
)
```

**Hosts:**
- EU: `https://cloud.langfuse.com` (default)
- US: `https://us.cloud.langfuse.com`

### `load_env()`

Load environment variables from `.env` file:

```python
from langfuse_custom_tracer import load_env

# Load from .env in current directory
load_env()

# Load from custom file
load_env(".env.production")
```

Requires `python-dotenv`. Install with: `pip install langfuse-custom-tracer[env]`

### `BaseTracer.trace()`

Create a root span (top-level trace):

```python
with tracer.trace(
    name="my-pipeline",
    input={"file": "data.csv"},
    metadata={"version": "1.0"},
    user_id="user-123",
    session_id="session-456",
    tags=["production", "batch"]
) as span:
    # Do work here
    span.update(output={"rows_processed": 1000})
```

**Parameters:**
- `name` (str): Span name
- `input` (any): Input data (shown in Langfuse)
- `metadata` (dict): Custom metadata
- `user_id` (str): User identifier
- `session_id` (str): Session identifier
- `tags` (list): String tags for filtering

### `BaseTracer.generation()`

Create a generation span (LLM call):

```python
with tracer.generation(
    name="extract",
    model="gemini-2.0-flash",
    input="Extract data",
    metadata={"temperature": 0.7}
) as gen:
    response = model.generate_content("Extract data")
    usage = tracer.extract_usage(response, model="gemini-2.0-flash")
    gen.update(output=response.text, usage_details=usage)
```

**Parameters:**
- `name` (str): Generation name
- `model` (str): Model identifier
- `input` (any): Prompt/input
- `metadata` (dict): Custom metadata

### `GeminiTracer.extract_usage()` / `AnthropicTracer.extract_usage()`

Extract token counts and calculate costs:

```python
# Gemini
usage = tracer.extract_usage(
    response,                           # Gemini response object
    model="gemini-2.0-flash"           # Model name for pricing
)

# Anthropic
usage = tracer.extract_usage(
    response,                           # Anthropic message object
    model="claude-3-5-sonnet-20241022"  # Model name for pricing
)

# Returns:
# {
#     "input": 156,              # Prompt tokens
#     "output": 89,              # Completion tokens
#     "total": 245,              # Total tokens
#     "unit": "TOKENS",
#     "inputCost": 0.000234,     # Input cost in USD (from dynamic pricing)
#     "outputCost": 0.000053,    # Output cost in USD (from dynamic pricing)
#     "totalCost": 0.000287,     # Total cost in USD
#     "cachedTokens": 10,        # (optional) cached tokens (Gemini & Anthropic)
#     "pricing_source": "json",  # Where pricing came from (json or default)
#     "pricing_version": "2026-04-22-v1"  # Pricing version for audit trail
# }
```

### `BaseTracer.flush()`

Send pending traces to Langfuse (blocking):

```python
tracer.flush()  # Wait for all events to be sent
```

Required for short-lived scripts. Long-running servers batch automatically.

## 🤖 Auto Tracing (Zero Boilerplate)

**NEW!** Automatic tracing with just one import. No manual wrapping required!

### What is Auto Tracing?

Instead of manually wrapping each LLM call, just import and enable auto-tracing:

```python
from langfuse_custom_tracer import observe

# Enable auto-tracing (patches Gemini & Anthropic SDK globally)
observe()

# Now every LLM call is automatically traced and sent to Langfuse!
import google.generativeai as genai

genai.configure(api_key="...")
model = genai.GenerativeModel("gemini-2.0-flash")

# This is automatically traced (no manual spans needed!)
response = model.generate_content("Hello, world!")
```

### Features

- ✅ **Zero boilerplate** - One import, automatic tracing
- ✅ **User tracking** - Tag all calls to a specific user
- ✅ **Session grouping** - Group related calls together
- ✅ **Score & rate** - Attach quality scores after the fact
- ✅ **Async support** - Works with asyncio (contextvars-based)
- ✅ **Error handling** - Captures failures gracefully
- ✅ **Dynamic pricing** - Automatic cost calculation
- ✅ **Latency tracking** - Measures wall-clock time

### Basic Setup

```python
import os
from langfuse_custom_tracer import load_env, observe

# Load credentials from .env
load_env()

# Enable auto-tracing (must be done before importing LLM SDKs)
observe()

# Now all Gemini and Anthropic calls are automatically traced!
import google.generativeai as genai
from anthropic import Anthropic

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Both calls are automatically traced
gemini_response = gemini_model.generate_content("Who invented Python?")
anthropic_response = anthropic_client.messages.create(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Who invented Python?"}]
)
```

### User Tracking

Tag all calls to a specific user:

```python
from langfuse_custom_tracer import observe, set_user

observe()

# In a web app, set user at request start
@app.post("/chat")
async def chat(request: ChatRequest, user: User = Depends(get_current_user)):
    set_user(user.id)  # Tag all subsequent calls to this user
    
    # This call is automatically traced and tagged to user.id
    response = await model.generate_content(request.message)
    return {"reply": response.text}
```

In Langfuse, you'll see:
- **Users tab**: All calls aggregated by user
- **Cost per user**: Total tokens and estimated cost
- **User sessions**: All conversations for a specific user

### Session Tracking

Group related calls into sessions:

```python
from langfuse_custom_tracer import observe, set_user, set_session

observe()

@app.post("/new-conversation")
async def new_conversation(user: User = Depends(get_current_user)):
    set_user(user.id)
    session_id = set_session()  # Start a new session, get ID back
    
    # All subsequent calls in this context are grouped
    response1 = model.generate_content("Question 1")
    response2 = model.generate_content("Question 2")
    response3 = model.generate_content("Question 3")
    
    # Later, you can retrieve the session ID:
    store_session_id(user.id, session_id)
```

In Langfuse, you'll see:
- **Sessions tab**: All calls in a conversation grouped together
- **Timeline view**: See the flow of a multi-turn conversation
- **Session metrics**: Total cost and tokens per conversation

### Scoring & Feedback

Attach quality scores to traces after the call completes:

```python
from langfuse_custom_tracer import observe, set_user, score, get_trace_id

observe()

set_user("user-123")

# Make LLM call
response = model.generate_content("Explain quantum computing")

# Later (even in a different request), score the trace
trace_id = get_trace_id()  # Get the trace ID from current context

# User clicks "thumbs up" button
score("thumbs_up", 1.0, trace_id=trace_id, comment="Very helpful!")

# Or score by quality metrics
score("relevance", 0.95, trace_id=trace_id, data_type="NUMERIC")
score("hallucination", False, trace_id=trace_id, data_type="BOOLEAN")
```

### Async Support

Auto-tracing works seamlessly with asyncio:

```python
import asyncio
from langfuse_custom_tracer import observe, set_user
import google.generativeai as genai

observe()

async def process_user_batch(user_id: str, messages: list):
    set_user(user_id)  # ContextVar isolates per asyncio task
    
    # Each task gets its own user_id
    tasks = [
        model.generate_content_async(msg) 
        for msg in messages
    ]
    
    # All calls tagged to the same user_id (via ContextVar)
    results = await asyncio.gather(*tasks)
    return results

# Each user gets their own isolated context
asyncio.run(process_user_batch("user-1", ["msg1", "msg2"]))
asyncio.run(process_user_batch("user-2", ["msg3", "msg4"]))
```

### Auto Tracing API Reference

| Function | Purpose |
|----------|---------|
| `observe()` | Enable auto-tracing (patches SDK globally) |
| `set_user(user_id)` | Tag all subsequent calls to a user |
| `set_session(session_id=None)` | Start a session (auto-generates UUID if not provided) |
| `end_session()` | Clear current session |
| `get_trace_id()` | Get trace ID of most recent call |
| `score(name, value, trace_id=None, comment=None, data_type="NUMERIC")` | Attach score to trace |

### What Gets Traced Automatically

Each auto-traced call captures:
- ✅ Model name
- ✅ Input prompt
- ✅ Output response
- ✅ Token counts (input, output, cached)
- ✅ Cost (dynamic, from remote pricing)
- ✅ Latency (wall-clock time in ms)
- ✅ User ID and session ID
- ✅ Status (SUCCESS or ERROR)
- ✅ Pricing source and version

### Supported SDKs

| Provider | SDK | Methods Patched | Status |
|----------|-----|-----------------|--------|
| **Gemini (Legacy)** | `google-generativeai` | `GenerativeModel.generate_content()` | ✅ Supported |
| **Gemini (New)** | `google-genai` | `Models.generate_content()` | ✅ Supported |
| **Anthropic** | `anthropic` | `Messages.create()` | ✅ Supported |

## 🔧 Supported Models

### Gemini ✅

All Google Gemini models with Q1 2026 pricing:

| Model | Input | Output | Cache |
|-------|-------|--------|-------|
| gemini-2.5-pro | $1.25/1M | $10.00/1M | $0.3125/1M |
| gemini-2.0-flash | $0.15/1M | $0.60/1M | $0.0375/1M |
| gemini-2.0-flash-lite | $0.075/1M | $0.30/1M | $0.01875/1M |
| gemini-1.5-pro | $1.25/1M | $5.00/1M | $0.3125/1M |
| gemini-1.5-flash | $0.075/1M | $0.30/1M | $0.01875/1M |
| gemini-1.5-flash-8b | $0.0375/1M | $0.15/1M | $0.01/1M |

### Anthropic Claude ✅

All Claude models with Q1 2026 pricing (with prompt caching support):

| Model | Input | Output | Cache Read | Cache Write |
|-------|-------|--------|------------|--------------|
| claude-3-5-sonnet-20241022 | $3.00/1M | $15.00/1M | $0.30/1M | $3.75/1M |
| claude-3-5-haiku-20241022 | $0.80/1M | $4.00/1M | $0.08/1M | $1.00/1M |
| claude-3-opus-20250219 | $15.00/1M | $75.00/1M | $1.50/1M | $18.75/1M |
| claude-3-sonnet-20250229 | $3.00/1M | $15.00/1M | $0.30/1M | $3.75/1M |
| claude-3-haiku-20250307 | $0.80/1M | $4.00/1M | $0.08/1M | $1.00/1M |

## 📁 Project Structure

```
langfuse-custom-tracer/
├── langfuse_custom_tracer/
│   ├── __init__.py              # Package exports
│   ├── client.py                # Langfuse client setup
│   ├── pricing_manager.py       # Dynamic pricing manager (NEW)
│   ├── auto.py                  # Automatic tracer patching
│   ├── context.py               # Context management
│   ├── factory.py               # Tracer factory
│   ├── scoring.py               # Cost scoring
│   └── tracers/
│       ├── __init__.py
│       ├── base.py              # BaseTracer (abstract)
│       ├── gemini.py            # GeminiTracer (19 tests, dynamic pricing)
│       └── anthropic.py         # AnthropicTracer (43 tests, dynamic pricing)
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_pricing_manager.py  # 19 tests (new)
│   ├── test_gemini_tracer.py    # 19 tests
│   ├── test_anthropic_tracer.py # 43 tests
│   ├── test_base_tracer.py      # Base tests
│   ├── test_auto_patch.py       # Auto patching tests
│   ├── test_factory.py          # Factory tests
│   └── test_client.py           # Client tests
├── pricing.json                  # Dynamic pricing data (NEW)
├── examples/
│   └── env_setup_example.py     # Usage example
├── SETUP.md                      # Setup guide
├── TESTING.md                    # Testing guide
├── FEATURE_COMPLETE.md           # Feature implementation details
└── pyproject.toml               # Package config
```

## 🧪 Testing

81 unit tests with 64% coverage:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov

# Run specific test
pytest tests/test_gemini_tracer.py::TestGeminiTracer::test_extract_usage_basic -v

# Run Anthropic tests
pytest tests/test_anthropic_tracer.py -v

# Run pricing manager tests
pytest tests/test_pricing_manager.py -v
```

All tests pass ✅

**Test Coverage Breakdown:**
- PricingManager: 19 tests, 79% coverage (remote pricing fetching, caching, fallback)
- AnthropicTracer: 43 tests, 100% coverage
- GeminiTracer: 19 tests, 76% coverage
- **Total**: 81 tests, 64% coverage

**Execution time**: ~1 second
**All tests passing**: ✅ 81/81

## 🔐 Security

- **Never commit `.env` files** - Already in `.gitignore`
- **API keys required** - Will raise `ImportError` if missing
- **HTTPS only** - All Langfuse communication encrypted
- **No keys in code** - Always use environment variables

## � Dynamic Pricing (NEW!)

**Major improvement**: Pricing is now decoupled from source code and managed via remote JSON!

```python
from langfuse_custom_tracer import get_pricing_manager

# Get pricing for a model
pm = get_pricing_manager()
price, version, source = pm.get_price("gemini-2.5-flash")
print(f"Input: ${price['input']} per 1M tokens (v{version}, from {source})")
```

**Benefits:**
- ✅ Update pricing without redeploying the library
- ✅ TTL-based caching (default 10 minutes)
- ✅ Graceful fallback if remote is unavailable
- ✅ All traces include pricing metadata
- ✅ Support for 25+ models across Gemini, Claude, GPT

**How it works:**
1. Library fetches pricing from remote JSON (GitHub by default)
2. Caches the data for 10 minutes
3. If remote is unavailable, uses cached or default pricing
4. Every trace includes `pricing_source` and `pricing_version`

**Custom pricing URL:**
```python
pm = get_pricing_manager(url="https://your-domain.com/pricing.json")
# Or via environment variable
# export PRICING_JSON_URL=https://your-domain.com/pricing.json
```

See [FEATURE_COMPLETE.md](./FEATURE_COMPLETE.md) for full details.

## �📚 Examples

### Example 1: Gemini Extraction Task

```python
from langfuse_custom_tracer import create_langfuse_client, GeminiTracer
import google.generativeai as genai
import os

lf = create_langfuse_client(
    os.getenv("LANGFUSE_SECRET_KEY"),
    os.getenv("LANGFUSE_PUBLIC_KEY")
)
tracer = GeminiTracer(lf)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# Simple extraction
with tracer.trace("email-analysis") as span:
    with tracer.generation("extract", model="gemini-2.0-flash",
                          input="Extract sender, subject, body") as gen:
        response = model.generate_content(
            "From the email below, extract sender, subject, body:\n..."
        )
        usage = tracer.extract_usage(response, model="gemini-2.0-flash")
        gen.update(output=response.text, usage_details=usage)

tracer.flush()
```

### Example 1b: Anthropic Extraction Task

```python
from langfuse_custom_tracer import create_langfuse_client, AnthropicTracer
from anthropic import Anthropic
import os

lf = create_langfuse_client(
    os.getenv("LANGFUSE_SECRET_KEY"),
    os.getenv("LANGFUSE_PUBLIC_KEY")
)
tracer = AnthropicTracer(lf)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Simple extraction with Claude
with tracer.trace("email-analysis") as span:
    with tracer.generation("extract", model="claude-3-5-sonnet-20241022",
                          input="Extract sender, subject, body") as gen:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{
                "role": "user",
                "content": "From the email below, extract sender, subject, body:\n..."
            }]
        )
        usage = tracer.extract_usage(response, model="claude-3-5-sonnet-20241022")
        gen.update(output=response.content[0].text, usage_details=usage)

tracer.flush()
```

### Example 2: Multi-Step Pipeline

```python
with tracer.trace("document-processing", user_id="user-123",
                 metadata={"doc_type": "invoice"}) as span:
    
    # Step 1: Extract text
    with tracer.trace("step-1-extract"):
        with tracer.generation("ocr", model="gemini-2.0-flash-lite"):
            text = model.generate_content("Extract text from image")
            # ...
    
    # Step 2: Classify
    with tracer.trace("step-2-classify"):
        with tracer.generation("classify", model="gemini-2.0-flash"):
            classification = model.generate_content(f"Classify: {text}")
            # ...
    
    # Step 3: Extract fields
    with tracer.trace("step-3-extract-fields"):
        with tracer.generation("extract", model="gemini-2.0-flash"):
            fields = model.generate_content(f"Extract fields: {text}")
            # ...

tracer.flush()
```

In Langfuse you'll see:
- Total latency: sum of all steps
- Total cost: $0.0015
- Token breakdown by step
- Each step as a child span

### Example 3: Error Handling

```python
with tracer.trace("risky-operation"):
    with tracer.generation("call", model="gemini-2.0-flash"):
        try:
            response = model.generate_content("...")
            usage = tracer.extract_usage(response)
            gen.update(output=response.text, usage_details=usage)
        except Exception as e:
            gen.update(status_code=500, error=str(e))
            raise

tracer.flush()
```

## 📖 Documentation

- [SETUP.md](./SETUP.md) - Installation and configuration
- [TESTING.md](./TESTING.md) - Testing guide and running tests
- [examples/env_setup_example.py](./examples/env_setup_example.py) - More examples

## 🤝 Contributing

This is an early-stage project. Contributions welcome!

**Next features:**
- Additional LLM providers (Ollama, Groq, Azure, Anthropic)
- Async support
- Batch operations
- Response filtering

## 📝 License

MIT - See [LICENSE](./LICENSE) file

## 🙋 Support

- **Documentation**: Read the [docs](./SETUP.md)
- **Issues**: Report bugs on GitHub
- **Questions**: Check [TESTING.md](./TESTING.md) for common issues

---

**Built with ❤️ for the LLM community**

*Langfuse is open-source observability for LLM applications*

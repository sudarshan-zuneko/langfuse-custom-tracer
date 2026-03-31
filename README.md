# Langfuse Custom Tracer

<div align="center">

**Langfuse v4 tracing for Google Gemini, Ollama, Groq, Azure OpenAI, and Anthropic**

![Tests](https://img.shields.io/badge/tests-47%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

## 🎯 What is This?

A lightweight Python library that adds **observability and cost tracking** to your LLM applications using [Langfuse](https://langfuse.com).

- **Automatic token counting** for all supported LLM providers
- **Cost calculation** with real-time pricing
- **Nested trace visualization** in Langfuse
- **Simple context manager API** built on OpenTelemetry
- **Zero setup** - works with just API keys

## 🚀 Quick Start

### 1. Install

```bash
# Basic installation
pip install langfuse-custom-tracer

# With environment variable support
pip install langfuse-custom-tracer[env]

# With Gemini support
pip install langfuse-custom-tracer[gemini]

# Everything
pip install langfuse-custom-tracer[all]
```

### 2. Get API Keys

- **Langfuse**: Sign up at [cloud.langfuse.com](https://cloud.langfuse.com)
- **Gemini**: Get key from [ai.google.dev](https://ai.google.dev)

### 3. Set Environment Variables

Create a `.env` file:

```env
# Langfuse (get from your dashboard)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...

# Gemini API
GEMINI_API_KEY=...
```

### 4. Use It

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
        gen.update(output=response.text, usage=usage)
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
   ├─ Cost: $0.00023
   │  ├─ Input: $0.000234 (156 tokens @ $0.15/1M)
   │  ├─ Output: $0.000053 (89 tokens @ $0.60/1M)
   │  └─ Total: $0.000287
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
    gen.update(output=response.text, usage=usage)
```

**Parameters:**
- `name` (str): Generation name
- `model` (str): Model identifier
- `input` (any): Prompt/input
- `metadata` (dict): Custom metadata

### `GeminiTracer.extract_usage()`

Extract token counts and calculate costs:

```python
usage = tracer.extract_usage(
    response,                           # Gemini response object
    model="gemini-2.0-flash"           # Model name for pricing
)

# Returns:
# {
#     "input": 156,              # Prompt tokens
#     "output": 89,              # Completion tokens
#     "total": 245,              # Total tokens
#     "unit": "TOKENS",
#     "inputCost": 0.000234,     # Input cost in USD
#     "outputCost": 0.000053,    # Output cost in USD
#     "totalCost": 0.000287,     # Total cost in USD
#     "cachedTokens": 10         # (optional) cached tokens
# }
```

### `BaseTracer.flush()`

Send pending traces to Langfuse (blocking):

```python
tracer.flush()  # Wait for all events to be sent
```

Required for short-lived scripts. Long-running servers batch automatically.

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

### Coming Soon ⏳

- **Ollama** (local models)
- **Groq** (fast inference)
- **Azure OpenAI** (enterprise)
- **Anthropic Claude** (frontier models)

## 📁 Project Structure

```
langfuse-custom-tracer/
├── langfuse_custom_tracer/
│   ├── __init__.py              # Package exports
│   ├── client.py                # Langfuse client setup
│   └── tracers/
│       ├── __init__.py
│       ├── base.py              # BaseTracer (abstract)
│       └── gemini.py            # GeminiTracer (concrete)
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_base_tracer.py      # 15 tests
│   ├── test_gemini_tracer.py    # 20 tests
│   └── test_client.py           # 12 tests
├── examples/
│   └── env_setup_example.py     # Usage example
├── SETUP.md                      # Setup guide
├── TESTING.md                    # Testing guide
└── pyproject.toml               # Package config
```

## 🧪 Testing

47 unit tests with 96% coverage:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov

# Run specific test
pytest tests/test_gemini_tracer.py::TestGeminiTracer::test_extract_usage_basic -v
```

All tests pass ✅

## 🔐 Security

- **Never commit `.env` files** - Already in `.gitignore`
- **API keys required** - Will raise `ImportError` if missing
- **HTTPS only** - All Langfuse communication encrypted
- **No keys in code** - Always use environment variables

## 📚 Examples

### Example 1: Simple Extraction Task

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
        usage = tracer.extract_usage(response)
        gen.update(output=response.text, usage=usage)

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
            gen.update(output=response.text, usage=usage)
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

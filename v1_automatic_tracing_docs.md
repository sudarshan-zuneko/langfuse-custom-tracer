# Langfuse Custom Tracer (v1.0+) — Automatic Tracing

As of **v1.0.0**, the library provides an **automatic tracing layer**. You no longer need to manually manage context managers (`with tracer.trace()`), tokens, or generation updates.

## 🚀 The New Approach: `TracedLLMClient`

The `TracedLLMClient` wraps your standard LLM calls and automatically:
1. Opens a top-level `trace` in Langfuse.
2. Opens a nested `generation` span.
3. Automatically calculates exact token counts.
4. Calculates real-time query pricing/costs.
5. Limits output sizes to 2,000 characters for Langfuse logging to prevent database bloat, while returning the **full text** back to your Python script.
6. Catches and logs all errors.

---

## 🛠️ Installation

```bash
# Basic setup
pip install langfuse-custom-tracer==1.0.2

# Include the Gemini SDK
pip install "langfuse-custom-tracer[gemini]"
```

---

## 📖 Quick Examples

### Example 1: Basic Text Generation

```python
import os
from langfuse_custom_tracer import load_env, create_langfuse_client, create_traced_client, GeminiTracer

# 1. Load keys from .env
load_env()

# 2. Init Langfuse
lf = create_langfuse_client(
    os.getenv("LANGFUSE_SECRET_KEY"), 
    os.getenv("LANGFUSE_PUBLIC_KEY")
)

# 3. Create the Automatic Tracing Client (This handles everything!)
llm = create_traced_client(
    provider="gemini",                     # "gemini" or "anthropic"
    api_key=os.getenv("GEMINI_API_KEY"),
    tracer=GeminiTracer(lf),
    model="gemini-2.5-flash"
)

# 4. Generate
response = llm.generate("Explain quantum computing in one sentence.")

print(f"Response:  {response.text}")
print(f"Total USD: ${response.usage['totalCost']:.6f}")
print(f"Latency:   {response.latency_ms:.0f} ms")

llm.flush()  # Ensures the trace hits the Langfuse servers before your script exits
```

### Example 2: Multimodal (Images/PDFs)

```python
import base64
from pathlib import Path

# Provide image logic
with open("bank_statement.pdf", "rb") as f:
    data = base64.b64encode(f.read()).decode("utf-8")

prompt = [
    {"inline_data": {"mime_type": "application/pdf", "data": data}},
    "Extract all transactions into a JSON array."
]

# Pass custom trace IDs and tags for your Langfuse Dashboard
response = llm.generate(
    prompt,
    trace_name="bank-statement-extraction",        # Shows up as Trace Name
    tags=["production", "app-v2"],                 # Tags in Langfuse Dashboard
    max_tokens=8192                                # SDK passthrough kwargs
)

print(f"Extracted JSON:\n{response.text}")
```

### Example 3: Running Multiple Queries in Parallel

Because the tracing is isolated, you can safely run multiple queries concurrently using `asyncio` without mixing up the traces.

```python
import asyncio

async def run_parallel():
    prompts = ["What is ML?", "What is AI?", "What is DL?"]
    
    # Run 3 queries at the exact same time
    tasks = [
        llm.agenerate(p, trace_name=f"task-{i}") 
        for i, p in enumerate(prompts)
    ]
    
    results = await asyncio.gather(*tasks)
    
    for r in results:
        print(f"Tokens: {r.usage['total']} | Answer: {r.text[:50]}...")

asyncio.run(run_parallel())
```

---

## 📦 What is `LLMResponse`?

Every time you call `.generate()` or `.agenerate()`, you receive an `LLMResponse` dataclass.

```python
@dataclass
class LLMResponse:
    text: str              # The raw string output from the model
    usage: dict            # Dictionary: input, output, total, inputCost, outputCost, totalCost
    model: str             # "gemini-2.5-flash"
    provider: str          # "gemini" or "anthropic"
    latency_ms: float      # How long the API call took
    raw_response: Any      # The raw, unfiltered SDK response block if you need it
```

### Sample Usage Dictionary
```json
{
  "input": 637,
  "output": 496,
  "total": 1133,
  "inputCost": 0.000191,
  "outputCost": 0.001240,
  "totalCost": 0.001431
}
```
*(Based on Q1 2026 pricing)*

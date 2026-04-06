"""
Example: Automatic tracing with Gemini using TracedLLMClient.

This is the new v1.0.0 way — no manual `with tracer.trace()` blocks needed.
"""

import os
from langfuse_custom_tracer import (
    load_env, create_langfuse_client, create_traced_client, GeminiTracer,
)

# 1. Load environment
if os.path.exists(".env"):
    load_env(".env")
elif os.path.exists("../.env"):
    load_env("../.env")

# 2. Initialize Langfuse + tracer
lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    base_url=os.getenv("LANGFUSE_BASE_URL"),
)

# 3. Create a traced client — ONE LINE
llm = create_traced_client(
    provider="gemini",
    api_key=os.getenv("GEMINI_API_KEY"),
    tracer=GeminiTracer(lf),
    model="gemini-2.0-flash",
)

# 4. Just call generate() — tracing is automatic!
prompt = "Explain quantum computing in one simple sentence."
print(f"Prompt: {prompt}")

response = llm.generate(prompt, trace_name="quantum-explanation")

print(f"\nResponse: {response.text}")
print(f"Model:    {response.model}")
print(f"Provider: {response.provider}")
print(f"Latency:  {response.latency_ms:.0f}ms")
print(f"Usage:    {response.usage}")

# 5. Flush traces
llm.flush()
print("\nTrace sent! Check your Langfuse dashboard.")

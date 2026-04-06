"""
Example: Automatic tracing with Anthropic Claude using TracedLLMClient.
"""

import os
from langfuse_custom_tracer import (
    load_env, create_langfuse_client, create_traced_client, AnthropicTracer,
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

# 3. Create traced client — just switch provider!
llm = create_traced_client(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    tracer=AnthropicTracer(lf),
    model="claude-3-5-sonnet-20241022",
    default_max_tokens=8192,  # High for bank statement processing
)

# 4. Generate with automatic tracing
response = llm.generate(
    "Explain quantum computing in one simple sentence.",
    trace_name="claude-explanation",
)

print(f"Response: {response.text}")
print(f"Usage:    {response.usage}")
print(f"Latency:  {response.latency_ms:.0f}ms")

llm.flush()
print("\nTrace sent!")

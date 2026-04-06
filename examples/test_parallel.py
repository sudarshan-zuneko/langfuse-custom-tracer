"""
Example: Parallel LLM calls with automatic tracing.

Each call creates its own independent trace in Langfuse.
Uses asyncio.gather for concurrent execution.
"""

import os
import asyncio
from langfuse_custom_tracer import (
    load_env, create_langfuse_client, create_traced_client, GeminiTracer,
)

# 1. Load environment
if os.path.exists(".env"):
    load_env(".env")
elif os.path.exists("../.env"):
    load_env("../.env")

# 2. Initialize
lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    base_url=os.getenv("LANGFUSE_BASE_URL"),
)

llm = create_traced_client(
    provider="gemini",
    api_key=os.getenv("GEMINI_API_KEY"),
    tracer=GeminiTracer(lf),
    model="gemini-2.0-flash",
)

# 3. Define parallel tasks
prompts = [
    "What is machine learning?",
    "What is deep learning?",
    "What is reinforcement learning?",
]


async def main():
    print(f"Running {len(prompts)} parallel LLM calls...\n")

    tasks = [
        llm.agenerate(
            prompt,
            trace_name=f"parallel-task-{i+1}",
            tags=["parallel", "demo"],
        )
        for i, prompt in enumerate(prompts)
    ]

    results = await asyncio.gather(*tasks)

    for i, resp in enumerate(results):
        print(f"Task {i+1}: {resp.text[:100]}...")
        print(f"  Tokens: {resp.usage.get('total', '?')}, Latency: {resp.latency_ms:.0f}ms")
        print()

    llm.flush()
    print("All traces sent!")


if __name__ == "__main__":
    asyncio.run(main())

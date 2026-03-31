"""
Example: Setting up and using credentials with .env file
"""

import os
from langfuse_custom_tracer import load_env, create_langfuse_client, GeminiTracer

# ============================================================
# OPTION 1: Load from .env file (Recommended)
# ============================================================
# 1. Create a .env file in your project root:
#    LANGFUSE_SECRET_KEY=sk-lf-...
#    LANGFUSE_PUBLIC_KEY=pk-lf-...
#    GEMINI_API_KEY=your-gemini-key

# 2. Load the .env file
load_env()

# 3. Create client from environment variables
lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
)

# 4. Create tracer
tracer = GeminiTracer(lf)

print("✓ Langfuse client initialized from .env file")


# ============================================================
# OPTION 2: Pass credentials directly (for CI/CD)
# ============================================================
# lf = create_langfuse_client(
#     secret_key="sk-lf-...",
#     public_key="pk-lf-...",
# )


# ============================================================
# OPTION 3: Load from custom .env file
# ============================================================
# load_env(".env.production")  # Use a different .env file
# lf = create_langfuse_client(
#     secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
#     public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
# )


if __name__ == "__main__":
    print("Setup complete! Your credentials are loaded.")
    print(f"Using Langfuse host: {os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com')}")

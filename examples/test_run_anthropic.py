import os
import sys
from langfuse_custom_tracer import load_env, create_langfuse_client
from langfuse_custom_tracer.tracers.anthropic import AnthropicTracer

# 1. Load keys from your .env file
# Try to load from current dir or parent dir
if os.path.exists(".env"):
    load_env(".env")
elif os.path.exists("../.env"):
    load_env("../.env")

# 2. Initialize the client
lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    base_url=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
)

# 3. Create the tracer
tracer = AnthropicTracer(lf)

# 4. Trigger whatever you need to trace here!
try:
    import anthropic
except ImportError:
    print("Error: 'anthropic' package not found. Install it with 'pip install anthropic'.")
    sys.exit(1)

anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_key:
    print("Error: ANTHROPIC_API_KEY is not set in your .env file.")
    print("Please add ANTHROPIC_API_KEY=your_key_here to your .env file.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=anthropic_key)
model_name = "claude-3-5-sonnet-20241022"

prompt = "Explain quantum computing in one simple sentence."
print(f"Sending prompt: '{prompt}' to {model_name}")

with tracer.trace("anthropic-claude-test", input={"prompt": prompt}) as span:
    with tracer.generation("generate-explanation", model=model_name, input=prompt) as gen:
        # Call Anthropic API
        response = client.messages.create(
            model=model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract usage and cost mapping
        usage = tracer.extract_usage(response, model=model_name)
        print("\nDEBUG extracted usage dictionary:", usage)
        
        # Update the Langfuse generation with output and usage
        # Note: usage_details is required for Langfuse v4 token tracking
        gen.update(output=response.content[0].text, usage_details=usage)
        print("\nClaude Response:", response.content[0].text)
        
    span.update(output="Successfully completed")

# Always flush at the end to ensure traces are sent before the script exits
tracer.flush()
print("\nTrace sent! Check your Langfuse Cloud Dashboard.")

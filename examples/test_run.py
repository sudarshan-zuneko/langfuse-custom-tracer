import os
from langfuse_custom_tracer import load_env, create_langfuse_client
from langfuse_custom_tracer.tracers.gemini import GeminiTracer

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
    base_url=os.getenv("LANGFUSE_BASE_URL")
)

# 3. Create the tracer
tracer = GeminiTracer(lf)

# 4. Trigger whatever you need to trace here!
import google.generativeai as genai
import sys

gemini_key = os.getenv("GEMINI_API_KEY")
if not gemini_key:
    print("Error: GEMINI_API_KEY is not set in your .env file.")
    sys.exit(1)

genai.configure(api_key=gemini_key)
model_name = "gemini-2.0-flash"
model = genai.GenerativeModel(model_name)

prompt = "Explain quantum computing in one simple sentence. in detail"
print(f"Sending prompt: '{prompt}'")

with tracer.trace("simple-gemini-test", input={"prompt": prompt}) as span:
    with tracer.generation("generate-explanation", model=model_name, input=prompt) as gen:
        response = model.generate_content(prompt)
        print("\nDEBUG raw usage_metadata:", getattr(response, 'usage_metadata', None))
        
        # Extract usage mapping using your custom Langfuse integration
        usage = tracer.extract_usage(response, model=model_name)
        print("DEBUG extracted usage dictionary:", usage)
        
        # Update the Langfuse generation and print
        gen.update(output=response.text, usage_details=usage)
        print("\nGemini Response:", response.text)
        
    span.update(output="Successfully completed")

# Always flush at the end to ensure traces are sent before the script exits
tracer.flush()
print("\nTrace sent! Check your Langfuse Cloud Dashboard.")

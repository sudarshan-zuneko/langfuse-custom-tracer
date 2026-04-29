import os
import google.generativeai as genai
from langfuse_custom_tracer import load_env, observe, set_user, set_session, score

# 1. Load configuration from .env
load_env()

# 2. Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)
genai.configure(api_key=api_key)

# 3. Enable Auto-Tracing
print("Enabling Langfuse Auto-Tracing...")
observe()

# 4. Set Context
set_user("tester_zuneko")
set_session("live_verification_session")

# 5. Make LLM Call (Automatically Traced)
print("Sending request to Gemini...")
model = genai.GenerativeModel("gemini-2.5-flash")

try:
    response = model.generate_content("Say 'Integration Successful' if you can read this.")
    print(f"Gemini Response: {response.text}")

    # 6. Score the response
    print("Attaching score...")
    score("integration_test", 1.0, comment="Live verification successful")
    
    print("\nSUCCESS: Live Test Completed!")
    print("Check your Langfuse dashboard for a trace named 'gemini-auto-trace'.")
    
    # Give Langfuse a second to flush in background
    import time
    from langfuse_custom_tracer.auto import _get_langfuse
    client = _get_langfuse()
    if client:
        print("Flushing traces...")
        client.flush()
        time.sleep(2)

except Exception as e:
    print(f"Error during live test: {e}")

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Import Langfuse auto-tracing and context functions
from langfuse_custom_tracer import observe, set_user, get_trace_id, score, flush

load_dotenv()

def run_pypi_auto_trace():
    print("Running Langfuse-custom-tracer PyPI auto-trace demo...")

    # 1. Enable auto-tracing. This patches the Gemini SDK.
    observe(debug=True)

    # 2. Set a user for the entire trace (optional, but good for context)
    set_user("pypi_auto_trace_user")

    try:
        # 3. Configure Gemini API key (this is still manual as it's an SDK requirement)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-3-flash-preview")

        # 4. Make a standard Gemini API call - it will be automatically traced!
        print("Making Gemini call (this will be automatically traced by langfuse-custom-tracer)...")
        response = model.generate_content("Write a short, funny poem about a cat and a laser pointer.")
        print(f"Gemini response: {response.text[:100]}...")

        # 5. Add a score to the automatically traced generation
        #    The `score` function will find the most recent active generation.
        score(name="humor", value=0.8, comment="The poem was mildly amusing.")
        print("Score added automatically to the trace.")
        
        trace_id = get_trace_id()
        print(f"Langfuse Trace ID: {trace_id}")
        print("Check your Langfuse dashboard for the trace, token usage, and cost.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure all traces are flushed to Langfuse
        flush()
        print("Langfuse traces flushed.")

if __name__ == "__main__":
    run_pypi_auto_trace()

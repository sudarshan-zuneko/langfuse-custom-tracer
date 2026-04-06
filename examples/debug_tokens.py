import os
from langfuse_custom_tracer import load_env
import google.generativeai as genai

load_env("../.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")
prompt = "Explain quantum computing in 5 sentences."

response = model.generate_content(prompt)
um = response.usage_metadata
print("prompt_token_count:", getattr(um, "prompt_token_count", None))
print("candidates_token_count:", getattr(um, "candidates_token_count", None))
print("total_token_count:", getattr(um, "total_token_count", None))
print("cached_content_token_count:", getattr(um, "cached_content_token_count", None))

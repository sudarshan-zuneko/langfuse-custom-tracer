import os
from langfuse_custom_tracer import load_env
import google.generativeai as genai
import base64
from pathlib import Path

load_env("../.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")
file_path = "../image2.jpeg"
with open(file_path, "rb") as f:
    data = base64.b64encode(f.read()).decode("utf-8")

part = {"inline_data": {"mime_type": "image/jpeg", "data": data}}
prompt = [part, "Analyze the provided bank statement"]

response = model.generate_content(prompt)
print("--- USAGE METADATA ---")
print(response.usage_metadata)

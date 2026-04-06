import os
import sys
import base64
from pathlib import Path
from langfuse_custom_tracer import load_env, create_langfuse_client
from langfuse_custom_tracer.tracers.gemini import GeminiTracer

# 1. Load keys from your .env file
load_env("../.env")

# 2. Initialize the client
lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL")
)

# 3. Create the tracer
tracer = GeminiTracer(lf)

# 4. Configure Gemini
import google.generativeai as genai

gemini_key = os.getenv("GEMINI_API_KEY")
if not gemini_key:
    print("Error: GEMINI_API_KEY is not set in your .env file.")
    sys.exit(1)

genai.configure(api_key=gemini_key)
model_name = "gemini-2.5-pro"
model = genai.GenerativeModel(model_name)

# ─────────────────────────────────────────────
# Helper: load image from disk
# ─────────────────────────────────────────────
SUPPORTED_MIME = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}

def load_image(image_path: str) -> dict:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    mime_type = SUPPORTED_MIME.get(path.suffix.lower())
    if not mime_type:
        raise ValueError(f"Unsupported format '{path.suffix}'. Supported: {list(SUPPORTED_MIME)}")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return {"inline_data": {"mime_type": mime_type, "data": data}}

# ─────────────────────────────────────────────
# Helper: print cost breakdown
# ─────────────────────────────────────────────
def print_cost_breakdown(usage: dict, model: str):
    print("\n" + "=" * 50)
    print("          COST BREAKDOWN")
    print("=" * 50)
    print(f"  Model         : {model}")
    print(f"  Input tokens  : {usage.get('input',  0):,}")
    print(f"  Output tokens : {usage.get('output', 0):,}")
    print(f"  Total tokens  : {usage.get('total',  0):,}")
    if usage.get("cachedTokens"):
        print(f"  Cached tokens : {usage.get('cachedTokens', 0):,}")
    print("-" * 50)
    print(f"  Input cost    : ${usage.get('inputCost',  0):.6f}")
    print(f"  Output cost   : ${usage.get('outputCost', 0):.6f}")
    print(f"  Total cost    : ${usage.get('totalCost',  0):.6f}")
    print("=" * 50 + "\n")

# ─────────────────────────────────────────────
# ✏️  Set your image paths here
# ─────────────────────────────────────────────
IMAGE_PATHS = [
    r"C:\Users\HR Zuneko Labs\Desktop\langfuse-custom-tracer\image1.jpeg", 
    r"C:\Users\HR Zuneko Labs\Desktop\langfuse-custom-tracer\image2.jpeg", 
    r"C:\Users\HR Zuneko Labs\Desktop\langfuse-custom-tracer\image3.jpeg", 
    r"C:\Users\HR Zuneko Labs\Desktop\langfuse-custom-tracer\image4.jpeg",   # e.g. an invoice
    # "image2.jpg", # add more as needed
]

prompt = "Extract all meaningful data from the provided image(s) and present it in a clean structured format."
print(f"Sending prompt with {len(IMAGE_PATHS)} image(s)...")

# Load images
image_parts = []
for idx, img_path in enumerate(IMAGE_PATHS, 1):
    try:
        image_parts.append(load_image(img_path))
        print(f"  ✓ Loaded image {idx}: {img_path}")
    except (FileNotFoundError, ValueError) as e:
        print(f"  ✗ Skipping: {e}")

if not image_parts:
    print("No valid images loaded. Exiting.")
    sys.exit(1)

# Build content: images first, then the prompt text
content_parts = image_parts + [prompt]

# 5. Trace + generation  (same pattern as the original template)
with tracer.trace("image-extraction", input={"prompt": prompt, "image_count": len(image_parts)}) as span:
    with tracer.generation("extract-image-data", model=model_name, input=prompt) as gen:
        response = model.generate_content(content_parts)
        usage = tracer.extract_usage(response, model=model_name)
        gen.update(output=response.text, usage_details=usage)
        print_cost_breakdown(usage, model_name)
    span.update(output="Image extraction completed")
tracer.flush()
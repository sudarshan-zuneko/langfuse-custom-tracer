"""
Example: PDF Bank Statement Extraction with Automatic Tracing (v1.0.0)

Upload a PDF bank statement, extract structured data using Gemini,
and get full observability in Langfuse — all with zero boilerplate.

Usage:
    python test_pdf_extraction.py path/to/bank_statement.pdf
    python test_pdf_extraction.py statement1.pdf statement2.pdf
"""

import os
import sys
import json
import base64
from pathlib import Path
from langfuse_custom_tracer import (
    load_env, create_langfuse_client, create_traced_client, GeminiTracer,
)

# ─────────────────────────────────────────────────────────────────────
# 1. Environment Setup
# ─────────────────────────────────────────────────────────────────────
if os.path.exists(".env"):
    load_env(".env")
elif os.path.exists("../.env"):
    load_env("../.env")

lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    base_url=os.getenv("LANGFUSE_BASE_URL"),
)

llm = create_traced_client(
    provider="gemini",
    api_key=os.getenv("GEMINI_API_KEY"),
    tracer=GeminiTracer(lf),
    model="gemini-2.5-flash",
)

# ─────────────────────────────────────────────────────────────────────
# 2. File loading helpers
# ─────────────────────────────────────────────────────────────────────
SUPPORTED_MIME = {
    ".pdf":  "application/pdf",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
    ".tiff": "image/tiff",
    ".bmp":  "image/bmp",
}


def load_file(file_path: str) -> dict:
    """Load a PDF or image file as a Gemini-compatible inline_data part."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_type = SUPPORTED_MIME.get(path.suffix.lower())
    if not mime_type:
        raise ValueError(
            f"Unsupported format '{path.suffix}'. "
            f"Supported: {list(SUPPORTED_MIME.keys())}"
        )

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Loaded: {path.name} ({size_mb:.1f} MB, {mime_type})")

    return {"inline_data": {"mime_type": mime_type, "data": data}}


# ─────────────────────────────────────────────────────────────────────
# 3. Extraction prompt
# ─────────────────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a bank statement data extraction expert.

Analyze the provided bank statement document(s) and extract ALL data into the following JSON structure:

{
  "bank_name": "Name of the bank",
  "branch": "Branch name if visible",
  "account_holder": "Account holder name",
  "account_number": "Account number (masked if partially visible)",
  "statement_period": {
    "from": "YYYY-MM-DD",
    "to": "YYYY-MM-DD"
  },
  "opening_balance": 0.00,
  "closing_balance": 0.00,
  "currency": "INR",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "Transaction description",
      "reference": "Reference/Cheque number if available",
      "type": "CREDIT or DEBIT",
      "amount": 0.00,
      "balance": 0.00
    }
  ],
  "summary": {
    "total_credits": 0.00,
    "total_debits": 0.00,
    "total_transactions": 0,
    "credit_count": 0,
    "debit_count": 0
  }
}

RULES:
1. Extract EVERY transaction — do not skip any rows.
2. Dates must be in YYYY-MM-DD format.
3. Amounts must be numeric (no commas, no currency symbols).
4. If a field is not available, use null.
5. Return ONLY valid JSON — no markdown, no explanation.
"""


# ─────────────────────────────────────────────────────────────────────
# 4. Cost breakdown printer
# ─────────────────────────────────────────────────────────────────────

def print_cost_breakdown(response):
    """Print a formatted cost report from the LLMResponse."""
    usage = response.usage
    print("\n" + "=" * 55)
    print("         📊 EXTRACTION REPORT")
    print("=" * 55)
    print(f"  Model          : {response.model}")
    print(f"  Provider       : {response.provider}")
    print(f"  Latency        : {response.latency_ms:,.0f} ms")
    print("-" * 55)
    print(f"  Input tokens   : {usage.get('input', 0):,}")
    print(f"  Output tokens  : {usage.get('output', 0):,}")
    print(f"  Total tokens   : {usage.get('total', 0):,}")
    if usage.get("cachedTokens"):
        print(f"  Cached tokens  : {usage.get('cachedTokens', 0):,}")
    print("-" * 55)
    print(f"  Input cost     : ${usage.get('inputCost',  0):.6f}")
    print(f"  Output cost    : ${usage.get('outputCost', 0):.6f}")
    print(f"  Total cost     : ${usage.get('totalCost',  0):.6f}")
    print("=" * 55)


# ─────────────────────────────────────────────────────────────────────
# 5. Main extraction logic
# ─────────────────────────────────────────────────────────────────────

def extract_from_files(file_paths: list[str]):
    """Extract structured data from PDF/image bank statements."""

    # Load all files
    print(f"\n📂 Loading {len(file_paths)} file(s)...")
    file_parts = []
    for path in file_paths:
        try:
            file_parts.append(load_file(path))
        except (FileNotFoundError, ValueError) as e:
            print(f"  ✗ Skipping: {e}")

    if not file_parts:
        print("\n❌ No valid files loaded. Exiting.")
        sys.exit(1)

    # Build content: files first, then the extraction prompt
    content_parts = file_parts + [EXTRACTION_PROMPT]

    # Call the LLM with automatic tracing
    print(f"\n🔄 Sending {len(file_parts)} file(s) to {llm.model}...")
    print("   (This may take a moment for large documents)\n")

    response = llm.generate(
        content_parts,
        trace_name="bank-statement-extraction",
        tags=["bank-statement", "pdf-extraction", "production"],
        metadata={
            "file_count": len(file_parts),
            "file_names": [Path(p).name for p in file_paths],
        },
    )

    # Print cost breakdown
    print_cost_breakdown(response)

    # Parse and display the structured output
    raw_text = response.text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    try:
        data = json.loads(raw_text)
        print("\n✅ Structured Data Extracted Successfully!\n")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Summary
        if "summary" in data:
            s = data["summary"]
            print(f"\n📋 Summary:")
            print(f"   Total transactions : {s.get('total_transactions', 'N/A')}")
            print(f"   Credits            : {s.get('credit_count', 'N/A')} "
                  f"(₹{s.get('total_credits', 0):,.2f})")
            print(f"   Debits             : {s.get('debit_count', 'N/A')} "
                  f"(₹{s.get('total_debits', 0):,.2f})")

        if "transactions" in data:
            print(f"   Rows extracted     : {len(data['transactions'])}")

        # Save to file
        output_file = "extracted_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved to: {output_file}")

    except json.JSONDecodeError:
        print("\n⚠️  Could not parse as JSON. Raw output:")
        print(raw_text[:3000])

    # Flush traces to Langfuse
    llm.flush()
    print("\n📡 Trace sent to Langfuse dashboard!")


# ─────────────────────────────────────────────────────────────────────
# 6. Entry point
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pdf_extraction.py <file1.pdf> [file2.pdf] ...")
        print("\nSupported formats: PDF, JPG, PNG, TIFF, BMP, GIF, WEBP")
        print("\nExample:")
        print("  python test_pdf_extraction.py bank_statement.pdf")
        print("  python test_pdf_extraction.py page1.jpg page2.jpg page3.jpg")
        sys.exit(1)

    extract_from_files(sys.argv[1:])

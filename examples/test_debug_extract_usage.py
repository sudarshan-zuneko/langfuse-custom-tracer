"""
Debug test for extract_usage methods without actual API calls.
This tests the Gemini and Anthropic tracer extract_usage methods.
"""

import os
import sys
from unittest.mock import Mock

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from langfuse_custom_tracer import load_env, create_langfuse_client
from langfuse_custom_tracer.tracers.gemini import GeminiTracer
from langfuse_custom_tracer.tracers.anthropic import AnthropicTracer

# Load environment
if os.path.exists(".env"):
    load_env(".env")
elif os.path.exists("../.env"):
    load_env("../.env")

# Create client
lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
)

print("\n" + "="*80)
print("TESTING GEMINI EXTRACT_USAGE")
print("="*80)

# Create a mock Gemini response
gemini_response = Mock()
gemini_response.usage_metadata = Mock()
gemini_response.usage_metadata.prompt_token_count = 20
gemini_response.usage_metadata.candidates_token_count = 100
gemini_response.usage_metadata.cached_content_token_count = 0
gemini_response.text = "Quantum computing is a revolutionary technology that leverages quantum mechanics to solve problems faster than classical computers."

print("\nMocked Gemini response:")
print(f"  prompt_token_count: {gemini_response.usage_metadata.prompt_token_count}")
print(f"  candidates_token_count: {gemini_response.usage_metadata.candidates_token_count}")
print(f"  cached_content_token_count: {gemini_response.usage_metadata.cached_content_token_count}")

gemini_tracer = GeminiTracer(lf)
print("\nCalling GeminiTracer.extract_usage():")
gemini_usage = gemini_tracer.extract_usage(gemini_response, model="gemini-1.5-flash")
print(f"\nFinal Gemini Usage Dictionary: {gemini_usage}")

print("\n" + "="*80)
print("TESTING ANTHROPIC EXTRACT_USAGE")
print("="*80)

# Create a mock Anthropic response
anthropic_response = Mock()
anthropic_response.usage = Mock()
anthropic_response.usage.input_tokens = 50
anthropic_response.usage.output_tokens = 150
anthropic_response.usage.cache_read_input_tokens = 0
anthropic_response.usage.cache_creation_input_tokens = 0
anthropic_response.content = [Mock(text="Claude's response about quantum computing...")]

print("\nMocked Anthropic response:")
print(f"  input_tokens: {anthropic_response.usage.input_tokens}")
print(f"  output_tokens: {anthropic_response.usage.output_tokens}")
print(f"  cache_read_input_tokens: {anthropic_response.usage.cache_read_input_tokens}")
print(f"  cache_creation_input_tokens: {anthropic_response.usage.cache_creation_input_tokens}")

anthropic_tracer = AnthropicTracer(lf)
print("\nCalling AnthropicTracer.extract_usage():")
anthropic_usage = anthropic_tracer.extract_usage(anthropic_response, model="claude-3-5-sonnet-20241022")
print(f"\nFinal Anthropic Usage Dictionary: {anthropic_usage}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nGemini Usage Summary:")
print(f"  Input Tokens: {gemini_usage.get('input')}")
print(f"  Output Tokens: {gemini_usage.get('output')}")
print(f"  Total Tokens: {gemini_usage.get('total')}")
print(f"  Input Cost: ${gemini_usage.get('inputCost')}")
print(f"  Output Cost: ${gemini_usage.get('outputCost')}")
print(f"  Total Cost: ${gemini_usage.get('totalCost')}")

print(f"\nAnthropic Usage Summary:")
print(f"  Input Tokens: {anthropic_usage.get('input')}")
print(f"  Output Tokens: {anthropic_usage.get('output')}")
print(f"  Total Tokens: {anthropic_usage.get('total')}")
print(f"  Input Cost: ${anthropic_usage.get('inputCost')}")
print(f"  Output Cost: ${anthropic_usage.get('outputCost')}")
print(f"  Total Cost: ${anthropic_usage.get('totalCost')}")

print("\n✓ Debug test completed successfully!")

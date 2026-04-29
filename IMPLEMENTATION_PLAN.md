# Implementation Plan: Resolving Zero Token/Cost and Verifying Features

## Project Goal
Ensure that the `langfuse-custom-tracer` library correctly captures and displays token usage and estimated costs for LLM calls (Gemini and Anthropic) in the Langfuse dashboard, along with all other planned features from `v3_automatic_tracing_docs.md`.

## Current Problem
Token usage and cost are showing as zero in the Langfuse dashboard, despite auto-tracing being enabled and models being updated. This indicates an issue with either token extraction, cost calculation, or data transmission to Langfuse.

## Phases of Implementation and Verification

### Phase 1: Verify `extract_usage` methods and LLM Response Structure

**Objective**: Confirm that raw LLM responses contain token information and that `extract_usage` methods in tracers correctly parse this data and calculate costs.

**Action Plan**:

1.  **Add Debug Logging to `GeminiTracer.extract_usage` (`langfuse_custom_tracer/tracers/gemini.py`)**:
    *   Insert `print` statements to log:
        *   The raw `response` object received.
        *   The `_um` (usage_metadata) extracted from the response.
        *   The values of `prompt_tokens`, `completion_tokens`, and `cached_tokens`.
        *   The `pricing` dictionary obtained from `pricing_manager`.
        *   The calculated `input_cost`, `output_cost`, `cache_cost`, and `total_cost`.
        *   The final `usage` dictionary being returned.

2.  **Add Debug Logging to `AnthropicTracer.extract_usage` (`langfuse_custom_tracer/tracers/anthropic.py`)**:
    *   Insert `print` statements to log:
        *   The raw `response` object.
        *   The `usage_data` extracted.
        *   The values of `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`.
        *   The `pricing` dictionary.
        *   The calculated costs and the final `usage` dictionary.

3.  **Run Sample Demo (`examples/simple_gemini_trace.py`)**:
    *   Execute the `simple_gemini_trace.py` script.
    *   Capture the *full* terminal output, including all debug statements.

4.  **Analyze Debug Output (Internal)**:
    *   Examine the terminal output to identify:
        *   If Gemini's `response.usage_metadata` (or Anthropic's `response.usage`) contains valid token counts.
        *   If `prompt_tokens`, `completion_tokens`, etc., are non-zero when expected.
        *   If `pricing_manager.get_price()` returns non-zero costs for the specific model.
        *   If `input_cost`, `output_cost`, `total_cost` are calculated correctly (non-zero).
        *   If the final `usage` dictionary contains `input`, `output`, `inputCost`, `outputCost`, `totalCost` with correct, non-zero values.

### Phase 2: Verify `auto.py` Integration with `obs.update()`

**Objective**: Confirm that the `usage` dictionary from `extract_usage` is correctly passed to and processed by `obs.update()` in `auto.py`.

**Action Plan**:

1.  **Add Debug Logging to `_build_wrapper` (`langfuse_custom_tracer/auto.py`)**:
    *   In the `wrapper` function, specifically in the `try` block before `obs.update()`, insert `print` statements to log:
        *   The `usage` dictionary returned by `tracer.extract_usage`.
        *   The `output` (response text) being passed to `obs.update()`.

2.  **Run Sample Demo (`examples/simple_gemini_trace.py`)**:
    *   Execute the `simple_gemini_trace.py` script.
    *   Capture the *full* terminal output.

3.  **Analyze Debug Output (Internal)**:
    *   Verify if the `usage` dictionary passed to `obs.update()` contains the correct token and cost values.
    *   Confirm that `obs.update()` is correctly receiving `usage_details`.

### Phase 3: Implement Fixes Based on Analysis

**Objective**: Apply necessary code changes to resolve any identified issues in token extraction, cost calculation, or integration with `obs.update()`.

**Action Plan**:

1.  **Refine `extract_usage` (if needed)**:
    *   If token counts are incorrect, adjust `_get_val` logic or the way `usage_metadata`/`usage` is accessed.
    *   If cost calculation is flawed, correct the arithmetic in `extract_usage`.

2.  **Ensure `_pricing_source` and `_pricing_version` are present**:
    *   If `KeyError: 'pricing_source'` occurs in tests or debug, ensure `_pricing_source` and `_pricing_version` are always added to the `usage` dictionary in `extract_usage` for both tracers.

3.  **Adjust `auto.py`'s `obs.update()` (if needed)**:
    *   Ensure `obs.update()` correctly maps the `usage` dictionary to `usage_details` (or similar field as per Langfuse SDK v4 requirements).

4.  **Remove Debug Logs**: Once issues are resolved, remove all debug `print` statements from the codebase.

### Phase 4: Full Automated Test Verification

**Objective**: Ensure all automated tests pass, confirming the stability and correctness of all features, including token/cost tracking.

**Action Plan**:

1.  **Run All Tests**:
    *   Execute `py -m pytest` from the project root.
    *   Analyze the test report for any failures.

2.  **Address Test Failures**:
    *   For any remaining failures, analyze their root cause (e.g., outdated test assertions, new bugs introduced) and apply targeted fixes. This includes:
        *   **Anthropic Pricing Tests**: Ensure `test_anthropic_tracer.py` uses `pricing_manager.get_price()` correctly and has up-to-date model pricing.
        *   **Gemini Pricing Tests**: Verify `test_gemini_tracer.py`'s `SAMPLE_PRICING` and assertions match the expected `gemini-3-flash-preview` pricing and `pricing_manager`'s behavior.
        *   **`test_auto_patch.py`**: Ensure client initialization and scoring mocks are correct, and all assertions are valid for auto-tracing behavior.
        *   **`TracedLLMClient` properties and methods**: Verify `model`, `provider`, and `_dispatch` logic.
        *   **`LLMResponse.__repr__`**: Confirm it includes `latency_ms`.

### Phase 5: Final Manual Verification in Langfuse Dashboard

**Objective**: Confirm that a live LLM call using the library results in correct token usage and cost display in the Langfuse dashboard.

**Action Plan**:

1.  **Run Demo Scripts**:
    *   Execute `examples/simple_gemini_trace.py`.
    *   Execute `examples/test_pypi_trace.py`.
    *   Optionally, execute `examples/auto_trace_demo.py` (after verifying Anthropic API key).

2.  **Check Langfuse Dashboard**:
    *   For each trace, confirm:
        *   `inputTokens`, `outputTokens`, `totalTokens` are non-zero and correct.
        *   `inputCost`, `outputCost`, `totalCost` are non-zero and correct.
        *   Scores are attached and visible.
        *   User and session IDs are correctly populated.

### Deliverables
*   Fully functional `langfuse-custom-tracer` library.
*   Accurate token usage and cost tracking in the Langfuse dashboard.
*   All automated tests passing.
*   Demonstration scripts (`simple_gemini_trace.py`, `test_pypi_trace.py`, `auto_trace_demo.py`) successfully running and sending complete data to Langfuse.

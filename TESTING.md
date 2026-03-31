# Testing Guide

Comprehensive unit tests for langfuse-custom-tracer. All core functionality is tested with mocking to avoid needing actual API keys.

## Test Coverage

### ✅ BaseTracer (15 tests)
- **Context managers**: `trace()`, `generation()`
- **Parameters**: input, metadata, user_id, session_id, tags
- **Error handling**: With/without client, exception handling
- **Integration**: trace() and generation() nesting

**File**: `tests/test_base_tracer.py`

### ✅ GeminiTracer (20 tests)
- **Pricing lookup**: Exact match, case-insensitive, partial match, fallback
- **Token usage extraction**: With/without cached tokens
- **Cost calculation**: Input cost, output cost, cache cost, total cost
- **Model variations**: Different Gemini models (2.5-pro, 2.0-flash, etc.)
- **Edge cases**: High token counts, missing fields, None values

**File**: `tests/test_gemini_tracer.py`

### ✅ Client Setup (18 tests)
- **create_langfuse_client()**: Basic creation, env var initialization
- **load_env()**: .env file loading, custom paths
- **Environment variables**: Setting, overriding, persistence
- **Error handling**: Missing imports, non-existent files
- **Integration**: load_env() + create_langfuse_client() workflow

**File**: `tests/test_client.py`

**Total**: 53 unit tests

## Setup

### Install Test Dependencies

```bash
# Install dev dependencies
pip install -e ".[dev]"

# OR install just what you need
pip install pytest>=8.0 pytest-cov>=4.0 pytest-timeout>=2.1
```

## Running Tests

### Run All Tests

```bash
pytest
```

With verbose output:
```bash
pytest -v
```

### Run Single Test File

```bash
pytest tests/test_gemini_tracer.py
```

### Run Single Test Class

```bash
pytest tests/test_gemini_tracer.py::TestGeminiTracer
```

### Run Single Test

```bash
pytest tests/test_gemini_tracer.py::TestGeminiTracer::test_extract_usage_basic -v
```

### Run with Coverage Report

```bash
pytest --cov=langfuse_custom_tracer --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Run Tests Using Python Script

```bash
# All tests
python run_tests.py all

# Unit tests only
python run_tests.py unit

# With coverage
python run_tests.py coverage

# Specific test
python run_tests.py tests/test_gemini_tracer.py
```

## Test Fixtures

All tests use mocks to avoid needing actual API credentials. Key fixtures in `conftest.py`:

- **`mock_langfuse_client`**: Mock Langfuse v4 client
- **`gemini_response_with_usage`**: Mock Gemini response with token usage
- **`gemini_response_without_usage`**: Gemini response without usage data
- **`env_file`**: Temporary .env file for testing
- **`clean_env`**: Auto-cleans environment variables between tests

## What's Tested

### ✅ BaseTracer
- Context manager functionality (trace, generation)
- All optional parameters (input, metadata, user_id, session_id, tags)
- Error handling and graceful fallbacks
- Flush mechanism

### ✅ GeminiTracer
- All Gemini pricing tiers (6 models)
- Accurate token counting
- Cost calculations for:
  - Regular tokens
  - Cached tokens (with discount)
  - Total costs
- Handling of missing/None values
- High token counts (stress test)

### ✅ Client Setup
- Environment variable management
- .env file loading with python-dotenv
- Client initialization
- Custom host/endpoint configuration

## What's NOT Tested (Integration)

These require actual API keys and are excluded from unit tests:

- Actual Langfuse API communication
- Actual Gemini API calls
- Actual .env file generation
- Live streaming to Langfuse

*Integration tests would be added later*

## Test Output Example

```
tests/test_base_tracer.py::TestBaseTracer::test_init PASSED                       [  1%]
tests/test_base_tracer.py::TestBaseTracer::test_init_with_none PASSED             [  2%]
tests/test_base_tracer.py::TestBaseTracer::test_trace_context_manager PASSED      [  3%]
...
tests/test_gemini_tracer.py::TestGeminiTracer::test_extract_usage_basic PASSED    [45%]
tests/test_gemini_tracer.py::TestGeminiTracer::test_extract_usage_cost_calculation PASSED [46%]
...
tests/test_client.py::TestCreateLangfuseClient::test_basic_client_creation PASSED [80%]
...

========================= 53 passed in 2.34s =========================
```

## Debugging Tests

### Run with print output

```bash
pytest -v -s
```

The `-s` flag shows print statements.

### Run with detailed traceback

```bash
pytest -v --tb=long
```

### Stop on first failure

```bash
pytest -x
```

## Coverage Report

After running tests with coverage:

```bash
pytest --cov=langfuse_custom_tracer --cov-report=term-missing
```

Shows which lines are not covered by tests.

## Best Practices

1. **Run tests before committing**
   ```bash
   pytest && git commit
   ```

2. **Always check coverage**
   ```bash
   pytest --cov
   ```

3. **Run specific tests while developing**
   ```bash
   pytest tests/test_gemini_tracer.py::TestGeminiTracer -v
   ```

4. **Use fixtures for clean state**
   - All tests automatically get clean environment
   - Mocks prevent external API calls

## Troubleshooting

### Tests fail with "ImportError: No module named 'langfuse'"

Install the package in development mode:
```bash
pip install -e .
```

### Tests fail with "ModuleNotFoundError: No module named 'pytest'"

Install test dependencies:
```bash
pip install -e ".[dev]"
```

### Coverage is incomplete

Some lines are excluded from coverage (mocking, error paths):
```bash
pytest --cov --cov-report=html  # View detailed report
```

## Next Steps

After implementing remaining LLM tracers (Ollama, Groq, Azure, Anthropic), add tests:

```python
# tests/test_ollama_tracer.py
class TestOllamaTracer:
    def test_extract_usage(self): ...

# tests/test_groq_tracer.py  
class TestGroqTracer:
    def test_extract_usage(self): ...
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -e ".[dev]"
      - run: pytest --cov
```


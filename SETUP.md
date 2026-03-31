# API Keys & Configuration Guide

## Setup

### 1. Install Dependencies

To use .env file support, install with the `env` extra:

```bash
pip install langfuse-custom-tracer[env]
```

Or for all features including LLM providers:

```bash
pip install langfuse-custom-tracer[all]
```

### 2. Configure Environment Variables

#### Option A: If you don't have a `.env` file yet

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Then edit `.env` with your credentials:

```env
# Langfuse (get from https://cloud.langfuse.com)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Gemini API (get from https://ai.google.dev)
GEMINI_API_KEY=your-api-key-here

# Other LLM providers (optional)
OLLAMA_API_KEY=
GROQ_API_KEY=
AZURE_OPENAI_KEY=
ANTHROPIC_API_KEY=
```

#### Option B: If you already have a `.env` file

Simply **add these variables to your existing `.env` file**:

```env
# Langfuse Configuration
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# LLM Provider Keys
GEMINI_API_KEY=your-api-key-here
# OLLAMA_API_KEY=
# GROQ_API_KEY=
# AZURE_OPENAI_KEY=
# ANTHROPIC_API_KEY=
```

You only need to add the values you plan to use. Comment out or remove the ones you don't need.

### 3. Load and Use

```python
import os
from langfuse_custom_tracer import load_env, create_langfuse_client, GeminiTracer

# Load from .env file
load_env()

# Create client from environment variables
lf = create_langfuse_client(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
)

# Create tracer
tracer = GeminiTracer(lf)
```

## Security Notes

⚠️ **Important:**
- `.env` files should **never** be committed to git
- `.gitignore` already excludes `.env` files
- Use `.env.example` for sharing template configurations
- For production, use environment variables or secret management services (AWS Secrets Manager, Vault, etc.)

## Environment Variables Reference

### Langfuse

| Variable | Required | Example |
|----------|----------|---------|
| `LANGFUSE_SECRET_KEY` | Yes | `sk-lf-...` |
| `LANGFUSE_PUBLIC_KEY` | Yes | `pk-lf-...` |
| `LANGFUSE_BASE_URL` | No | `https://cloud.langfuse.com` |

Default Langfuse URL is EU cloud. Use `https://us.cloud.langfuse.com` for US cloud.

### LLM Provider Keys

| Provider | Variable | Get From |
|----------|----------|----------|
| Gemini | `GEMINI_API_KEY` | https://ai.google.dev |
| Groq | `GROQ_API_KEY` | https://console.groq.com |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| Azure OpenAI | `AZURE_OPENAI_KEY` | https://portal.azure.com |
| Ollama | `OLLAMA_API_KEY` | Local (usually not needed) |

## Examples

See [examples/env_setup_example.py](examples/env_setup_example.py) for more usage patterns.

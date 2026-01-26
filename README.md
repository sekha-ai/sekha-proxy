# Sekha Proxy

> **Transparent LLM Proxy with Automatic Context Injection - OPTIONAL Component**

[![CI](https://github.com/sekha-ai/sekha-proxy/workflows/CI/badge.svg)](https://github.com/sekha-ai/sekha-proxy/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sekha-ai/sekha-proxy/branch/main/graph/badge.svg)](https://codecov.io/gh/sekha-ai/sekha-proxy)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/orgs/sekha-ai/packages?repo_name=sekha-proxy)

---

## 🎯 What is Sekha Proxy?

**Sekha Proxy is an OPTIONAL component** that sits transparently between your LLM client and the actual LLM. It automatically:

1. **Intercepts** your chat requests
2. **Injects** relevant context from past conversations (via Controller)
3. **Forwards** to your chosen LLM (Ollama, GPT-4, Claude, etc.)
4. **Stores** the full conversation for future recall
5. **Returns** the response with metadata about context used

**Think of it as:** A smart middleman that gives your LLM perfect memory without changing your application code.

---

## ❓ Do You Need the Proxy?

### ❌ You DON'T Need Proxy If:

- Using **Claude Desktop** (has MCP tools built-in)
- Building custom integrations (can call Controller API directly)
- Using AI provider SDKs that integrate with Sekha directly
- Want programmatic control over when/how to store conversations

### ✅ You NEED Proxy If:

- Using generic LLM clients (curl, Postman, UI apps expecting OpenAI API)
- Want **zero-config** conversation capture
- Don't want to modify your existing application code
- Need a drop-in replacement for OpenAI API endpoint
- Want the **Web UI** for configuration and monitoring

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────┐
│  Your LLM Client                         │
│  (curl, ChatGPT clone, custom app)       │
│  Points to: http://localhost:8081        │
└─────────────────┬────────────────────────┘
                  │ POST /v1/chat/completions
                  ▼
┌──────────────────────────────────────────┐
│  Sekha Proxy (Port 8081) ← YOU ARE HERE  │
│  • Intercepts request                    │
│  • Gets context from Controller          │
│  • Injects context into messages         │
│  • Forwards to LLM                       │
│  • Stores conversation                   │
└────────────────┬─────────────────────────┘
                 │
     ┌───────────┼───────────┐
     │           │           │
     ▼           ▼           ▼
┌────────┐  ┌────────┐  ┌──────────┐
│ Ctrlr  │  │ Bridge │  │ Ctrlr    │
│Context │  │ → LLM  │  │ Store    │
└────────┘  └────────┘  └──────────┘
```

**Request Flow:**
1. Client: "What did we discuss about Python?"
2. Proxy → Controller: GET /api/v1/context/assemble?query="Python"
3. Controller returns: Past conversations about Python
4. Proxy injects context as system message
5. Proxy → LLM-Bridge → Actual LLM (GPT-4, Claude, Ollama, etc.)
6. LLM response returned to client
7. Proxy → Controller: POST /api/v1/conversations (store for future)

---

## ✨ Features

### Core Capabilities

- ✅ **OpenAI-Compatible**: Drop-in replacement for OpenAI API
- ✅ **Automatic Context Injection**: Past conversations inserted transparently
- ✅ **Multi-LLM Support**: Works with any LLM via LLM-Bridge
- ✅ **Web UI**: Configuration dashboard at `/static/index.html`
- ✅ **Zero Code Changes**: Point your client to proxy, that's it!
- ✅ **Metadata Responses**: Returns `sekha_metadata` showing context used
- ✅ **Smart Filtering**: Exclude folders, prefer labels, token budgets

### Web UI Features

- View recent conversations
- Configure context injection settings
- Monitor LLM usage
- Health status dashboard
- Manual conversation labeling

---

## 🚀 Quick Start

### With Docker (Full Stack)

```bash
git clone https://github.com/sekha-ai/sekha-docker.git
cd sekha-docker/docker
cp .env.example .env

# Edit proxy settings
nano .env
# Set:
# PROXY_PORT=8081
# AUTO_INJECT_CONTEXT=true
# CONTEXT_BUDGET=4000

docker compose -f docker-compose.prod.yml up -d

# Access Web UI
open http://localhost:8081
```

### Standalone Development

```bash
# Clone
git clone https://github.com/sekha-ai/sekha-proxy.git
cd sekha-proxy

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env

# Run (requires Controller + LLM-Bridge running)
python proxy.py
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Proxy Settings
PROXY_HOST=0.0.0.0
PROXY_PORT=8081

# Controller Connection
CONTROLLER_URL=http://localhost:8080
CONTROLLER_API_KEY=your-api-key
CONTROLLER_TIMEOUT=30

# LLM Connection
LLM_PROVIDER=bridge              # bridge | openai | anthropic
LLM_URL=http://localhost:5001    # LLM-Bridge endpoint
LLM_MODEL=llama3.1:8b            # Default model
LLM_TIMEOUT=120

# Memory Settings
MEMORY_AUTO_INJECT_CONTEXT=true
MEMORY_DEFAULT_FOLDER=/work
MEMORY_CONTEXT_TOKEN_BUDGET=4000
MEMORY_PREFERRED_LABELS=          # Comma-separated
MEMORY_EXCLUDED_FOLDERS=/tmp      # Comma-separated
```

### Advanced Configuration

**Context Injection Options:**
```bash
# Disable context injection (just storage)
MEMORY_AUTO_INJECT_CONTEXT=false

# Increase context budget for more history
MEMORY_CONTEXT_TOKEN_BUDGET=8000

# Prioritize specific labels
MEMORY_PREFERRED_LABELS=work,python,important

# Exclude personal folders
MEMORY_EXCLUDED_FOLDERS=/personal,/drafts
```

**Multi-LLM Setup:**
```bash
# Use OpenAI directly (bypassing Bridge)
LLM_PROVIDER=openai
LLM_URL=https://api.openai.com
OPENAI_API_KEY=sk-...

# Use Anthropic directly
LLM_PROVIDER=anthropic
LLM_URL=https://api.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 📡 API Reference

### POST /v1/chat/completions

OpenAI-compatible chat endpoint with Sekha enhancements.

**Request:**
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "What did we discuss about Python?"}
  ],
  
  // Sekha-specific (optional)
  "folder": "/work/projects",
  "context_budget": 4000,
  "excluded_folders": ["/personal"]
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "gpt-4",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Based on our previous discussion..."
      },
      "finish_reason": "stop"
    }
  ],
  
  // Sekha metadata (added by proxy)
  "sekha_metadata": {
    "context_used": [
      {"label": "Python Best Practices", "folder": "/work"},
      {"label": "Type Hints Discussion", "folder": "/work"}
    ],
    "context_count": 2
  }
}
```

### GET /health

Health status of proxy and dependencies.

**Response:**
```json
{
  "status": "healthy",
  "proxy": {"version": "1.0.0"},
  "controller": {"status": "healthy", "url": "http://localhost:8080"},
  "llm": {"status": "healthy", "provider": "bridge"}
}
```

### GET /api/info

Proxy configuration and stats.

**Response:**
```json
{
  "name": "Sekha Proxy",
  "version": "1.0.0",
  "config": {
    "llm_provider": "bridge",
    "auto_inject_context": true,
    "context_budget": 4000
  }
}
```

---

## 🔧 Usage Examples

### cURL

```bash
curl http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Python (OpenAI SDK)

```python
import openai

# Point to proxy instead of OpenAI
openai.api_base = "http://localhost:8081/v1"

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's in my memory?"}]
)

print(response.choices[0].message.content)
# Automatically includes context from past conversations!
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://localhost:8081/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    model: 'gpt-4',
    messages: [{role: 'user', content: 'Hello!'}],
    folder: '/work/project-x'  // Sekha-specific
  })
});

const data = await response.json();
console.log(data.sekha_metadata); // See what context was used
```

### Custom App Integration

```python
# Just change the base URL - everything else stays the same!
import requests

BASE_URL = "http://localhost:8081"  # Was: https://api.openai.com

response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    json={
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Recap our discussion"}]
    }
)

result = response.json()
print(f"Response: {result['choices'][0]['message']['content']}")
print(f"Context used: {len(result.get('sekha_metadata', {}).get('context_used', []))} items")
```

---

## 📊 Monitoring & Debugging

### Web UI Dashboard

Access at `http://localhost:8081/static/index.html`

**Features:**
- Recent conversations list
- Context injection stats
- LLM provider status
- Configuration editor
- Health monitoring

### Logs

```bash
# View proxy logs
docker logs -f sekha-proxy

# Standalone
tail -f proxy.log
```

**Log levels:**
```bash
LOG_LEVEL=DEBUG  # Verbose
LOG_LEVEL=INFO   # Normal (default)
LOG_LEVEL=WARN   # Errors only
```

---

## 🔒 Security

### API Key Protection

```bash
# Require API key for proxy access
PROXY_API_KEY=your-secret-key
```

Clients must include:
```bash
curl -H "Authorization: Bearer your-secret-key" \
  http://localhost:8081/v1/chat/completions ...
```

### HTTPS/TLS

```bash
# Enable TLS
PROXY_TLS_CERT=/path/to/cert.pem
PROXY_TLS_KEY=/path/to/key.pem
```

---

## 🤝 Integration Patterns

### Pattern 1: Transparent Proxy (No Code Changes)

**Before:**
```python
openai.api_base = "https://api.openai.com"
```

**After:**
```python
openai.api_base = "http://localhost:8081"  # That's it!
```

### Pattern 2: Selective Context Injection

```python
# Only inject context for specific conversations
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[...],
    folder="/work",              # Only search in /work
    context_budget=8000,         # More context
    preferred_labels=["python"]  # Prefer Python discussions
)
```

### Pattern 3: Disable Injection (Just Storage)

```bash
# In .env
MEMORY_AUTO_INJECT_CONTEXT=false
```

Proxy will still **store** conversations but won't inject context.
Use this when you want to build your own context retrieval logic.

---

## 🔧 Development

### Setup

```bash
# Clone
git clone https://github.com/sekha-ai/sekha-proxy.git
cd sekha-proxy

# Install dev dependencies
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Type checking
mypy .

# Linting
ruff check .
black --check .
```

### Project Structure

```
sekha-proxy/
├── proxy.py              # Main FastAPI app
├── config.py             # Configuration
├── context_injection.py  # Context injection logic
├── health.py             # Health monitoring
├── static/               # Web UI
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── tests/
├── requirements.txt
└── pyproject.toml
```

---

## 📚 Documentation

**Full docs:** [docs.sekha.dev](https://docs.sekha.dev)

- [Architecture Overview](https://docs.sekha.dev/architecture/overview/)
- [Proxy Configuration](https://docs.sekha.dev/configuration/proxy/)
- [Web UI Guide](https://docs.sekha.dev/guides/web-ui/)
- [Deployment](https://docs.sekha.dev/deployment/)

---

## 🔗 Related Projects

- **[sekha-controller](https://github.com/sekha-ai/sekha-controller)** - Memory orchestration (Rust)
- **[sekha-llm-bridge](https://github.com/sekha-ai/sekha-llm-bridge)** - Universal LLM adapter (required)
- **[sekha-mcp](https://github.com/sekha-ai/sekha-mcp)** - MCP server for Claude Desktop
- **[sekha-docker](https://github.com/sekha-ai/sekha-docker)** - Full stack deployment

---

## 📄 License

AGPL-3.0 - Free for personal and educational use.

Commercial license available: [hello@sekha.dev](mailto:hello@sekha.dev)

**[View License Details](LICENSE)**

---

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/sekha-ai/sekha-proxy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sekha-ai/sekha-controller/discussions)
- **Email**: [dev@sekha.dev](mailto:dev@sekha.dev)

---

**Built with ❤️ by the Sekha team**

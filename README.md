# Sekha Proxy

> **Intelligent LLM routing with automatic context injection**

Sekha Proxy sits between your application and any LLM (Ollama, OpenAI, Anthropic, etc.), automatically injecting relevant conversation history for perfect memory continuity.

## Features

- 🧠 **Automatic Context Injection** - AI remembers past conversations without manual prompting
- 🔌 **LLM Agnostic** - Works with Ollama, OpenAI, Anthropic, Google, Cohere, and more
- 🎯 **Zero Latency Impact** - Async storage, context retrieval optimized (<10ms overhead)
- 🔒 **Privacy First** - Exclude sensitive folders from AI context
- 📊 **OpenAI Compatible** - Drop-in replacement for `/v1/chat/completions`
- 🏗️ **Production Ready** - Docker deployment, health checks, proper logging

## How It Works

```
User → Sekha Proxy → LLM → Response
          ↓              ↑
    Context Retrieval    Enhanced Prompt
          ↓
    Sekha Controller
    (stores conversations)
```

1. **Receive** user's chat request
2. **Search** controller for relevant past conversations
3. **Inject** context into system prompt (invisible to user)
4. **Forward** to LLM with full historical context
5. **Store** conversation for future use (async)

## Quick Start

### Prerequisites

- Python 3.11+
- [Sekha Controller](https://github.com/sekha-ai/sekha-controller) running
- LLM (Ollama, OpenAI API key, etc.)

### Installation

```bash
# Clone repository
git clone https://github.com/sekha-ai/sekha-proxy.git
cd sekha-proxy

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Edit configuration

# Run proxy
python proxy.py
```

### Configuration

Edit `.env`:

```bash
# Required
CONTROLLER_URL=http://localhost:8080
CONTROLLER_API_KEY=sk-sekha-your-key-here

# LLM Settings
LLM_PROVIDER=ollama
LLM_URL=http://localhost:11434

# Memory Settings
AUTO_INJECT_CONTEXT=true
CONTEXT_TOKEN_BUDGET=2000
EXCLUDED_FOLDERS=/personal/private
```

### Docker Deployment

```bash
# Build
docker build -t sekha-proxy .

# Run
docker run -p 8081:8081 \
  -e CONTROLLER_URL=http://controller:8080 \
  -e CONTROLLER_API_KEY=sk-sekha-key \
  -e LLM_URL=http://ollama:11434 \
  sekha-proxy
```

## Usage

### Point Your App at Proxy

Instead of:
```python
client = OpenAI(base_url="http://localhost:11434")
```

Use:
```python
client = OpenAI(base_url="http://localhost:8081")
```

### Example: Multi-Session Continuity

**Session 1 (Monday):**
```python
response = client.chat.completions.create(
    model="llama3",
    messages=[{"role": "user", "content": "I'm using Rust with SQLite"}]
)
# Sekha stores this conversation
```

**Session 2 (Tuesday, different app/LLM):**
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What database am I using?"}]
)
# Response: "You're using SQLite with Rust..."
# AI automatically retrieved context from Session 1!
```

### Privacy: Exclude Folders

```bash
# In .env
EXCLUDED_FOLDERS=/personal/medical,/work/confidential
```

Conversations in these folders won't be used for AI context.

## API Endpoints

### `POST /v1/chat/completions`

OpenAI-compatible chat endpoint with automatic context injection.

**Request:**
```json
{
  "model": "llama3",
  "messages": [
    {"role": "user", "content": "What did we discuss yesterday?"}
  ]
}
```

**Response:**
```json
{
  "choices": [...],
  "sekha_metadata": {
    "context_used": [
      {"label": "Database discussion", "folder": "/work/projects"}
    ],
    "context_count": 2
  }
}
```

### `GET /health`

Health check for proxy, controller, and LLM.

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "controller": {"status": "ok", "url": "http://localhost:8080"},
    "llm": {"status": "ok", "url": "http://localhost:11434"},
    "proxy": {"status": "ok"}
  }
}
```

### `GET /`

Proxy information and configuration.

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_HOST` | `0.0.0.0` | Proxy bind address |
| `PROXY_PORT` | `8081` | Proxy port |
| `LLM_PROVIDER` | `ollama` | LLM provider (ollama/openai/anthropic/google/cohere) |
| `LLM_URL` | `http://localhost:11434` | LLM endpoint |
| `LLM_API_KEY` | - | API key for cloud LLMs |
| `LLM_TIMEOUT` | `120` | LLM request timeout (seconds) |
| `CONTROLLER_URL` | `http://localhost:8080` | Sekha Controller URL |
| `CONTROLLER_API_KEY` | **required** | Controller API key |
| `AUTO_INJECT_CONTEXT` | `true` | Enable automatic context injection |
| `CONTEXT_TOKEN_BUDGET` | `2000` | Max tokens for context |
| `CONTEXT_LIMIT` | `5` | Max conversations to retrieve |
| `DEFAULT_FOLDER` | `/auto-captured` | Default folder for conversations |
| `EXCLUDED_FOLDERS` | - | Folders to exclude (comma-separated) |

## Architecture

Sekha Proxy is a **thin routing layer** that leverages Sekha Controller's intelligence:

- **Context Assembly**: Controller's 4-phase algorithm (Recall → Rank → Assemble → Enhance)
- **Scoring**: Importance + recency + label matching
- **Storage**: SQLite (structured) + ChromaDB (semantic)
- **Summarization**: Hierarchical summaries for long histories

Proxy responsibilities:
1. Extract user query
2. Call `/api/v1/context/assemble`
3. Inject context into prompt
4. Forward to LLM
5. Store response

## Performance

- **Latency**: <10ms overhead vs direct LLM call
- **Context Retrieval**: <100ms for 1M+ messages
- **Storage**: Async, non-blocking
- **Throughput**: Handles 100+ req/s on modest hardware

## Development

### Running Tests

```bash
pip install pytest pytest-asyncio pytest-cov
pytest tests/ -v --cov
```

### Project Structure

```
sekha-proxy/
├── proxy.py              # Main FastAPI server
├── config.py             # Configuration management
├── context_injection.py  # Context formatting
├── health.py             # Health monitoring
├── requirements.txt      # Dependencies
├── Dockerfile            # Container image
├── docker-compose.yml    # Full stack deployment
└── tests/                # Test suite
```

## Troubleshooting

### Proxy Won't Start

```bash
# Check configuration
python -c "from config import Config; c = Config.from_env(); c.validate()"

# Check controller connectivity
curl http://localhost:8080/health
```

### Context Not Injecting

1. Check `AUTO_INJECT_CONTEXT=true` in `.env`
2. Verify controller has conversations: `curl http://localhost:8080/api/v1/conversations`
3. Check proxy logs for context retrieval errors

### LLM Errors

```bash
# Test LLM directly
curl http://localhost:11434/api/tags  # Ollama
curl https://api.openai.com/v1/models -H "Authorization: Bearer $LLM_API_KEY"  # OpenAI
```

## License

AGPL-3.0-or-later

## Links

- **Homepage**: [sekha.dev](https://sekha.dev)
- **Controller**: [github.com/sekha-ai/sekha-controller](https://github.com/sekha-ai/sekha-controller)
- **Documentation**: [docs.sekha.dev](https://docs.sekha.dev)
- **Issues**: [github.com/sekha-ai/sekha-proxy/issues](https://github.com/sekha-ai/sekha-proxy/issues)

---

**Built with 💙 by the Sekha team**

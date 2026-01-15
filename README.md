[![CI Status](https://github.com/sekha-ai/sekha-proxy/workflows/CI/badge.svg)](https://github.com/sekha-ai/sekha-proxy/actions)
[![codecov](https://codecov.io/gh/sekha-ai/sekha-proxy/branch/main/graph/badge.svg)](https://codecov.io/gh/sekha-ai/sekha-proxy)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

# Sekha Proxy

> **Intelligent LLM routing with automatic context injection and persistent memory**

Sekha Proxy sits between your application and any LLM (Ollama, OpenAI, Anthropic, etc.), automatically injecting relevant conversation history for perfect memory continuity.

## 🚀 Quick Start (One Command)

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

Then open **http://localhost:8081** in your browser! 🎉

---

## Features

- 🧠 **Automatic Context Injection** - AI remembers past conversations without manual prompting
- 🔒 **Privacy Controls** - Exclude sensitive folders from AI context (e.g., `/personal`, `/private`)
- 🎨 **Web UI** - Beautiful chat interface with privacy controls built-in
- 🔌 **LLM Agnostic** - Works with Ollama, OpenAI, Anthropic, Google, Cohere, and more
- 🎯 **Zero Latency Impact** - Async storage, context retrieval optimized (<10ms overhead)
- 📊 **OpenAI Compatible** - Drop-in replacement for `/v1/chat/completions`
- 🏗️ **Production Ready** - Docker deployment, health checks, proper logging

## How It Works

```
User/App → Sekha Proxy → LLM → Response
              │          ↑
              │    Enhanced Prompt
              ↓          with Context
          Context 
          Retrieval
              ↓
        Sekha Controller
        (4-Phase Assembly)
              ↓
        SQLite + ChromaDB
```

1. **Receive** user's chat request
2. **Search** controller for relevant past conversations
3. **Filter** out excluded folders (privacy)
4. **Inject** context into system prompt (invisible to user)
5. **Forward** to LLM with full historical context
6. **Store** conversation for future use (async)

## Web UI

Access the beautiful web interface at **http://localhost:8081**:

- 💬 **Chat Interface** - Intuitive conversation UI
- 📁 **Folder Organization** - Organize conversations by project/topic
- 🚫 **Privacy Controls** - Exclude folders from context in real-time
- 🎯 **Context Budget** - Control how much history to include
- 🚀 **Live Updates** - See context injection in action

## Full Stack Deployment (Docker Compose)

Deploy the complete Sekha stack with one command:

```bash
# Clone repositories
git clone https://github.com/sekha-ai/sekha-controller.git
git clone https://github.com/sekha-ai/sekha-proxy.git

# Start all services
cd sekha-proxy
export CONTROLLER_API_KEY="your-secure-key"
docker-compose up -d

# Pull Ollama model
docker exec sekha-proxy-ollama-1 ollama pull llama2

# Access UI
open http://localhost:8081
```

This starts:
- **Sekha Proxy** (Python) - Port 8081
- **Sekha Controller** (Rust) - Port 8080
- **Ollama** (LLM) - Port 11434
- **ChromaDB** (Vector Store) - Port 8000

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for complete deployment guide.

## Manual Setup

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
LLM_MODEL=llama2

# Memory Settings
MEMORY_AUTO_INJECT_CONTEXT=true
MEMORY_CONTEXT_TOKEN_BUDGET=4000
MEMORY_DEFAULT_FOLDER=/work
MEMORY_EXCLUDED_FOLDERS=/personal,/private
```

## Usage

### Web UI

Simply open **http://localhost:8081** and start chatting!

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
    model="llama2",
    messages=[{"role": "user", "content": "I'm building a Rust app with PostgreSQL"}]
)
# Sekha stores this conversation in /demo folder
```

**Session 2 (Tuesday, different app/LLM):**
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What database am I using for my Rust app?"}]
)
# Response: "You're using PostgreSQL with Rust..."
# AI automatically retrieved context from Session 1!
```

### Privacy: Exclude Folders

**Via Environment:**
```bash
MEMORY_EXCLUDED_FOLDERS=/personal/medical,/work/confidential
```

**Via API:**
```python
response = client.chat.completions.create(
    model="llama2",
    messages=[{"role": "user", "content": "What's my project status?"}],
    extra_body={
        "folder": "/work/project-alpha",
        "excluded_folders": ["/personal", "/private"]
    }
)
```

**Via Web UI:**
- Enter folders in the "Exclude Folders" field
- Conversations in those folders won't be used for context

## API Endpoints

### `POST /v1/chat/completions`

OpenAI-compatible chat endpoint with automatic context injection.

**Request:**
```json
{
  "model": "llama2",
  "messages": [
    {"role": "user", "content": "What did we discuss yesterday?"}
  ],
  "folder": "/work/project-alpha",
  "excluded_folders": ["/personal"],
  "context_budget": 4000
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
  "controller": "healthy",
  "llm": "healthy"
}
```

### `GET /`

Redirects to web UI (`/static/index.html`)

### `GET /api/info`

Proxy information and configuration.

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_HOST` | `0.0.0.0` | Proxy bind address |
| `PROXY_PORT` | `8081` | Proxy port |
| `LLM_PROVIDER` | `ollama` | LLM provider |
| `LLM_URL` | `http://localhost:11434` | LLM endpoint |
| `LLM_MODEL` | `llama2` | Model name |
| `LLM_API_KEY` | - | API key for cloud LLMs |
| `LLM_TIMEOUT` | `120` | LLM request timeout (seconds) |
| `CONTROLLER_URL` | `http://localhost:8080` | Sekha Controller URL |
| `CONTROLLER_API_KEY` | **required** | Controller API key |
| `CONTROLLER_TIMEOUT` | `30` | Controller timeout (seconds) |
| `MEMORY_AUTO_INJECT_CONTEXT` | `true` | Enable automatic context |
| `MEMORY_CONTEXT_TOKEN_BUDGET` | `4000` | Max tokens for context |
| `MEMORY_DEFAULT_FOLDER` | `/auto-captured` | Default folder |
| `MEMORY_PREFERRED_LABELS` | - | Labels to prioritize |
| `MEMORY_EXCLUDED_FOLDERS` | - | Folders to exclude (comma-separated) |

## Architecture

Sekha Proxy is a **thin routing layer** that leverages Sekha Controller's intelligence:

### Controller's 4-Phase Algorithm

1. **Recall**: Semantic search (200 candidates) + pinned + recent
2. **Rank**: Composite scoring (importance + recency + labels)
3. **Assemble**: Fill context budget with top-ranked messages
4. **Enhance**: Add citations and summaries

### Privacy Filtering

- Phase 1 filters out excluded folders during recall
- Supports prefix matching: `/work/secret` excludes all subfolders
- Per-request or global configuration

### Storage

- **SQLite**: Structured data (conversations, messages, metadata)
- **ChromaDB**: Vector embeddings for semantic search
- **Hybrid Search**: Best of both worlds

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
├── static/
│   └── index.html        # Web UI
├── docs/
│   └── DEPLOYMENT.md     # Deployment guide
├── scripts/
│   └── start.sh          # Quick start script
├── tests/                # Test suite
├── requirements.txt      # Dependencies
├── Dockerfile            # Container image
└── docker-compose.yml    # Full stack
```

## Testing the Full Flow

### 1. Store a conversation

```bash
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I am using PostgreSQL for my database"}
    ],
    "folder": "/work/project-alpha"
  }'
```

### 2. Test memory recall

```bash
# Wait a moment for storage, then:
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What database am I using?"}
    ],
    "folder": "/work/project-alpha"
  }'
```

The AI should remember "PostgreSQL"!

### 3. Test privacy filtering

```bash
# Store sensitive info
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "My API key is sk-secret-123"}
    ],
    "folder": "/private/secrets"
  }'

# Query with folder exclusion
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is my API key?"}
    ],
    "folder": "/work",
    "excluded_folders": ["/private"]
  }'
```

The AI should NOT recall the sensitive information!

## Troubleshooting

### Proxy Won't Start

```bash
# Check configuration
python -c "from config import Config; c = Config.from_env(); c.validate()"

# Check controller connectivity
curl http://localhost:8080/health
```

### Context Not Injecting

1. Check `MEMORY_AUTO_INJECT_CONTEXT=true` in `.env`
2. Verify controller has conversations: `curl http://localhost:8080/api/v1/conversations`
3. Check proxy logs: `docker-compose logs -f proxy`

### LLM Errors

```bash
# Test LLM directly
curl http://localhost:11434/api/tags  # Ollama
curl https://api.openai.com/v1/models -H "Authorization: Bearer $LLM_API_KEY"  # OpenAI
```

### Web UI Not Loading

```bash
# Check static files
ls -la static/

# Check proxy logs
docker-compose logs -f proxy

# Test health
curl http://localhost:8081/health
```

## Documentation

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions
- **[API Documentation](docs/API.md)** - API reference
- **[Architecture](docs/ARCHITECTURE.md)** - System design
- **[Contributing](CONTRIBUTING.md)** - Development guide

## License

AGPL-3.0-or-later

## Links

- **Homepage**: [sekha.dev](https://sekha.dev)
- **Controller**: [github.com/sekha-ai/sekha-controller](https://github.com/sekha-ai/sekha-controller)
- **Documentation**: [docs.sekha.dev](https://docs.sekha.dev)
- **Issues**: [github.com/sekha-ai/sekha-proxy/issues](https://github.com/sekha-ai/sekha-proxy/issues)

---

**Built with 💙 by the Sekha team**

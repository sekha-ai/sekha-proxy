# Deployment Guide

Complete guide for deploying Sekha Proxy in various environments.

## Quick Start (Docker Compose)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB disk space

### One-Command Deploy

```bash
# Clone both repositories
git clone https://github.com/sekha-ai/sekha-controller.git
git clone https://github.com/sekha-ai/sekha-proxy.git

# Start all services
cd sekha-proxy
export CONTROLLER_API_KEY="your-secure-key-here"
docker-compose up -d

# Pull Ollama model (first time only)
docker exec -it sekha-proxy-ollama-1 ollama pull llama2

# Check health
curl http://localhost:8081/health
```

### Access the UI

Open your browser to: **http://localhost:8081**

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│          User Browser (localhost:8081)          │
│              Web UI + Chat Interface            │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Sekha Proxy (Python) - Port 8081            │
│  - Context Injection                            │
│  - Privacy Filtering                            │
│  - Auto Storage                                 │
└───────┬────────────────────────┬────────────────┘
        │                        │
        │ GET context            │ Forward to LLM
        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐
│   Controller     │    │   Ollama/LLM     │
│   (Rust) 8080    │    │   Port 11434     │
│                  │    │                  │
│  - 4-Phase Asm   │    │  - llama2        │
│  - Privacy       │    │  - mistral       │
│  - SQLite        │    │  - etc.          │
└────────┬─────────┘    └──────────────────┘
         │
         ▼
┌──────────────────┐
│   Chroma         │
│   Port 8000      │
│                  │
│  - Vector Store  │
│  - Embeddings    │
└──────────────────┘
```

---

## Service Ports

| Service    | Port  | URL                          |
|------------|-------|------------------------------|
| Proxy UI   | 8081  | http://localhost:8081        |
| Proxy API  | 8081  | http://localhost:8081/v1/... |
| Controller | 8080  | http://localhost:8080        |
| Ollama     | 11434 | http://localhost:11434       |
| Chroma     | 8000  | http://localhost:8000        |

---

## Configuration

### Environment Variables

Create a `.env` file in the sekha-proxy directory:

```bash
# Security
CONTROLLER_API_KEY=your-secure-key-here

# Proxy Settings
PROXY_HOST=0.0.0.0
PROXY_PORT=8081

# Controller Connection
CONTROLLER_URL=http://controller:8080
CONTROLLER_TIMEOUT=30

# LLM Provider (Ollama)
LLM_PROVIDER=ollama
LLM_URL=http://ollama:11434
LLM_MODEL=llama2
LLM_TIMEOUT=120

# Memory Configuration
MEMORY_AUTO_INJECT_CONTEXT=true
MEMORY_DEFAULT_FOLDER=/work
MEMORY_CONTEXT_TOKEN_BUDGET=4000
MEMORY_EXCLUDED_FOLDERS=/private,/personal
```

### Using External LLM (OpenAI, Anthropic, etc.)

```bash
# OpenAI
LLM_PROVIDER=openai
LLM_URL=https://api.openai.com
LLM_MODEL=gpt-4
LLM_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=anthropic
LLM_URL=https://api.anthropic.com
LLM_MODEL=claude-3-opus-20240229
LLM_API_KEY=sk-ant-...

# Remove ollama from docker-compose.yml or comment it out
```

---

## Testing the Deployment

### 1. Health Check

```bash
curl http://localhost:8081/health
```

Expected response:
```json
{
  "status": "healthy",
  "controller": "healthy",
  "llm": "healthy"
}
```

### 2. API Test

```bash
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, remember that my name is Alice"}
    ],
    "folder": "/demo"
  }'
```

### 3. Test Memory (Second Request)

```bash
# Wait a moment, then ask
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is my name?"}
    ],
    "folder": "/demo"
  }'
```

The AI should remember "Alice" from the previous conversation!

### 4. Test Privacy Filtering

```bash
# Store sensitive info in /private folder
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "My social security number is 123-45-6789"}
    ],
    "folder": "/private/secrets"
  }'

# Later, exclude /private from context
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is my social security number?"}
    ],
    "folder": "/work",
    "excluded_folders": ["/private"]
  }'
```

The AI should NOT recall the sensitive information!

---

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f proxy
docker-compose logs -f controller
```

### Check Service Status

```bash
docker-compose ps
```

### Resource Usage

```bash
docker stats
```

---

## Scaling

### Horizontal Scaling

Run multiple proxy instances behind a load balancer:

```bash
docker-compose up --scale proxy=3
```

### Vertical Scaling

Increase resources in docker-compose.yml:

```yaml
services:
  proxy:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## Production Deployment

### Security Hardening

1. **Change default API key**
   ```bash
   export CONTROLLER_API_KEY=$(openssl rand -hex 32)
   ```

2. **Enable HTTPS** (add nginx reverse proxy)
   ```yaml
   services:
     nginx:
       image: nginx:alpine
       ports:
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./certs:/etc/nginx/certs
   ```

3. **Network isolation**
   - Keep Chroma and Controller on private network
   - Only expose Proxy to internet

4. **Rate limiting**
   - Add rate limits in proxy or nginx

### Backup Strategy

```bash
# Backup controller database
docker exec sekha-proxy-controller-1 \
  sqlite3 /data/sekha.db ".backup '/data/backup-$(date +%Y%m%d).db'"

# Backup Chroma data
docker run --rm -v sekha-proxy_chroma_data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/chroma-backup-$(date +%Y%m%d).tar.gz /data
```

### Update Strategy

```bash
# Pull latest images
docker-compose pull

# Restart with new images (zero downtime with multiple replicas)
docker-compose up -d --no-deps --build proxy
```

---

## Troubleshooting

### Proxy Can't Connect to Controller

```bash
# Check controller is running
docker-compose ps controller

# Check controller health
curl http://localhost:8080/health

# Check network connectivity
docker-compose exec proxy ping controller
```

### Ollama Model Not Found

```bash
# List available models
docker exec -it sekha-proxy-ollama-1 ollama list

# Pull model
docker exec -it sekha-proxy-ollama-1 ollama pull llama2
```

### Context Not Being Injected

1. Check `MEMORY_AUTO_INJECT_CONTEXT=true`
2. Verify controller has stored conversations
3. Check controller logs for errors

### High Memory Usage

- Reduce `MEMORY_CONTEXT_TOKEN_BUDGET`
- Use smaller LLM model
- Increase swap space

---

## Alternative Deployments

### Kubernetes

See `k8s/` directory for Kubernetes manifests.

### Systemd Service

For running without Docker:

```bash
# Copy systemd unit files
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sekha-proxy
sudo systemctl start sekha-proxy
```

### Cloud Platforms

- **AWS**: Use ECS/Fargate with RDS for SQLite → PostgreSQL
- **GCP**: Use Cloud Run with Cloud SQL
- **Azure**: Use Container Instances with Cosmos DB

---

## Next Steps

- Review [Configuration Guide](CONFIGURATION.md)
- Set up [Monitoring](MONITORING.md)
- Configure [Backups](BACKUPS.md)
- Read [API Documentation](API.md)

#!/bin/bash
set -e

# Sekha Proxy Quick Start Script
# This script sets up and starts all Sekha services

echo "🧠 Sekha Proxy - Quick Start"
echo "============================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker found"

# Check for controller repo
if [ ! -d "../sekha-controller" ]; then
    echo ""
    echo "Cloning sekha-controller..."
    cd ..
    git clone https://github.com/sekha-ai/sekha-controller.git
    cd sekha-proxy
fi

echo "✅ Controller repository found"

# Generate API key if not set
if [ -z "$CONTROLLER_API_KEY" ]; then
    export CONTROLLER_API_KEY=$(openssl rand -hex 16)
    echo "🔑 Generated API key: $CONTROLLER_API_KEY"
    echo "   (Set CONTROLLER_API_KEY env var to use a custom key)"
fi

echo ""
echo "Starting services..."
echo ""

# Start services
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."

# Wait for services
for i in {1..30}; do
    if curl -s http://localhost:8081/health > /dev/null 2>&1; then
        echo "✅ Proxy is healthy!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# Check if Ollama has models
echo ""
echo "Checking Ollama models..."
if docker exec sekha-proxy-ollama-1 ollama list 2>/dev/null | grep -q llama2; then
    echo "✅ Ollama model ready"
else
    echo "📊 Pulling llama2 model (this may take a few minutes)..."
    docker exec -it sekha-proxy-ollama-1 ollama pull llama2
    echo "✅ Model downloaded"
fi

echo ""
echo "============================"
echo "✅ Sekha Proxy is ready!"
echo "============================"
echo ""
echo "Access the Web UI:"
echo "  🌐 http://localhost:8081"
echo ""
echo "API Endpoints:"
echo "  Chat:   POST http://localhost:8081/v1/chat/completions"
echo "  Health: GET  http://localhost:8081/health"
echo ""
echo "Service URLs:"
echo "  Proxy:      http://localhost:8081"
echo "  Controller: http://localhost:8080"
echo "  Ollama:     http://localhost:11434"
echo "  Chroma:     http://localhost:8000"
echo ""
echo "Quick Test:"
echo "  curl -X POST http://localhost:8081/v1/chat/completions \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'"
echo ""
echo "View Logs:"
echo "  docker-compose logs -f"
echo ""
echo "Stop Services:"
echo "  docker-compose down"
echo ""

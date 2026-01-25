# Sekha Proxy

> **LLM Proxy with Automatic Memory Integration**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)
[![Status](https://img.shields.io/badge/status-experimental-red.svg)]()

---

## What is Sekha Proxy?

**Transparent LLM proxy** that automatically saves all conversations to Sekha.

Place it between your app and any LLM:

```
Your App → Sekha Proxy → LLM (OpenAI/Anthropic/etc)
                 │
                 ↓
           Sekha Controller
           (auto-save memory)
```

**Status:** Experimental - API subject to change

---

## 📚 Documentation

**Main docs: [docs.sekha.dev](https://docs.sekha.dev)**

- [Getting Started](https://docs.sekha.dev/getting-started/quickstart/)
- [API Reference](https://docs.sekha.dev/api-reference/rest-api/)
- [Architecture](https://docs.sekha.dev/architecture/overview/)

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/sekha-ai/sekha-proxy.git
cd sekha-proxy
pip install -r requirements.txt
```

### Configuration

```yaml
# config.yaml
sekha:
  controller_url: http://localhost:8080
  api_key: your-sekha-api-key

proxy:
  port: 8000
  allowed_providers:
    - openai
    - anthropic
```

### Run

```bash
python -m sekha_proxy --config config.yaml
```

### Use

```python
import openai

# Point to proxy instead of OpenAI directly
openai.api_base = "http://localhost:8000/v1"

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Conversation automatically saved to Sekha!
```

---

## ✨ Features

- ✅ Transparent proxy (no app changes)
- ✅ Auto-save all conversations
- ✅ Supports OpenAI, Anthropic
- ✅ Streaming responses
- ✅ Token tracking
- ✅ Request/response logging

---

## 🔗 Links

- **Main Repo:** [sekha-controller](https://github.com/sekha-ai/sekha-controller)
- **Docs:** [docs.sekha.dev](https://docs.sekha.dev)
- **Website:** [sekha.dev](https://sekha.dev)
- **Discord:** [discord.gg/sekha](https://discord.gg/sekha)

---

## 📄 License

AGPL-3.0 - **[License Details](https://docs.sekha.dev/about/license/)**

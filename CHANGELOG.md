# Changelog

All notable changes to Sekha Proxy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-10

### Added
- **Multi-provider routing via bridge**: All LLM requests now route through sekha-llm-bridge for intelligent provider selection across 100+ LLM providers (OpenAI, Anthropic, OpenRouter, local Ollama, etc.)
- **Automatic vision model detection**: Enhanced image detection supporting:
  - OpenAI multimodal format (content as array with image_url type)
  - Image URLs with common extensions (jpg, png, gif, etc.)
  - Base64 data URIs
- **Routing metadata in responses**: All responses now include `sekha_metadata.routing` with:
  - Provider ID and model ID used
  - Estimated cost per request
  - Task type (chat, vision, embedding)
- **Vision metadata**: Responses with images include image count and vision support status
- **Cost tracking**: Automatic cost estimation for all requests
- **Provider health monitoring**: Circuit breakers and health checks for bridge connectivity

### Changed
- **Configuration structure**: `LLM_URL` renamed to `BRIDGE_URL` to reflect new architecture
- **Always routes through bridge**: Proxy no longer talks directly to LLM providers
- **Improved error handling**: Better fallback mechanisms when bridge routing fails
- **Enhanced logging**: More detailed logging for routing decisions and image detection

### Fixed
- Type safety improvements (46 mypy errors resolved)
- Better handling of missing context scenarios
- Improved error messages for bridge connectivity issues

### Technical
- All tests passing (100% pass rate)
- Full CI/CD pipeline validated
- Type checking with mypy strict mode
- Linting with ruff
- Test coverage maintained

### Configuration Migration

**Before (v0.1.0):**
```bash
LLM_URL=http://ollama:11434
LLM_PROVIDER=ollama
```

**After (v0.2.0):**
```bash
BRIDGE_URL=http://bridge:5001
PREFERRED_CHAT_MODEL=llama3.1:8b
PREFERRED_VISION_MODEL=gpt-4o
```

## [0.1.0] - 2026-01-15

### Added
- Initial release of Sekha Proxy
- OpenAI-compatible API endpoint
- Automatic context injection from controller
- Conversation storage
- Web UI for monitoring
- Health check endpoints
- Single LLM provider support (Ollama)
- Basic configuration via environment variables

[0.2.0]: https://github.com/sekha-ai/sekha-proxy/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sekha-ai/sekha-proxy/releases/tag/v0.1.0

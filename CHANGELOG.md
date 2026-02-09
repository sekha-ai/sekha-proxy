# Changelog

All notable changes to Sekha Proxy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-10

### Added
- **Multi-provider routing**: All requests now route through LLM Bridge for intelligent provider selection
- **OpenRouter support**: Access 400+ models through OpenRouter integration via Bridge
- **Automatic vision detection**: Detects images in messages and routes to vision-capable models
  - Supports OpenAI multimodal format
  - Detects image URLs in text (jpg, png, gif, webp, svg)
  - Detects base64 data URIs
- **Routing metadata**: Response includes `sekha_metadata.routing` with provider, model, and cost info
- **Vision metadata**: Image count and vision support details when images detected
- **Preferred model configuration**: Set `PREFERRED_CHAT_MODEL` and `PREFERRED_VISION_MODEL`
- **Provider health monitoring**: Bridge reports provider health with circuit breakers
- **Cost estimation**: Every request includes estimated cost in metadata

### Changed
- **BREAKING**: Configuration structure updated
  - `LLM_URL` renamed to `BRIDGE_URL`
  - `LLM_PROVIDER` removed (bridge handles provider selection)
  - New: `PREFERRED_CHAT_MODEL` (optional)
  - New: `PREFERRED_VISION_MODEL` (optional)
- **BREAKING**: Proxy now requires LLM Bridge service (no direct LLM connections)
- **Improved error handling**: Better fallback behavior when bridge routing fails
- Health monitor now checks bridge status instead of direct LLM
- Enhanced logging with routing details

### Fixed
- Type safety improvements (46 mypy errors fixed)
- Better handling of empty context results
- Improved test coverage for vision detection
- Fixed context_count metadata only appearing when context exists

### Technical
- All tests passing (unit + integration)
- Full CI/CD pipeline validated
- Production-ready Docker images
- Type checking with mypy
- Linting with ruff

## [0.1.0] - 2026-01-15

### Added
- Initial release
- OpenAI-compatible proxy endpoint (`/v1/chat/completions`)
- Automatic context injection from controller
- Conversation storage to controller
- Web UI for configuration
- Health monitoring
- Basic LLM provider support (Ollama, OpenAI, Anthropic)
- Context token budget management
- Folder-based conversation organization
- Label preferences for context retrieval

[0.2.0]: https://github.com/sekha-ai/sekha-proxy/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sekha-ai/sekha-proxy/releases/tag/v0.1.0

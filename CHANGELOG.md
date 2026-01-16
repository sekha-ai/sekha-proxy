# Changelog

All notable changes to Sekha Proxy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial proxy implementation with automatic context injection
- Integration with sekha-controller for context assembly
- OpenAI-compatible `/v1/chat/completions` endpoint
- Automatic conversation storage
- Health monitoring for controller and LLM
- Privacy controls (folder exclusion)
- Comprehensive test suite
- Docker support
- CI/CD pipeline

### Changed

### Fixed

### Removed

## [0.0.0] - 2026-01-10

### Added
- Initial release
- Core proxy functionality
- Context injection from sekha-controller
- Support for multiple LLM providers (Ollama, OpenAI, Anthropic, etc.)
- Health monitoring
- Docker deployment
- Comprehensive documentation

[Unreleased]: https://github.com/sekha-ai/sekha-proxy/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/sekha-ai/sekha-proxy/releases/tag/v1.0.0

## [0.1.0] - 2026-01-16

### Added
- Initial release
- OpenAI-compatible proxy endpoint (/v1/chat/completions)
- Automatic context injection from Sekha Controller
- Privacy controls with folder exclusion
- Web UI for chat and configuration
- Docker Compose deployment
- LLM provider support: Ollama, OpenAI, Anthropic, Google, Cohere
- Health monitoring and metrics
- Comprehensive test suite (>85% coverage)

### Features
- Sub-10ms overhead vs direct LLM calls
- Async storage and context retrieval
- Configurable context budgets
- Label and folder organization
- Real-time privacy filtering

[0.1.0]: https://github.com/sekha-ai/sekha-proxy/releases/tag/v0.1.0
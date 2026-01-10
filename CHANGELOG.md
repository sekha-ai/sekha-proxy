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

## [1.0.0] - 2026-01-10

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

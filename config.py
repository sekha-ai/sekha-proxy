"""Configuration management for Sekha Proxy."""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ProxyConfig:
    """Proxy server configuration."""

    host: str = field(default="0.0.0.0")
    port: int = field(default=8081)


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = field(default="ollama")
    url: str = field(default="http://localhost:11434")
    api_key: Optional[str] = field(default=None)
    timeout: int = field(default=120)  # 2 minutes for LLM responses


@dataclass
class ControllerConfig:
    """Sekha Controller configuration."""

    url: str = field(default="http://localhost:8080")
    api_key: str = field(default="")
    timeout: int = field(default=30)


@dataclass
class MemoryConfig:
    """Memory and context configuration."""

    auto_inject_context: bool = field(default=True)
    context_token_budget: int = field(default=2000)
    context_limit: int = field(default=5)
    default_folder: str = field(default="/auto-captured")
    preferred_labels: List[str] = field(default_factory=list)
    excluded_folders: List[str] = field(default_factory=list)


@dataclass
class PrivacyConfig:
    """Privacy settings."""

    exclude_from_ai_context: bool = field(default=False)


@dataclass
class Config:
    """Complete Sekha Proxy configuration."""

    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            proxy=ProxyConfig(
                host=os.getenv("PROXY_HOST", "0.0.0.0"),
                port=int(os.getenv("PROXY_PORT", "8081")),
            ),
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "ollama"),
                url=os.getenv("LLM_URL", "http://localhost:11434"),
                api_key=os.getenv("LLM_API_KEY"),
                timeout=int(os.getenv("LLM_TIMEOUT", "120")),
            ),
            controller=ControllerConfig(
                url=os.getenv("CONTROLLER_URL", "http://localhost:8080"),
                api_key=os.getenv("CONTROLLER_API_KEY", ""),
                timeout=int(os.getenv("CONTROLLER_TIMEOUT", "30")),
            ),
            memory=MemoryConfig(
                auto_inject_context=os.getenv("AUTO_INJECT_CONTEXT", "true").lower()
                == "true",
                context_token_budget=int(os.getenv("CONTEXT_TOKEN_BUDGET", "2000")),
                context_limit=int(os.getenv("CONTEXT_LIMIT", "5")),
                default_folder=os.getenv("DEFAULT_FOLDER", "/auto-captured"),
                preferred_labels=(
                    os.getenv("PREFERRED_LABELS", "").split(",")
                    if os.getenv("PREFERRED_LABELS")
                    else []
                ),
                excluded_folders=(
                    os.getenv("EXCLUDED_FOLDERS", "").split(",")
                    if os.getenv("EXCLUDED_FOLDERS")
                    else []
                ),
            ),
            privacy=PrivacyConfig(
                exclude_from_ai_context=os.getenv(
                    "EXCLUDE_FROM_AI_CONTEXT", "false"
                ).lower()
                == "true"
            ),
        )

    def validate(self) -> None:
        """Validate configuration."""
        if not self.controller.api_key:
            raise ValueError("CONTROLLER_API_KEY is required")

        if self.llm.provider not in [
            "ollama",
            "openai",
            "anthropic",
            "google",
            "cohere",
        ]:
            raise ValueError(f"Unsupported LLM provider: {self.llm.provider}")

        if self.memory.context_token_budget < 100:
            raise ValueError("context_token_budget must be at least 100")

        if self.memory.context_limit < 1:
            raise ValueError("context_limit must be at least 1")

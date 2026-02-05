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
    """LLM Bridge configuration.
    
    In v2.0, the proxy ALWAYS communicates with the bridge.
    The bridge handles all provider routing and model selection.
    """

    # Bridge URL (always required)
    bridge_url: str = field(default="http://localhost:5001")
    
    # Request timeout
    timeout: int = field(default=120)
    
    # Optional model preferences (bridge will use these as hints)
    preferred_chat_model: Optional[str] = field(default=None)
    preferred_embedding_model: Optional[str] = field(default=None)
    preferred_vision_model: Optional[str] = field(default=None)


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
                bridge_url=os.getenv("LLM_BRIDGE_URL", "http://localhost:5001"),
                timeout=int(os.getenv("LLM_TIMEOUT", "120")),
                preferred_chat_model=os.getenv("PREFERRED_CHAT_MODEL"),
                preferred_embedding_model=os.getenv("PREFERRED_EMBEDDING_MODEL"),
                preferred_vision_model=os.getenv("PREFERRED_VISION_MODEL"),
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

        if not self.llm.bridge_url:
            raise ValueError("LLM_BRIDGE_URL is required")

        if self.memory.context_token_budget < 100:
            raise ValueError("context_token_budget must be at least 100")

        if self.memory.context_limit < 1:
            raise ValueError("context_limit must be at least 1")

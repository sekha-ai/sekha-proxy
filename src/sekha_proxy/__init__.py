"""Sekha Proxy - Intelligent LLM routing with automatic context injection."""

__version__ = "0.2.0"
__author__ = "Sekha AI"
__email__ = "dev@sekha-ai.dev"

# Export main classes for convenience
from sekha_proxy.config import Config
from sekha_proxy.context_injection import ContextInjector
from sekha_proxy.health import HealthMonitor
from sekha_proxy.proxy import SekhaProxy, app

__all__ = [
    "Config",
    "ContextInjector",
    "HealthMonitor",
    "SekhaProxy",
    "app",
    "__version__",
]

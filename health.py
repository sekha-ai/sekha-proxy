"""Health monitoring for Sekha Proxy."""

import logging
from typing import Any, Dict

from httpx import AsyncClient, HTTPError

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor health of proxy, controller, and LLM."""

    def __init__(
        self,
        controller_url: str,
        llm_url: str,
        controller_api_key: str,
        llm_provider: str = "ollama",
    ):
        self.controller_url = controller_url
        self.llm_url = llm_url
        self.llm_provider = llm_provider
        self.controller_client = AsyncClient(
            base_url=controller_url,
            headers={"Authorization": f"Bearer {controller_api_key}"},
            timeout=5.0,
        )
        self.llm_client = AsyncClient(base_url=llm_url, timeout=5.0)

    async def check_all(self) -> Dict[str, Any]:
        """
        Check health of all components.

        Returns:
            Health status dict with:
            - status: "healthy" | "degraded" | "unhealthy"
            - checks: {controller, llm, proxy}
        """
        checks = {
            "controller": await self._check_controller(),
            "llm": await self._check_llm(),
            "proxy": {"status": "ok"},  # If we're running, proxy is ok
        }

        # Determine overall status
        if all(c["status"] == "ok" for c in checks.values()):
            overall_status = "healthy"
        elif any(c["status"] == "error" for c in checks.values()):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {"status": overall_status, "checks": checks}

    async def _check_controller(self) -> Dict[str, Any]:
        """
        Check controller health.

        Returns:
            {"status": "ok" | "error", "error": str (if error)}
        """
        try:
            response = await self.controller_client.get("/health")
            if response.status_code == 200:
                return {"status": "ok", "url": self.controller_url}
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "url": self.controller_url,
                }
        except HTTPError as e:
            logger.error(f"Controller health check failed: {e}")
            return {"status": "error", "error": str(e), "url": self.controller_url}
        except Exception as e:
            logger.error(f"Controller health check unexpected error: {e}")
            return {
                "status": "error",
                "error": f"Unexpected: {str(e)}",
                "url": self.controller_url,
            }

    async def _check_llm(self) -> Dict[str, Any]:
        """
        Check LLM health.

        For bridge: GET /health
        For Ollama: GET /api/tags
        For OpenAI/Anthropic: GET /v1/models

        Returns:
            {"status": "ok" | "error", "error": str (if error)}
        """
        try:
            # For bridge provider, check /health endpoint
            if self.llm_provider == "bridge":
                response = await self.llm_client.get("/health")
                if response.status_code == 200:
                    return {"status": "ok", "url": self.llm_url, "provider": "bridge"}
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}",
                        "url": self.llm_url,
                        "provider": "bridge",
                    }

            # Try Ollama-style health check first
            response = await self.llm_client.get("/api/tags")
            if response.status_code == 200:
                return {
                    "status": "ok",
                    "url": self.llm_url,
                    "provider": self.llm_provider,
                }

            # Try OpenAI-style health check
            response = await self.llm_client.get("/v1/models")
            if response.status_code == 200:
                return {
                    "status": "ok",
                    "url": self.llm_url,
                    "provider": self.llm_provider,
                }

            return {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "url": self.llm_url,
                "provider": self.llm_provider,
            }
        except HTTPError as e:
            logger.warning(f"LLM health check failed: {e}")
            # LLM might not have health endpoint - don't fail hard
            return {
                "status": "warning",
                "error": f"Cannot verify: {str(e)}",
                "url": self.llm_url,
                "provider": self.llm_provider,
            }
        except Exception as e:
            logger.error(f"LLM health check unexpected error: {e}")
            return {
                "status": "error",
                "error": f"Unexpected: {str(e)}",
                "url": self.llm_url,
                "provider": self.llm_provider,
            }

    async def close(self):
        """Close HTTP clients."""
        await self.controller_client.aclose()
        await self.llm_client.aclose()

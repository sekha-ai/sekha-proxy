"""Sekha Proxy - Intelligent LLM routing with automatic context injection"""

__version__ = "2.0.0"
__author__ = "Sekha AI"
__email__ = "dev@sekha-ai.dev"

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from httpx import AsyncClient, HTTPError

from config import Config
from context_injection import ContextInjector
from health import HealthMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SekhaProxy:
    """Main proxy class that handles LLM routing with context injection."""

    def __init__(self, config: Config):
        self.config = config
        self.injector = ContextInjector()

        # HTTP client for bridge (v2.0 uses bridge for ALL LLM operations)
        self.bridge_client = AsyncClient(
            base_url=config.llm.bridge_url, timeout=config.llm.timeout
        )
        
        # HTTP client for controller
        self.controller_client = AsyncClient(
            base_url=config.controller.url,
            headers={"Authorization": f"Bearer {config.controller.api_key}"},
            timeout=config.controller.timeout,
        )

        # Health monitor
        self.health_monitor = HealthMonitor(
            controller_url=config.controller.url,
            llm_url=config.llm.bridge_url,  # Monitor bridge instead of direct LLM
            controller_api_key=config.controller.api_key,
            llm_provider="bridge",  # v2.0: always use bridge
        )

        logger.info("Sekha Proxy v2.0 initialized:")
        logger.info(f"  Bridge: {config.llm.bridge_url}")
        logger.info(f"  Controller: {config.controller.url}")
        logger.info(f"  Auto-inject context: {config.memory.auto_inject_context}")

    async def forward_chat(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main proxy logic - leverages controller intelligence and bridge routing.

        Args:
            request: OpenAI-compatible chat request

        Returns:
            Enhanced chat response with sekha_metadata including routing info
        """
        user_messages = request.get("messages", [])
        folder = request.get("folder", self.config.memory.default_folder)
        excluded_folders = request.get(
            "excluded_folders", self.config.memory.excluded_folders
        )
        context_budget = request.get(
            "context_budget", self.config.memory.context_token_budget
        )

        if not user_messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        # Extract last user query for context search
        last_query = self.injector.extract_last_user_message(user_messages)

        # Step 1: Get context from controller (if enabled)
        context = []
        if self.config.memory.auto_inject_context and last_query:
            try:
                context = await self._get_context_from_controller(
                    query=last_query,
                    preferred_labels=self.config.memory.preferred_labels,
                    context_budget=context_budget,
                    excluded_folders=excluded_folders,
                )
                logger.info(f"Retrieved {len(context)} context messages")
            except Exception as e:
                logger.error(
                    f"Context retrieval failed: {e}. Continuing without context."
                )
                context = []

        # Step 2: Inject context into prompt
        if context:
            enhanced_messages = self.injector.inject_context(user_messages, context)
            logger.debug(f"Injected {len(context)} context messages")
        else:
            enhanced_messages = user_messages

        # Step 3: Detect if vision is needed
        has_images = any(
            isinstance(msg.get("content"), list) 
            and any(item.get("type") == "image_url" for item in msg.get("content", []))
            for msg in enhanced_messages
        )

        # Step 4: Route request through bridge (v2.0)
        try:
            # Get optimal model routing from bridge
            routing_request = {
                "task": "vision" if has_images else "chat_small",
                "require_vision": has_images,
            }
            
            # Add preferred model if specified
            if request.get("model"):
                routing_request["preferred_model"] = request["model"]
            elif has_images and self.config.llm.preferred_vision_model:
                routing_request["preferred_model"] = self.config.llm.preferred_vision_model
            elif self.config.llm.preferred_chat_model:
                routing_request["preferred_model"] = self.config.llm.preferred_chat_model

            # Get routing decision from bridge
            routing_response = await self.bridge_client.post(
                "/api/v1/route", json=routing_request
            )
            routing_response.raise_for_status()
            routing_info = routing_response.json()
            
            logger.info(
                f"Bridge routing: {routing_info['provider_id']}/{routing_info['model_id']} "
                f"(${routing_info['estimated_cost']:.4f})"
            )

            # Build chat completion request with routed model
            chat_request = {
                "model": routing_info["model_id"],
                "messages": enhanced_messages,
                "stream": request.get("stream", False),
                "temperature": request.get("temperature", 0.7),
                "max_tokens": request.get("max_tokens"),
            }

            # Forward to bridge's chat completion endpoint
            response = await self.bridge_client.post(
                "/v1/chat/completions", json=chat_request
            )
            response.raise_for_status()
            response_data: Dict[str, Any] = response.json()

        except HTTPError as e:
            logger.error(f"Bridge request failed: {e}")
            raise HTTPException(status_code=502, detail=f"Bridge error: {str(e)}")

        # Step 5: Store conversation (async, non-blocking)
        if response_data.get("choices"):
            assistant_message = response_data["choices"][0]["message"]
            asyncio.create_task(
                self._store_conversation(
                    messages=user_messages + [assistant_message],
                    context_used=context,
                    folder=folder,
                )
            )

        # Step 6: Add metadata about context and routing
        sekha_metadata = {
            "routing": {
                "provider_id": routing_info.get("provider_id"),
                "model_id": routing_info.get("model_id"),
                "provider_type": routing_info.get("provider_type"),
                "estimated_cost": routing_info.get("estimated_cost"),
                "reason": routing_info.get("reason"),
            }
        }
        
        if context:
            sekha_metadata["context"] = {
                "messages_used": [
                    {
                        "label": c.get("metadata", {})
                        .get("citation", {})
                        .get("label", "Unknown"),
                        "folder": c.get("metadata", {})
                        .get("citation", {})
                        .get("folder", "Unknown"),
                    }
                    for c in context
                ],
                "count": len(context),
            }

        response_data["sekha_metadata"] = sekha_metadata

        return response_data

    async def _get_context_from_controller(
        self,
        query: str,
        preferred_labels: List[str],
        context_budget: int,
        excluded_folders: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Call controller's existing context assembly endpoint.

        Args:
            query: User query for semantic search
            preferred_labels: Labels to prioritize
            context_budget: Token budget for context
            excluded_folders: Folders to exclude from context

        Returns:
            List of assembled messages with citations
        """
        try:
            response = await self.controller_client.post(
                "/api/v1/context/assemble",
                json={
                    "query": query,
                    "preferred_labels": preferred_labels,
                    "context_budget": context_budget,
                    "excluded_folders": excluded_folders,
                },
            )

            if response.status_code == 200:
                result: List[Dict[str, Any]] = response.json()
                return result
            else:
                logger.warning(f"Context assembly returned {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Context assembly request failed: {e}")
            return []

    async def _store_conversation(
        self,
        messages: List[Dict[str, Any]],
        context_used: List[Dict[str, Any]],
        folder: str,
    ):
        """
        Store conversation via controller's existing endpoint.

        Args:
            messages: Full conversation (user + assistant)
            context_used: Context that was injected
            folder: Folder path for organization
        """
        try:
            # Generate label from first user message
            label = self.injector.generate_label(messages)

            # Build metadata
            metadata = self.injector.build_metadata(
                context_used=context_used, llm_provider="bridge_v2"
            )

            # Store via controller
            response = await self.controller_client.post(
                "/api/v1/conversations",
                json={
                    "label": label,
                    "folder": folder,
                    "messages": [
                        {
                            "role": m.get("role", "user"),
                            "content": m.get("content", ""),
                        }
                        for m in messages
                        if m.get("role")
                        in ["user", "assistant"]  # Filter out system messages
                    ],
                    "metadata": metadata,
                },
            )

            if response.status_code == 201:
                logger.info(f"Conversation stored: {label} in {folder}")
            else:
                logger.warning(
                    f"Conversation storage returned {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")

    async def close(self):
        """Close HTTP clients."""
        await self.bridge_client.aclose()
        await self.controller_client.aclose()
        await self.health_monitor.close()


# FastAPI app
proxy_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage proxy lifecycle."""
    global proxy_instance

    # Load config
    config = Config.from_env()
    config.validate()

    # Initialize proxy
    proxy_instance = SekhaProxy(config)
    logger.info("Sekha Proxy v2.0 started")

    yield

    # Cleanup
    if proxy_instance:
        await proxy_instance.close()
    logger.info("Sekha Proxy stopped")


app = FastAPI(
    title="Sekha Proxy",
    description="Intelligent LLM routing with automatic context injection (v2.0)",
    version="2.0.0",
    lifespan=lifespan,
)

# Mount static files for web UI
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI-compatible chat completions endpoint with context injection.

    This is the main proxy endpoint. Point your LLM client here instead of
    directly to Ollama/OpenAI/etc.
    
    v2.0: Routes through bridge for multi-provider support.
    """
    if proxy_instance is None:
        raise HTTPException(status_code=503, detail="Proxy not initialized")

    try:
        body = await request.json()
        response = await proxy_instance.forward_chat(body)
        return JSONResponse(content=response)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        health_status = await proxy_instance.health_monitor.check_all()

        if health_status["status"] == "unhealthy":
            return JSONResponse(content=health_status, status_code=503)

        return health_status
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            content={"status": "error", "error": str(e)}, status_code=500
        )


@app.get("/")
async def root():
    """Root endpoint - redirect to web UI."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/static/index.html")


@app.get("/api/info")
async def info():
    """API info endpoint."""
    return {
        "name": "Sekha Proxy",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "health": "/health",
            "ui": "/static/index.html",
        },
        "config": {
            "bridge_url": proxy_instance.config.llm.bridge_url,
            "auto_inject_context": proxy_instance.config.memory.auto_inject_context,
            "context_budget": proxy_instance.config.memory.context_token_budget,
        },
        "features": [
            "Multi-provider routing via bridge",
            "Automatic context injection",
            "Vision model routing",
            "Cost estimation",
            "Provider fallback",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    # Load config for port
    config = Config.from_env()

    uvicorn.run(
        "proxy:app",
        host=config.proxy.host,
        port=config.proxy.port,
        reload=False,
        log_level="info",
    )

"""Sekha Proxy - Intelligent LLM routing with automatic context injection"""

__version__ = "2.0.0"
__author__ = "Sekha AI"
__email__ = "dev@sekha-ai.dev"

import asyncio
import logging
import re
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Tuple

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

# Image URL pattern for detection
IMAGE_URL_PATTERN = re.compile(
    r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|bmp|webp|svg)(?:[?#][^\s<>"]*)?',
    re.IGNORECASE,
)


class SekhaProxy:
    """Main proxy class that handles LLM routing with context injection.

    v2.0 Updates:
    - Routes all LLM requests through bridge for multi-provider support
    - Automatically detects vision needs from message content
    - Enhanced image URL detection with pattern matching
    - Includes routing metadata in responses
    """

    def __init__(self, config: Config):
        self.config = config
        self.injector = ContextInjector()

        # Bridge client (v2.0: all LLM requests go through bridge)
        self.bridge_client = AsyncClient(
            base_url=config.llm.bridge_url, timeout=config.llm.timeout
        )

        # Controller client
        self.controller_client = AsyncClient(
            base_url=config.controller.url,
            headers={"Authorization": f"Bearer {config.controller.api_key}"},
            timeout=config.controller.timeout,
        )

        # Health monitor
        self.health_monitor = HealthMonitor(
            controller_url=config.controller.url,
            llm_url=config.llm.bridge_url,  # Monitor bridge, not direct LLM
            controller_api_key=config.controller.api_key,
            llm_provider="bridge",  # v2.0: proxy always talks to bridge
        )

        logger.info("Sekha Proxy v2.0 initialized:")
        logger.info(f"  Bridge: {config.llm.bridge_url}")
        logger.info(f"  Controller: {config.controller.url}")
        logger.info(f"  Auto-inject context: {config.memory.auto_inject_context}")
        logger.info("  Enhanced vision detection: enabled")

    def _detect_images_in_messages(
        self, messages: List[Dict[str, Any]]
    ) -> Tuple[bool, int]:
        """Detect if any message contains images.

        Supports multiple detection methods:
        1. OpenAI multimodal format (content as list with image_url type)
        2. Image URLs in text content (matches common image file extensions)
        3. Base64 data URIs in text content

        Args:
            messages: List of message dictionaries

        Returns:
            Tuple of (has_images, image_count)
        """
        image_count = 0

        for msg in messages:
            content = msg.get("content", "")

            # Method 1: Check if content is a list (OpenAI multimodal format)
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        image_count += 1

            # Method 2 & 3: Check for images in text content
            if isinstance(content, str):
                # Detect image URLs with common extensions
                url_matches = IMAGE_URL_PATTERN.findall(content)
                image_count += len(url_matches)

                # Detect base64 data URIs
                base64_pattern = r"data:image/[a-zA-Z]+;base64,"
                base64_matches = re.findall(base64_pattern, content)
                image_count += len(base64_matches)

        has_images = image_count > 0

        if has_images:
            logger.info(f"Detected {image_count} image(s) in messages")

        return has_images, image_count

    async def forward_chat(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main proxy logic - leverages bridge routing and controller intelligence.

        v2.0 Changes:
        - Routes through bridge for provider selection
        - Detects vision needs automatically with enhanced detection
        - Includes routing metadata in response

        Args:
            request: OpenAI-compatible chat request

        Returns:
            Enhanced chat response with sekha_metadata
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

        # Step 3: Get optimal routing from bridge (v2.0)
        try:
            # Detect if images are present with enhanced detection
            has_images, image_count = self._detect_images_in_messages(enhanced_messages)

            # Determine task type
            task = "vision" if has_images else "chat_small"

            # Get preferred model from config or request
            preferred_model = request.get("model") or (
                self.config.llm.preferred_vision_model
                if has_images
                else self.config.llm.preferred_chat_model
            )

            # Route the request
            routing_response = await self.bridge_client.post(
                "/api/v1/route",
                json={
                    "task": task,
                    "preferred_model": preferred_model,
                    "require_vision": has_images,
                    "max_cost": None,  # Could add cost limits here
                },
            )
            routing_response.raise_for_status()
            routing_data = routing_response.json()

            selected_model = routing_data["model_id"]
            provider_id = routing_data["provider_id"]
            estimated_cost = routing_data["estimated_cost"]

            logger.info(
                f"Bridge routed to {provider_id}/{selected_model} "
                f"(${estimated_cost:.4f}){' with vision' if has_images else ''}"
            )

        except HTTPError as e:
            logger.error(f"Bridge routing failed: {e}, using fallback")
            # Fallback to requested model or default
            selected_model = request.get("model", "llama3.1:8b")
            provider_id = "fallback"
            estimated_cost = 0.0
            has_images = False
            image_count = 0

        # Step 4: Forward to bridge for completion
        try:
            # Build OpenAI-compatible request
            llm_request = {
                "model": selected_model,
                "messages": enhanced_messages,
                "stream": request.get("stream", False),
                "temperature": request.get("temperature", 0.7),
                "max_tokens": request.get("max_tokens"),
            }

            response = await self.bridge_client.post(
                "/v1/chat/completions", json=llm_request
            )
            response.raise_for_status()
            response_data: Dict[str, Any] = response.json()

        except HTTPError as e:
            logger.error(f"Bridge chat completion failed: {e}")
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

        # Step 6: Add metadata about context and routing (v2.0)
        sekha_metadata = {
            "routing": {
                "provider_id": provider_id,
                "model_id": selected_model,
                "estimated_cost": estimated_cost,
                "task": task,
            }
        }

        # Add vision metadata if images detected
        if has_images:
            sekha_metadata["vision"] = {
                "image_count": image_count,
                "supports_vision": True,
            }

        if context:
            sekha_metadata["context_used"] = [
                {
                    "label": c.get("metadata", {})
                    .get("citation", {})
                    .get("label", "Unknown"),
                    "folder": c.get("metadata", {})
                    .get("citation", {})
                    .get("folder", "Unknown"),
                }
                for c in context
            ]
            sekha_metadata["context_count"] = len(context)

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
                context_used=context_used, llm_provider="bridge-v2"
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

    v2.0: Routes through bridge for multi-provider support with enhanced vision detection
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
        "features": [
            "Multi-provider routing via bridge",
            "Automatic context injection",
            "Enhanced vision detection (URL patterns + multimodal)",
            "Cost tracking",
        ],
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

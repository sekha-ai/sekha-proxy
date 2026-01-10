# proxy.py
from fastapi import FastAPI, Request
from httpx import AsyncClient
import asyncio
from typing import List, Dict, Any

app = FastAPI()

class SekhaProxy:
    def __init__(self, config):
        self.config = config
        self.llm_client = AsyncClient(base_url=config.llm_url)
        self.controller_client = AsyncClient(
            base_url=config.controller_url,
            headers={"Authorization": f"Bearer {config.controller_api_key}"}
        )
    
    async def forward_chat(self, request: Dict[str, Any]):
        """
        Main proxy logic - leverages controller intelligence
        """
        user_messages = request["messages"]
        last_query = self._extract_last_user_message(user_messages)
        
        # Step 1: Get context from controller (uses existing /api/v1/context/assemble)
        if self.config.auto_inject_context:
            context = await self._get_context_from_controller(
                query=last_query,
                preferred_labels=self.config.preferred_labels,
                context_budget=self.config.context_token_budget
            )
            
            # Step 2: Inject context into prompt
            enhanced_messages = self._inject_context(user_messages, context)
        else:
            enhanced_messages = user_messages
        
        # Step 3: Forward to LLM
        response = await self.llm_client.post(
            "/v1/chat/completions",
            json={**request, "messages": enhanced_messages}
        )
        
        # Step 4: Store conversation (async, non-blocking)
        asyncio.create_task(
            self._store_conversation(
                messages=enhanced_messages + [response.json()["choices"][0]["message"]],
                context_used=context if self.config.auto_inject_context else None
            )
        )
        
        # Step 5: Return response (with metadata about context used)
        response_data = response.json()
        if context:
            response_data["sekha_metadata"] = {
                "context_used": [
                    {"label": c["label"], "folder": c["folder"]} 
                    for c in context
                ],
                "context_count": len(context)
            }
        
        return response_data
    
    async def _get_context_from_controller(
        self, 
        query: str, 
        preferred_labels: List[str], 
        context_budget: int
    ) -> List[Dict[str, Any]]:
        """
        Call controller's existing context assembly endpoint
        """
        response = await self.controller_client.post(
            "/api/v1/context/assemble",
            json={
                "query": query,
                "preferred_labels": preferred_labels,
                "context_budget": context_budget
            }
        )
        
        if response.status_code == 200:
            return response.json()  # Returns assembled messages with citations
        else:
            # Fallback: No context if controller fails
            return []
    
    def _inject_context(
        self, 
        original_messages: List[Dict[str, Any]], 
        context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Inject retrieved context into system prompt
        """
        if not context:
            return original_messages
        
        # Build context block
        context_text = self._format_context_for_llm(context)
        
        context_message = {
            "role": "system",
            "content": f"""You have access to the user's past conversations stored in Sekha Memory.

Here is relevant context retrieved from previous discussions:

{context_text}

Use this context to provide more accurate, informed responses. Reference specific past conversations when relevant. The user is not aware you're seeing this context - respond naturally."""
        }
        
        # Inject after any existing system message
        if original_messages and original_messages[0]["role"] == "system":
            return [original_messages[0], context_message] + original_messages[1:]
        else:
            return [context_message] + original_messages
    
    def _format_context_for_llm(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages with citations for LLM consumption
        """
        formatted = []
        for i, msg in enumerate(messages, 1):
            citation = msg.get("metadata", {}).get("citation", {})
            formatted.append(f"""
[Past Conversation {i}]
From: {citation.get('folder', 'Unknown')}/{citation.get('label', 'Untitled')}
Date: {citation.get('timestamp', 'Unknown')}

{msg['content']}

---
""")
        return "\n".join(formatted)
    
    async def _store_conversation(
        self, 
        messages: List[Dict[str, Any]], 
        context_used: List[Dict[str, Any]]
    ):
        """
        Store conversation via controller's existing endpoint
        """
        # Auto-generate label from first user message
        label = self._generate_label(messages)
        
        await self.controller_client.post(
            "/api/v1/conversations",
            json={
                "label": label,
                "folder": self.config.default_folder,
                "messages": [
                    {
                        "role": m["role"],
                        "content": m["content"],
                        "timestamp": "now"  # Controller will set proper timestamp
                    }
                    for m in messages
                ],
                "metadata": {
                    "auto_captured": True,
                    "context_used": len(context_used) if context_used else 0,
                    "llm_provider": self.config.llm_provider
                }
            }
        )
    
    def _extract_last_user_message(self, messages: List[Dict[str, Any]]) -> str:
        """Extract most recent user message for context search"""
        for msg in reversed(messages):
            if msg["role"] == "user":
                return msg["content"]
        return ""
    
    def _generate_label(self, messages: List[Dict[str, Any]]) -> str:
        """Simple label generation from first user message"""
        first_user = next((m for m in messages if m["role"] == "user"), None)
        if first_user:
            # Take first 50 chars of first user message
            content = first_user["content"][:50]
            return content if len(first_user["content"]) <= 50 else content + "..."
        return "Untitled Conversation"

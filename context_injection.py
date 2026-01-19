"""Context injection and formatting for LLM prompts."""

from typing import Any, Dict, List


class ContextInjector:
    """Handles context retrieval formatting and injection into LLM prompts."""

    def inject_context(
        self, original_messages: List[Dict[str, Any]], context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Inject retrieved context into system prompt.

        Args:
            original_messages: Original chat messages
            context: Retrieved context from controller

        Returns:
            Enhanced messages with context injected
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

Use this context to provide more accurate, informed responses. Reference specific past conversations when relevant. The user is not aware you're seeing this context - respond naturally.""",
        }

        # Inject after any existing system message
        if original_messages and original_messages[0]["role"] == "system":
            return [original_messages[0], context_message] + original_messages[1:]
        else:
            return [context_message] + original_messages

    def format_context_for_llm(self, messages: List[Dict[str, Any]]) -> str:
        """Public method for formatting context (used by tests)."""
        return self._format_context_for_llm(messages)

    def _format_context_for_llm(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages with citations for LLM consumption.

        Args:
            messages: List of message dicts from controller

        Returns:
            Formatted context string with citations
        """
        formatted = []
        for i, msg in enumerate(messages, 1):
            # Extract citation metadata
            metadata = msg.get("metadata", {})

            # Handle both nested and flat citation structures
            if isinstance(metadata, dict):
                citation = metadata.get("citation", {})
            else:
                citation = {}

            folder = citation.get("folder", "Unknown")
            label = citation.get("label", "Untitled")
            timestamp = citation.get("timestamp", "Unknown")

            # Get message content
            content = msg.get("content", "")

            formatted.append(
                f"""[Past Conversation {i}]
From: {folder}/{label}
Date: {timestamp}

{content}

---"""
            )

        return "\n".join(formatted)

    def extract_last_user_message(self, messages: List[Dict[str, Any]]) -> str:
        """
        Extract most recent user message for context search.

        Args:
            messages: List of chat messages

        Returns:
            Last user message content
        """
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content: str = msg.get("content", "")
                return content
        return ""

    def generate_label(self, messages: List[Dict[str, Any]]) -> str:
        """
        Simple label generation from first user message.

        Args:
            messages: List of chat messages

        Returns:
            Generated label (max 50 chars)
        """
        first_user = next((m for m in messages if m.get("role") == "user"), None)
        if first_user:
            content = first_user.get("content", "")
            # Ensure type safety for mypy
            content_str: str = str(content) if not isinstance(content, str) else content
            if len(content_str) <= 50:
                return content_str
            return content_str[:50] + "..."
        return "Untitled Conversation"

    def build_metadata(
        self, context_used: List[Dict[str, Any]], llm_provider: str
    ) -> Dict[str, Any]:
        """
        Build metadata for stored conversation.

        Args:
            context_used: List of context messages used
            llm_provider: LLM provider name

        Returns:
            Metadata dict
        """
        return {
            "auto_captured": True,
            "context_used": len(context_used) if context_used else 0,
            "context_used_count": (
                len(context_used) if context_used else 0
            ),  # For test compatibility
            "llm_provider": llm_provider,
            "context_conversations": [
                {
                    "label": c.get("metadata", {}).get("citation", {}).get("label", "Unknown"),
                    "folder": c.get("metadata", {}).get("citation", {}).get("folder", "Unknown"),
                }
                for c in (context_used or [])
            ],
        }

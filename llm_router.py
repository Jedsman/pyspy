"""
LLM Router - Abstraction layer for different LLM backends
Supports Gemini, Claude, and future LLM implementations.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Optional, Any
import google.generativeai as genai
import os

# Configure logging
import logging
logger = logging.getLogger(__name__)


class LLMRouter(ABC):
    """Base class for LLM routing implementations"""

    @abstractmethod
    async def process(
        self,
        conversation: str,
        active_file_content: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Process conversation and return LLM response.

        Args:
            conversation: The conversation history/transcripts
            active_file_content: Optional content of the active file being edited
            custom_system_prompt: Optional custom system prompt to override default

        Returns:
            Response dictionary with 'type' and 'data' keys
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this LLM backend"""
        pass


class GeminiRouter(LLMRouter):
    """Router for Google Gemini API"""

    def __init__(self, system_prompt: str = "", model: str = "gemini-2.0-flash"):
        """
        Initialize Gemini router.

        Args:
            system_prompt: The base system prompt for Gemini
            model: Model name to use (default: gemini-2.0-flash)
        """
        self.system_prompt = system_prompt
        self.model = model
        self.api_key = os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable not set. "
                "Gemini router requires API key."
            )

        genai.configure(api_key=self.api_key)
        logger.info(f"Initialized GeminiRouter with model: {self.model}")

    async def process(
        self,
        conversation: str,
        active_file_content: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Process conversation with Gemini API using function calling.

        Returns:
            Response dictionary with function calls or text content
        """
        # Build prompt
        if custom_system_prompt:
            # Custom prompt already includes system prompt + custom instructions
            prompt = custom_system_prompt
        else:
            # Normal flow: build prompt from system prompt + conversation
            prompt_parts = [self.system_prompt]

            if active_file_content:
                prompt_parts.append(
                    f"ACTIVE FILE: `{active_file_content[:50]}...`\n---\n```\n{active_file_content}\n```\n---"
                )

            prompt_parts.append(f"CONVERSATION HISTORY:\n---\n{conversation}\n---")
            prompt_parts.append(
                "Based on the conversation, you must now call the `GenerateFiles` tool to produce the required code file(s)."
            )

            prompt = "\n".join(prompt_parts)

        if os.getenv("DEBUG", "false").lower() == "true":
            logger.debug(f"Gemini prompt:\n{prompt}")

        try:
            # Call Gemini API synchronously (wrapped in async)
            model = genai.GenerativeModel(
                self.model,
                system_instruction=self.system_prompt if not custom_system_prompt else None,
            )

            response = model.generate_content(prompt)

            return {
                "type": "text",
                "data": response.text,
                "raw_response": response,
            }

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {
                "type": "error",
                "data": f"Gemini API error: {str(e)}",
            }

    def get_name(self) -> str:
        """Return router name"""
        return "Gemini"


class ClaudeRouter(LLMRouter):
    """Router for Anthropic Claude API (scaffold for future implementation)"""

    def __init__(self, system_prompt: str = "", model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Claude router.

        Args:
            system_prompt: The base system prompt for Claude
            model: Model name to use
        """
        self.system_prompt = system_prompt
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            logger.warning(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Claude router will not be functional."
            )

        logger.info(f"Initialized ClaudeRouter with model: {self.model}")

    async def process(
        self,
        conversation: str,
        active_file_content: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Process conversation with Claude API.

        Returns:
            Response dictionary (currently not implemented)
        """
        logger.warning("Claude router is not yet fully implemented")
        return {
            "type": "error",
            "data": "Claude router not yet implemented. Use Gemini for now.",
        }

    def get_name(self) -> str:
        """Return router name"""
        return "Claude"


def get_router(
    llm_method: str = "gemini",
    system_prompt: str = "",
    model: Optional[str] = None,
) -> LLMRouter:
    """
    Factory function to get appropriate LLM router.

    Args:
        llm_method: "gemini" or "claude"
        system_prompt: System prompt to use
        model: Optional model override

    Returns:
        Configured LLMRouter instance

    Raises:
        ValueError: If llm_method is not recognized
    """
    llm_method = llm_method.lower()

    if llm_method == "gemini":
        return GeminiRouter(
            system_prompt=system_prompt,
            model=model or "gemini-2.0-flash",
        )
    elif llm_method == "claude":
        return ClaudeRouter(
            system_prompt=system_prompt,
            model=model or "claude-3-5-sonnet-20241022",
        )
    else:
        raise ValueError(
            f"Unknown LLM method: {llm_method}. "
            f"Supported: 'gemini', 'claude'"
        )

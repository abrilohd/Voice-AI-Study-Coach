"""Multi-provider LLM router with streaming support.

This module provides a unified interface for streaming responses from multiple
LLM providers (Anthropic Claude, OpenAI, Google Gemini) with automatic fallback,
prompt caching support, and proper error handling.
"""

from collections.abc import AsyncGenerator
from typing import Any

import anthropic
import google.genai as genai
import openai

from app.core.config import settings


def _estimate_tokens(text: str) -> int:
    """Rough token estimate for cache threshold checks.

    Uses ~0.75 tokens per word heuristic. NOT accurate for billing or
    actual usage (can be off by 2-3x for code, non-English, technical content).
    Only used to determine if text meets minimum cache token thresholds.

    ALWAYS use real token counts from API responses for billing/tracking.

    Args:
        text: Text to estimate token count for

    Returns:
        Estimated token count
    """
    return int(len(text.split()) * 0.75)


class LLMRouter:
    """Multi-provider LLM router with lazy initialization and streaming.

    Clients are initialized only when first used (lazy-init pattern) to avoid
    startup crashes when API keys are missing. This allows the application to
    start even if some providers are not configured.

    Attributes:
        _anthropic: Anthropic client (lazily initialized)
        _openai: OpenAI async client (lazily initialized)
        _gemini: Gemini client (lazily initialized)
    """

    def __init__(self) -> None:
        """Initialize router with no clients (lazy-init pattern)."""
        self._anthropic: anthropic.Anthropic | None = None
        self._openai: openai.AsyncOpenAI | None = None
        self._gemini: genai.Client | None = None  # type: ignore[name-defined,assignment]

    def _get_anthropic(self) -> anthropic.Anthropic:
        """Lazy-initialize Anthropic client.

        Returns:
            Initialized Anthropic client

        Raises:
            ValueError: If anthropic_api_key is not configured
        """
        if self._anthropic is None:
            if not settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
            self._anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._anthropic

    def _get_openai(self) -> openai.AsyncOpenAI:
        """Lazy-initialize OpenAI client.

        Returns:
            Initialized OpenAI async client

        Raises:
            ValueError: If openai_api_key is not configured
        """
        if self._openai is None:
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
            self._openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai

    def _get_gemini(self) -> genai.Client:  # type: ignore[name-defined,valid-type]
        """Lazy-initialize Gemini client.

        Returns:
            Initialized Gemini client

        Raises:
            ValueError: If gemini_api_key is not configured
        """
        if self._gemini is None:
            if not settings.gemini_api_key:
                raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY in .env")
            self._gemini = genai.Client(api_key=settings.gemini_api_key)  # type: ignore[attr-defined,assignment,misc]
        return self._gemini

    def _build_system_claude(self, system: str, use_cache: bool) -> str | list[dict[str, Any]]:
        """Build system prompt for Claude with optional prompt caching.

        CRITICAL CONSTRAINTS for prompt caching:
        1. System prompt >= 1024 TOKENS (not chars) - minimum for caching
        2. Same prefix MUST be reused within 5-minute TTL
        3. Cache WRITES cost MORE than normal input (premium)
        4. Cache READS cost ~10% of normal input

        ECONOMICS: Caching only pays off if the SAME prefix is reused within
        the 5-min TTL. A single-turn chat gets ZERO benefit and is slightly
        MORE expensive due to cache write premium.

        Use caching for: multi-turn conversations, repeated system prompts
        DON'T use for: one-off requests, short prompts

        Args:
            system: System prompt text
            use_cache: Whether to enable prompt caching

        Returns:
            String system prompt, or list with cache_control if caching enabled
        """
        if use_cache and _estimate_tokens(system) >= settings.prompt_cache_min_tokens:
            return [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        return system

    async def _stream_anthropic(
        self, messages: list[dict[str, Any]], system: str, use_cache: bool
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream from Anthropic Claude with prompt caching support.

        Args:
            messages: List of message dicts with role and content
            system: System prompt
            use_cache: Whether to enable prompt caching

        Yields:
            Dicts with type="text" and content, or type="usage" with token counts
        """
        client = self._get_anthropic()
        system_formatted = self._build_system_claude(system, use_cache)

        stream = client.messages.stream(
            model=settings.claude_model,
            max_tokens=settings.max_response_tokens,
            system=system_formatted,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

        async with stream:  # type: ignore[attr-defined,union-attr,misc]
            async for event in stream:  # type: ignore[attr-defined,union-attr,misc]
                # Text content chunks
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield {"type": "text", "content": event.delta.text}
                # Real token usage from Anthropic's final stream event
                # ALWAYS use these real numbers - they're free and accurate
                elif event.type == "message_delta":
                    if hasattr(event, "usage"):
                        yield {
                            "type": "usage",
                            "input_tokens": event.usage.input_tokens,
                            "output_tokens": event.usage.output_tokens,
                        }

    async def _stream_openai(
        self, messages: list[dict[str, Any]], system: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream from OpenAI GPT.

        Args:
            messages: List of message dicts with role and content
            system: System prompt

        Yields:
            Dicts with type="text" and content, or type="usage" with token counts
        """
        client = self._get_openai()

        # Prepend system message to messages list (OpenAI format)
        messages_with_system = [{"role": "system", "content": system}, *messages]

        stream = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=settings.max_response_tokens,
            messages=messages_with_system,  # type: ignore[arg-type]
            stream=True,  # type: ignore[arg-type]
            stream_options={"include_usage": True},  # type: ignore[arg-type,typeddict-item,misc]
        )

        async for chunk in stream:
            # Text content chunks
            if chunk.choices and chunk.choices[0].delta.content is not None:
                yield {"type": "text", "content": chunk.choices[0].delta.content}

            # Usage information (final chunk)
            if hasattr(chunk, "usage") and chunk.usage is not None:
                yield {
                    "type": "usage",
                    "input_tokens": chunk.usage.prompt_tokens,
                    "output_tokens": chunk.usage.completion_tokens,
                }

    async def _stream_gemini(
        self, messages: list[dict[str, Any]], system: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream from Google Gemini.

        Args:
            messages: List of message dicts with role and content
            system: System prompt

        Yields:
            Dicts with type="text" and content (Gemini doesn't provide token usage in stream)
        """
        self._get_gemini()

        # Gemini format: system instruction + user/assistant messages
        model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name=settings.gemini_model, system_instruction=system
        )

        # Convert messages to Gemini format (role: user/model)
        gemini_messages = [
            {
                "role": "model" if msg["role"] == "assistant" else msg["role"],
                "parts": [msg["content"]],
            }
            for msg in messages
        ]

        response = await model.generate_content_async(  # type: ignore[attr-defined,misc,call-arg]
            gemini_messages,
            stream=True,
            generation_config=genai.GenerationConfig(  # type: ignore[attr-defined]
                max_output_tokens=settings.max_response_tokens
            ),
        )

        async for chunk in response:
            if hasattr(chunk, "text") and chunk.text:
                yield {"type": "text", "content": chunk.text}

        # Gemini usage info only available after stream completes
        # Note: usage_metadata available on final response object after iteration
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            yield {
                "type": "usage",
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count,
            }

    async def _stream_provider(
        self,
        provider: str,
        messages: list[dict[str, Any]],
        system: str,
        use_cache: bool,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream from a specific provider.

        Args:
            provider: Provider name (claude, openai, gemini)
            messages: List of message dicts
            system: System prompt
            use_cache: Whether to enable prompt caching (Claude only)

        Yields:
            Stream events from the provider

        Raises:
            ValueError: If provider is unknown
        """
        if provider == "claude":
            async for chunk in self._stream_anthropic(messages, system, use_cache):
                yield chunk
        elif provider == "openai":
            async for chunk in self._stream_openai(messages, system):
                yield chunk
        elif provider == "gemini":
            async for chunk in self._stream_gemini(messages, system):
                yield chunk
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        provider: str | None = None,
        use_cache: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream tokens from the selected LLM provider with automatic fallback.

        CRITICAL FALLBACK BEHAVIOR: Fallback ONLY happens BEFORE first token is yielded.

        WHY: If you've already yielded 200 tokens from Claude and it errors mid-stream,
        falling back to OpenAI means the user sees a response that's half Claude-voice,
        half GPT-voice, with no indication. This creates incoherent responses.

        SOLUTION:
        - If first-token fails: retry with fallback provider (safe - nothing shown yet)
        - If mid-stream error: end gracefully with error event, let frontend offer "regenerate"
        - NEVER splice providers mid-stream

        Args:
            messages: List of message dicts with role and content keys
            system: System prompt (prepended to conversation)
            provider: Specific provider to use (None = use settings.primary_llm)
            use_cache: Enable prompt caching for Claude (only helps if reused within 5min)

        Yields:
            Dicts with keys:
            - {"type": "text", "content": str} - Text chunks
            - {"type": "usage", "input_tokens": int, "output_tokens": int} - Token counts
            - {"type": "error", "message": str} - Error notification

        Example:
            async for chunk in llm_router.stream(messages, system="You are helpful"):
                if chunk["type"] == "text":
                    print(chunk["content"], end="")
                elif chunk["type"] == "usage":
                    print(f"Tokens: {chunk['input_tokens']} in, {chunk['output_tokens']} out")
                elif chunk["type"] == "error":
                    print(f"Error: {chunk['message']}")
                    break
        """
        selected_provider = provider or settings.primary_llm
        first_chunk_sent = False

        try:
            async for chunk in self._stream_provider(
                selected_provider, messages, system, use_cache
            ):
                first_chunk_sent = True
                yield chunk

        except Exception as e:
            if (
                not first_chunk_sent
                and settings.fallback_llm
                and settings.fallback_llm != selected_provider
            ):
                # Safe to retry — nothing shown to user yet
                try:
                    async for chunk in self._stream_provider(
                        settings.fallback_llm, messages, system, use_cache
                    ):
                        yield chunk
                except Exception as fallback_error:
                    # Fallback also failed
                    yield {
                        "type": "error",
                        "message": f"All providers failed: {str(fallback_error)}",
                    }
            else:
                # Mid-stream failure — do NOT splice providers
                # Send error event and let frontend handle regenerate
                yield {
                    "type": "error",
                    "message": f"stream interrupted: {str(e)}",
                }

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        provider: str | None = None,
    ) -> tuple[str, int, int]:
        """Non-streaming completion using direct API calls (more efficient).

        NOTE: This does NOT use stream() method because that wastes the streaming
        benefit and adds latency (TTFT + full generation, sequential). For true
        non-streaming use, we call provider APIs directly without stream=True.

        Args:
            messages: List of message dicts with role and content
            system: System prompt
            provider: Specific provider to use

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)

        Raises:
            Exception: If API call fails
        """
        selected_provider = provider or settings.primary_llm

        if selected_provider == "claude":
            anthropic_client = self._get_anthropic()
            claude_response = anthropic_client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.max_response_tokens,
                system=system,
                messages=messages,  # type: ignore[arg-type]
            )
            text = "".join(
                block.text
                for block in claude_response.content
                if hasattr(block, "text")  # type: ignore[attr-defined]
            )
            return (
                text,
                claude_response.usage.input_tokens,  # type: ignore[attr-defined,misc]
                claude_response.usage.output_tokens,  # type: ignore[attr-defined,misc]
            )

        elif selected_provider == "openai":
            openai_client = self._get_openai()
            messages_with_system = [{"role": "system", "content": system}, *messages]
            openai_response = await openai_client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=settings.max_response_tokens,
                messages=messages_with_system,  # type: ignore[arg-type]
                stream=False,
            )
            text = openai_response.choices[0].message.content or ""  # type: ignore[union-attr]
            usage = openai_response.usage  # type: ignore[union-attr]
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            return text, input_tokens, output_tokens

        elif selected_provider == "gemini":
            self._get_gemini()
            model = genai.GenerativeModel(  # type: ignore[attr-defined]
                model_name=settings.gemini_model, system_instruction=system
            )
            gemini_messages = [
                {
                    "role": "model" if msg["role"] == "assistant" else msg["role"],
                    "parts": [msg["content"]],
                }
                for msg in messages
            ]
            response = await model.generate_content_async(  # type: ignore[attr-defined,misc,call-arg]
                gemini_messages,
                generation_config=genai.GenerationConfig(  # type: ignore[attr-defined]
                    max_output_tokens=settings.max_response_tokens
                ),
            )
            text = response.text if hasattr(response, "text") else ""
            usage = response.usage_metadata if hasattr(response, "usage_metadata") else None
            input_tokens = usage.prompt_token_count if usage else 0
            output_tokens = usage.candidates_token_count if usage else 0
            return text, input_tokens, output_tokens

        else:
            raise ValueError(f"Unknown provider: {selected_provider}")


# Singleton instance - safe because clients init lazily
llm_router = LLMRouter()

"""Chat service for managing conversations and LLM interactions."""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.router import llm_router
from app.core.prompts import TUTOR_SYSTEM
from app.models.message import Message
from app.repositories.conversation_repository import ConversationRepository
from app.services.exceptions import ConversationNotFoundError


class ChatService:
    """Service for managing chat conversations and AI responses.

    Handles conversation lifecycle, message persistence, and LLM streaming
    with proper transaction management.

    Attributes:
        conversation_repo: Repository for conversation database operations
        db: Database session for transaction management
    """

    def __init__(self, conversation_repo: ConversationRepository, db: AsyncSession) -> None:
        """Initialize chat service.

        Args:
            conversation_repo: Repository for conversation operations
            db: Database session for commits
        """
        self.conversation_repo = conversation_repo
        self.db = db

    async def stream_response(
        self,
        user_id: UUID,
        messages: list[dict[str, Any]],
        topic: str | None,
        provider: str | None,
        conversation_id: UUID | None,
        use_prompt_cache: bool,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream AI response with message persistence and token tracking.

        This method:
        1. Gets or creates conversation
        2. Saves user message to database
        3. Streams LLM response while accumulating full text
        4. Saves assistant reply with real token counts
        5. Commits everything in one transaction after stream completes

        CRITICAL: Does NOT commit mid-stream. All database writes use flush()
        until the stream completes, then commits once. This prevents partial
        conversations if stream is interrupted.

        Args:
            user_id: UUID of the user
            messages: List of message dicts (last one is new user message)
            topic: Optional topic/subject for the conversation
            provider: Optional specific LLM provider to use
            conversation_id: Existing conversation ID (None = create new)
            use_prompt_cache: Enable prompt caching for Claude

        Yields:
            Dicts with keys:
            - {"type": "text", "content": str} - Text chunks to stream
            - {"type": "usage", "input_tokens": int, "output_tokens": int} - Token usage
            - {"type": "done"} - Final event signaling completion
            - {"type": "error", "message": str} - Error occurred during streaming

        Raises:
            ConversationNotFoundError: If conversation_id doesn't exist or user doesn't own it
        """
        # Step 1: Get or create conversation
        conv_id: UUID
        if conversation_id is None:
            # Create new conversation - title from first message preview
            title = messages[-1]["content"][:50] + (
                "..." if len(messages[-1]["content"]) > 50 else ""
            )
            conversation = await self.conversation_repo.create(
                user_id=user_id,
                title=title,
                topic=topic,
                llm_provider=provider or "claude",
                is_voice=False,
            )
            conv_id = conversation.id
        else:
            # Get existing conversation with ownership check
            maybe_conversation = await self.conversation_repo.get_by_id(conversation_id, user_id)
            if maybe_conversation is None:
                raise ConversationNotFoundError(conversation_id)
            conversation = maybe_conversation
            conv_id = conversation_id

        # Step 2: Save user message to database
        user_message_content = messages[-1]["content"]
        await self.conversation_repo.add_message(
            conversation_id=conv_id,
            role="user",
            content=user_message_content,
            token_count=0,  # Will update with real count after stream
        )

        # Step 3: Build system prompt
        system_prompt = TUTOR_SYSTEM
        if topic:
            system_prompt += f"\n\nCurrent topic: {topic}"

        # Step 4: Stream from LLM and accumulate response
        full_reply = ""
        real_input_tokens = 0
        real_output_tokens = 0
        stream_error = False

        try:
            async for chunk in llm_router.stream(
                messages=messages,
                system=system_prompt,
                provider=provider,
                use_cache=use_prompt_cache,
            ):
                if chunk["type"] == "text":
                    full_reply += chunk["content"]
                    yield {"type": "text", "content": chunk["content"]}

                elif chunk["type"] == "usage":
                    # Real token counts from provider (not estimates)
                    real_input_tokens = chunk["input_tokens"]
                    real_output_tokens = chunk["output_tokens"]

                elif chunk["type"] == "error":
                    # Stream was interrupted - don't save partial response
                    stream_error = True
                    yield chunk
                    return  # Exit without saving

        except Exception as e:
            # Unexpected error during streaming
            yield {"type": "error", "message": f"Streaming failed: {str(e)}"}
            return  # Exit without saving

        # Step 5: Save assistant reply and update token counts (single transaction)
        if not stream_error and full_reply:
            # Save assistant message with actual output token count
            await self.conversation_repo.add_message(
                conversation_id=conv_id,
                role="assistant",
                content=full_reply,
                token_count=real_output_tokens,
            )

            # Update conversation total token count
            total_tokens = real_input_tokens + real_output_tokens
            await self.conversation_repo.update_token_count(conv_id, total_tokens)

            # Commit everything in one transaction
            await self.db.commit()

            # Signal completion
            yield {"type": "done"}

    async def get_history(self, user_id: UUID, conversation_id: UUID) -> list[Message]:
        """Get conversation history with ownership verification.

        Args:
            user_id: UUID of the user
            conversation_id: UUID of the conversation

        Returns:
            List of Message instances ordered chronologically

        Raises:
            ConversationNotFoundError: If conversation doesn't exist or user doesn't own it
        """
        # Verify user owns the conversation
        conversation = await self.conversation_repo.get_by_id(conversation_id, user_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)

        # Get messages
        messages = await self.conversation_repo.get_messages(conversation_id)
        return messages

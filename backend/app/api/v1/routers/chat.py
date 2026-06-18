"""Chat routes for streaming conversations and message history."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import (
    get_chat_service,
    get_current_user,
    limiter,
)
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ConversationResponse,
    MessageResponse,
)
from app.services.chat_service import ChatService
from app.services.exceptions import ConversationNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/stream",
    summary="Stream AI chat response with SSE",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")  # Rate limit LLM calls to prevent abuse
async def stream_chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """
    Stream AI chat response using Server-Sent Events (SSE).

    Rate limit: 20 requests per minute per IP (LLM calls are expensive).

    The stream returns JSON-encoded SSE events with the following types:
    - `{"type": "text", "content": "..."}` - Text chunks from the AI response
    - `{"type": "usage", "input_tokens": int, "output_tokens": int}` - Token usage stats
    - `{"type": "done"}` - Stream completed successfully
    - `{"type": "error", "message": "..."}` - Error occurred during streaming

    Headers include:
    - `Cache-Control: no-cache` - Prevents caching of the stream
    - `X-Accel-Buffering: no` - **Critical**: Disables Nginx buffering so tokens
      reach the browser immediately without being batched
    - `Connection: keep-alive` - Keeps connection open for streaming

    Args:
        request: FastAPI request object (required for rate limiting)
        chat_request: Chat request with messages and configuration
        current_user: Authenticated user from JWT token
        chat_service: Chat service for streaming responses

    Returns:
        StreamingResponse with text/event-stream media type

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 404 if conversation not found or not owned by user
        HTTPException: 429 if rate limit exceeded
    """

    async def generate() -> AsyncGenerator[str, None]:
        """SSE generator that streams JSON-encoded events."""
        try:
            async for event in chat_service.stream_response(
                user_id=current_user.id,
                messages=[m.model_dump() for m in chat_request.messages],
                topic=chat_request.topic,
                provider=chat_request.provider,
                conversation_id=chat_request.conversation_id,
                use_prompt_cache=chat_request.use_prompt_cache,
            ):
                # JSON-encode all events (handles newlines in content safely)
                yield f"data: {json.dumps(event)}\n\n"

        except ConversationNotFoundError:
            # Conversation doesn't exist or user doesn't own it
            yield f"data: {json.dumps({'type': 'error', 'message': 'conversation not found'})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected (closed tab/browser) - this is normal, not an error
            # Re-raise to properly clean up the generator without logging
            raise

        except Exception:
            # Unexpected error during streaming - log for debugging
            logger.exception("Stream failed with unexpected error")
            yield f"data: {json.dumps({'type': 'error', 'message': 'internal error'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Critical for real-time streaming
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    summary="List user's conversations",
    status_code=status.HTTP_200_OK,
)
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> list[ConversationResponse]:
    """
    List conversations for the authenticated user with pagination.

    Returns conversations ordered by most recently updated first.

    Args:
        limit: Maximum number of conversations to return (default: 20, max: 100)
        offset: Number of conversations to skip for pagination (default: 0)
        current_user: Authenticated user from JWT token
        chat_service: Chat service for conversation operations

    Returns:
        List of conversations with metadata (no messages included)

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Clamp limit to prevent abuse
    limit = min(limit, 100)

    conversations = await chat_service.conversation_repo.list_by_user(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return [ConversationResponse.model_validate(conv) for conv in conversations]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Get conversation message history",
    status_code=status.HTTP_200_OK,
)
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> list[MessageResponse]:
    """
    Get all messages for a specific conversation.

    Returns messages ordered chronologically (oldest first).

    Args:
        conversation_id: UUID of the conversation
        current_user: Authenticated user from JWT token
        chat_service: Chat service for message operations

    Returns:
        List of messages in chronological order

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 404 if conversation not found or not owned by user
    """
    from uuid import UUID

    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format",
        )

    try:
        messages = await chat_service.get_history(
            user_id=current_user.id,
            conversation_id=conv_uuid,
        )
        return [MessageResponse.model_validate(msg) for msg in messages]

    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )

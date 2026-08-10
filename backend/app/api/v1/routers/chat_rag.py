"""RAG-augmented chat routes for streaming conversations with document context."""

import asyncio
import json
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.ai.llm.router import llm_router
from app.core.dependencies import (
    get_chat_service,
    get_current_user,
    get_rag_service,
    limiter,
)
from app.core.prompts import TUTOR_SYSTEM
from app.models.user import User
from app.schemas.document import RAGChatRequest
from app.services.chat_service import ChatService
from app.services.exceptions import ConversationNotFoundError
from app.services.rag_service import RAGService

log = structlog.get_logger()

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/rag-stream",
    summary="Stream AI chat response with RAG context from user documents",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")  # Same rate limit as regular chat
async def stream_rag_chat(
    request: Request,
    chat_request: RAGChatRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    rag_service: RAGService = Depends(get_rag_service),
) -> StreamingResponse:
    """
    Stream AI chat response augmented with RAG context from user documents.

    Rate limit: 20 requests per minute per IP (same as regular chat).

    This endpoint extends the regular chat stream with semantic retrieval:
    1. Retrieves relevant chunks from user's documents
    2. Injects context into system prompt if chunks found
    3. Streams response with LLM router (same pattern as /chat/stream)
    4. Includes source metadata in the final 'done' event

    The stream returns JSON-encoded SSE events:
    - `{"type": "text", "content": "..."}` - Text chunks from AI
    - `{"type": "usage", "input_tokens": int, "output_tokens": int}` - Token usage
    - `{"type": "done", "total_tokens": int, "sources": [...]}` - Completion with sources
    - `{"type": "error", "message": "..."}` - Error during streaming

    Headers:
    - `Cache-Control: no-cache` - Prevents caching
    - `X-Accel-Buffering: no` - Critical for real-time streaming
    - `Connection: keep-alive` - Keeps connection open

    Args:
        request: FastAPI request object (required for rate limiting)
        chat_request: RAG chat request with messages and optional document filters
        current_user: Authenticated user from JWT token
        chat_service: Chat service for conversation management
        rag_service: RAG service for document retrieval

    Returns:
        StreamingResponse with text/event-stream media type

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 404 if conversation not found
        HTTPException: 429 if rate limit exceeded
    """

    async def generate() -> AsyncGenerator[str, None]:
        """SSE generator that streams RAG-augmented responses."""
        try:
            # Extract last user message for retrieval query
            user_messages = [msg for msg in chat_request.messages if msg.role == "user"]
            if not user_messages:
                error_msg = {'type': 'error', 'message': 'no user messages found'}
                yield f"data: {json.dumps(error_msg)}\n\n"
                return

            last_message = user_messages[-1].content

            # Step 1: Retrieve relevant chunks
            retrieved_chunks = await rag_service.retrieve_chunks(
                user_id=current_user.id,
                query=last_message,
                document_ids=chat_request.document_ids,
                limit=5,  # MAX_CHUNKS_IN_CONTEXT
            )

            # Step 2: Build RAG context if chunks found
            system_prompt = TUTOR_SYSTEM
            sources = []

            if retrieved_chunks:
                rag_context = await rag_service.build_rag_context(retrieved_chunks)
                # Prepend RAG context to system prompt
                system_prompt = f"{rag_context}\n\n{TUTOR_SYSTEM}"

                # Build sources list for done event
                sources = [
                    {
                        "document_title": chunk.document_title,
                        "similarity_score": chunk.similarity_score,
                        "chunk_index": chunk.chunk_index,
                    }
                    for chunk in retrieved_chunks
                ]

                log.info(
                    "rag.retrieval.success",
                    user_id=str(current_user.id),
                    query_length=len(last_message),
                    chunks_found=len(retrieved_chunks),
                )
            else:
                # No chunks found - log and continue without RAG context
                log.info(
                    "rag.retrieval.empty",
                    query_length=len(last_message),
                    user_id=str(current_user.id),
                )

            # Step 3: Stream response via LLM router
            messages_dict = [msg.model_dump() for msg in chat_request.messages]
            input_tokens = 0
            output_tokens = 0

            async for event in llm_router.stream(
                messages=messages_dict,
                system=system_prompt,
                provider=None,  # Use primary LLM
                use_cache=True,
            ):
                if event["type"] == "text":
                    # Forward text chunks
                    yield f"data: {json.dumps(event)}\n\n"

                elif event["type"] == "usage":
                    # Capture token counts
                    input_tokens = event.get("input_tokens", 0)
                    output_tokens = event.get("output_tokens", 0)

                elif event["type"] == "error":
                    # Forward errors
                    yield f"data: {json.dumps(event)}\n\n"
                    return

            # Step 4: Send done event with sources
            total_tokens = input_tokens + output_tokens
            done_event = {
                "type": "done",
                "total_tokens": total_tokens,
                "sources": sources,
            }
            yield f"data: {json.dumps(done_event)}\n\n"

        except ConversationNotFoundError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'conversation not found'})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected - normal, re-raise to clean up
            raise

        except Exception as e:
            log.error("rag.stream.error", error=str(e), error_type=type(e).__name__)
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

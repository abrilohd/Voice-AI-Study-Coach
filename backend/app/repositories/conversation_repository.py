"""Repository for conversation and message database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


class ConversationRepository:
    """Repository for managing conversations and messages."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    async def create(
        self,
        user_id: UUID,
        title: str,
        topic: str | None,
        llm_provider: str,
        is_voice: bool,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            user_id: UUID of the user creating the conversation
            title: Title of the conversation
            topic: Optional topic/subject of the conversation
            llm_provider: LLM provider to use (claude, openai, gemini)
            is_voice: Whether this is a voice conversation

        Returns:
            Created Conversation instance
        """
        conversation = Conversation(
            user_id=user_id,
            title=title,
            topic=topic,
            llm_provider=llm_provider,
            is_voice=is_voice,
        )
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        """Get conversation by ID with user ownership check.

        Args:
            conversation_id: UUID of the conversation
            user_id: UUID of the user (prevents accessing other users' conversations)

        Returns:
            Conversation instance if found and owned by user, None otherwise
        """
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[Conversation]:
        """List conversations for a user with pagination.

        Args:
            user_id: UUID of the user
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip

        Returns:
            List of Conversation instances ordered by updated_at DESC
        """
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        token_count: int = 0,
        audio_url: str | None = None,
    ) -> Message:
        """Add a message to a conversation.

        Note: This method uses flush() not commit(). The caller (ChatService)
        must commit the transaction after the full stream completes.

        Args:
            conversation_id: UUID of the conversation
            role: Message role (user, assistant, system)
            content: Message content
            token_count: Number of tokens in the message
            audio_url: Optional URL to audio file for voice messages

        Returns:
            Created Message instance
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
            audio_url=audio_url,
        )
        self.db.add(message)
        await self.db.flush()  # NOT commit - caller commits once after stream
        await self.db.refresh(message)
        return message

    async def get_messages(self, conversation_id: UUID, limit: int = 50) -> list[Message]:
        """Get messages for a conversation ordered chronologically.

        Uses composite ordering (created_at ASC, id ASC) to handle
        duplicate timestamps under high concurrency.

        Args:
            conversation_id: UUID of the conversation
            limit: Maximum number of messages to return

        Returns:
            List of Message instances ordered by created_at ASC, then id ASC
        """
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)  # Composite tiebreaker
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_token_count(self, conversation_id: UUID, additional_tokens: int) -> None:
        """Update token count for a conversation.

        Uses flush() not commit() - caller commits after full transaction.

        Args:
            conversation_id: UUID of the conversation
            additional_tokens: Number of tokens to add to the conversation
        """
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            conversation.token_count += additional_tokens
            await self.db.flush()  # NOT commit - caller commits once

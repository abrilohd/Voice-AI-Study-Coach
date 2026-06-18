"""Service layer exceptions for business logic errors."""

from uuid import UUID


class UserAlreadyExistsError(Exception):
    """Raised when attempting to register an email that already exists."""

    def __init__(self, email: str) -> None:
        """Initialize exception with the conflicting email.

        Args:
            email: The email address that already exists
        """
        self.email = email
        super().__init__(f"User with email {email} already exists")


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid.

    Intentionally vague to prevent user enumeration attacks.
    Does not distinguish between wrong email vs wrong password.
    """

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class UserNotFoundError(Exception):
    """Raised when a user is not found by ID."""

    def __init__(self, user_id: UUID) -> None:
        """Initialize exception with the missing user ID.

        Args:
            user_id: The UUID of the user that was not found
        """
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} not found")


class UserInactiveError(Exception):
    """Raised when attempting to authenticate an inactive user account."""

    def __init__(self) -> None:
        super().__init__("User account is inactive")


class InvalidTokenError(Exception):
    """Raised when a refresh token is invalid or expired."""

    def __init__(self) -> None:
        super().__init__("Invalid or expired refresh token")


class ConversationNotFoundError(Exception):
    """Raised when a conversation is not found or user doesn't have access."""

    def __init__(self, conversation_id: UUID) -> None:
        """Initialize exception with the conversation ID.

        Args:
            conversation_id: The UUID of the conversation that was not found
        """
        self.conversation_id = conversation_id
        super().__init__(f"Conversation with ID {conversation_id} not found or access denied")

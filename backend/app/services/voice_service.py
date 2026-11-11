"""Voice service for Speech-to-Text using Groq Whisper.

TTS intentionally removed - UX complexity not justified for V1.
"""

import logging
from pathlib import Path

from groq import AsyncGroq

from app.core.config import settings
from app.services.exceptions import AudioProcessingError, TranscriptionError

logger = logging.getLogger(__name__)


class VoiceService:
    """Handles Speech-to-Text using Groq's Whisper API.

    Design decisions:
    - Uses Groq Whisper API (fast inference, no local compute needed)
    - Lazy client initialization (doesn't fail app startup if key missing)
    - Supports common audio formats (webm, mp3, mp4, m4a, wav, ogg, flac)
    - 25MB max file size (Groq API limit)
    """

    # Audio constraints
    MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25MB
    SUPPORTED_AUDIO_FORMATS = {".webm", ".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac"}

    def __init__(self) -> None:
        """Initialize service with lazy client."""
        self._groq_client: AsyncGroq | None = None

    @property
    def groq_client(self) -> AsyncGroq:
        """Lazy initialize Groq client.

        Returns:
            AsyncGroq client instance

        Raises:
            TranscriptionError: If Groq API key is not configured
        """
        if self._groq_client is None:
            if not settings.groq_api_key:
                raise TranscriptionError("Groq API key not configured")
            self._groq_client = AsyncGroq(api_key=settings.groq_api_key)
        return self._groq_client

    async def transcribe(self, audio: bytes, filename: str) -> str:
        """Transcribe audio bytes to text using Groq Whisper.

        Args:
            audio: Raw audio data
            filename: Original filename (used to detect format)

        Returns:
            Transcribed text string. Empty string if audio has no speech.

        Raises:
            AudioProcessingError: If file format unsupported or file too large
            TranscriptionError: If Groq API call fails
        """
        # Validate file size
        if len(audio) > self.MAX_AUDIO_SIZE_BYTES:
            raise AudioProcessingError(
                f"Audio file exceeds maximum size of {self.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB"
            )

        # Validate file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.SUPPORTED_AUDIO_FORMATS:
            supported = ", ".join(sorted(self.SUPPORTED_AUDIO_FORMATS))
            raise AudioProcessingError(
                f"Unsupported audio format {file_ext}. Supported: {supported}"
            )

        try:
            # Call Groq Whisper API
            response = await self.groq_client.audio.transcriptions.create(
                file=(filename, audio),
                model=settings.stt_model,
                response_format="json",
            )

            text = response.text.strip()
            logger.info(f"Transcription completed: {len(text)} characters")
            return text

        except Exception as e:
            # Log provider error but don't expose it to client
            logger.error(f"Groq Whisper transcription failed: {e}")
            raise TranscriptionError("Speech-to-text service unavailable")

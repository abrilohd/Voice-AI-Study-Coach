"""Voice service for Speech-to-Text and Text-to-Speech."""

import asyncio
import logging
import tempfile
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import settings
from app.services.exceptions import (
    AudioProcessingError,
    TranscriptionError,
    TTSError,
)

logger = logging.getLogger(__name__)


class VoiceService:
    """Handles Speech-to-Text (Whisper local) and Text-to-Speech (ElevenLabs API).

    Design decisions:
    - Whisper runs locally: no API cost, no rate limits, works offline
    - Whisper model "base" loads once via @lru_cache — ~74MB RAM, ~1s load time
    - "base" model accuracy: ~95% WER on clear English speech
    - For production: upgrade to "small" or "medium" for better accuracy
    - ElevenLabs TTS: best quality/latency tradeoff for voice AI assistants
    - TTS is async (httpx) — does not block the event loop
    """

    # Audio constraints
    MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25MB (Whisper handles up to 30min audio)
    SUPPORTED_AUDIO_FORMATS = {".webm", ".mp3", ".wav", ".m4a", ".ogg"}

    # TTS constraints
    MAX_TTS_TEXT_LENGTH = 5000  # ElevenLabs free tier limit

    # Whisper model configuration (from settings)
    @property
    def whisper_model_name(self) -> str:
        """Get Whisper model name from settings."""
        return settings.whisper_model

    @lru_cache(maxsize=1)
    def _load_whisper_model(self):  # type: ignore[no-untyped-def]
        """Load Whisper model once and cache it.

        lru_cache on a method — the model stays loaded for the process lifetime.
        This means first transcription request takes ~1s (model load),
        all subsequent requests are fast (~0.5-2s for <30s audio clips).

        Returns:
            Loaded Whisper model

        Raises:
            TranscriptionError: If model loading fails
        """
        try:
            import whisper

            logger.info(f"Loading Whisper model: {self.whisper_model_name}")
            model = whisper.load_model(self.whisper_model_name)
            logger.info("Whisper model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise TranscriptionError(f"Failed to load Whisper model: {e}")

    async def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        """Convert audio bytes → text using local Whisper model.

        Args:
            audio_bytes: Raw audio data from frontend (WebM/WAV/MP3)
            filename: Original filename (used to detect format)

        Returns:
            Transcribed text string. Empty string if audio has no speech.

        Raises:
            AudioProcessingError: If file format unsupported or file too large
            TranscriptionError: If Whisper fails to process the audio

        Implementation:
        1. Validate file size and extension
        2. Write bytes to a temp file (Whisper requires a file path)
        3. Run Whisper in a thread pool (it's CPU-bound, would block event loop)
        4. Clean up temp file
        5. Return transcribed text, stripped of leading/trailing whitespace
        """
        # Validate file size
        if len(audio_bytes) > self.MAX_AUDIO_SIZE_BYTES:
            raise AudioProcessingError(
                f"Audio file exceeds maximum size of {self.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB"
            )

        # Validate file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.SUPPORTED_AUDIO_FORMATS:
            supported = ", ".join(self.SUPPORTED_AUDIO_FORMATS)
            raise AudioProcessingError(
                f"Unsupported audio format {file_ext}. Supported: {supported}"
            )

        # Write to temporary file (Whisper requires file path)
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=file_ext
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            # Load model (cached after first call)
            model = self._load_whisper_model()

            # Run Whisper transcription in thread pool (CPU-bound operation)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: model.transcribe(temp_file_path)
            )

            # Extract text from result
            text: str = result.get("text", "").strip()
            logger.info(f"Transcription completed: {len(text)} characters")
            return text

        except (AudioProcessingError, TranscriptionError):
            # Re-raise our own exceptions
            raise

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise TranscriptionError(f"Whisper processing failed: {e}")

        finally:
            # Clean up temporary file
            if temp_file is not None:
                try:
                    Path(temp_file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")

    async def synthesize_speech(
        self, text: str, voice_id: str | None = None
    ) -> bytes:
        """Convert text → audio bytes using ElevenLabs API.

        Args:
            text: Text to synthesize (max 5000 chars for free tier)
            voice_id: Override default voice (optional)

        Returns:
            MP3 audio bytes (ready to stream directly to frontend)

        Raises:
            TTSError: If ElevenLabs API fails or text is too long

        Implementation:
        1. Validate text length (raise TTSError if > 5000 chars)
        2. Call ElevenLabs v1/text-to-speech/{voice_id} endpoint via httpx
        3. Use streaming=True for lower latency response
        4. Return raw MP3 bytes
        """
        # Validate text length
        if len(text) > self.MAX_TTS_TEXT_LENGTH:
            raise TTSError(
                f"Text exceeds maximum length of {self.MAX_TTS_TEXT_LENGTH} characters"
            )

        # Use default voice if not specified
        target_voice_id = voice_id or settings.tts_voice_id

        # Build API request
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice_id}"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": settings.tts_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                # Check for API errors
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"ElevenLabs API error: {response.status_code} - {error_detail}"
                    )
                    raise TTSError(f"ElevenLabs API returned status {response.status_code}")

                # Return MP3 bytes
                audio_bytes = response.content
                logger.info(f"TTS synthesis completed: {len(audio_bytes)} bytes")
                return audio_bytes

        except TTSError:
            # Re-raise our own exceptions
            raise

        except httpx.TimeoutException:
            logger.error("ElevenLabs API timeout")
            raise TTSError("TTS request timed out")

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise TTSError(f"TTS processing failed: {e}")

    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio formats.

        Returns:
            List of supported file extensions (e.g., ['.webm', '.mp3'])
        """
        return list(self.SUPPORTED_AUDIO_FORMATS)

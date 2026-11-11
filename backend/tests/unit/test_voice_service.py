"""Unit tests for VoiceService."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.exceptions import AudioProcessingError, TranscriptionError
from app.services.voice_service import VoiceService


@pytest.mark.asyncio
class TestTranscribe:
    """Unit tests for VoiceService.transcribe()."""

    async def test_transcribe_invalid_format(self):
        """Test transcription rejects unsupported file formats."""
        # Arrange
        service = VoiceService()
        audio_data = b"fake audio data"
        filename = "malicious.exe"

        # Act & Assert
        with pytest.raises(AudioProcessingError) as exc_info:
            await service.transcribe(audio_data, filename)

        assert "Unsupported audio format" in str(exc_info.value)
        assert ".exe" in str(exc_info.value)

    async def test_transcribe_file_too_large(self):
        """Test transcription rejects files exceeding 25MB limit."""
        # Arrange
        service = VoiceService()
        large_audio_data = b"\x00" * (26 * 1024 * 1024)  # 26MB
        filename = "large.mp3"

        # Act & Assert
        with pytest.raises(AudioProcessingError) as exc_info:
            await service.transcribe(large_audio_data, filename)

        assert "exceeds maximum size" in str(exc_info.value)
        assert "25" in str(exc_info.value)

    async def test_transcribe_success(self):
        """Test successful transcription."""
        # Arrange
        service = VoiceService()
        audio_data = b"fake audio data"
        filename = "test.mp3"

        # Mock Groq client
        mock_transcription = AsyncMock()
        mock_transcription.text = "Hello, this is a test."

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)

        # Act
        with patch("app.services.voice_service.AsyncGroq", return_value=mock_client):
            result = await service.transcribe(audio_data, filename)

        # Assert
        assert result == "Hello, this is a test."
        mock_client.audio.transcriptions.create.assert_called_once()

    async def test_transcribe_empty_result(self):
        """Test transcription with empty result."""
        # Arrange
        service = VoiceService()
        audio_data = b"silence"
        filename = "silent.wav"

        # Mock Groq client returning empty text
        mock_transcription = AsyncMock()
        mock_transcription.text = "  "  # Whitespace only

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)

        # Act
        with patch("app.services.voice_service.AsyncGroq", return_value=mock_client):
            result = await service.transcribe(audio_data, filename)

        # Assert
        assert result == ""  # Should be stripped to empty string

    async def test_transcribe_api_failure(self):
        """Test transcription handles API failures gracefully."""
        # Arrange
        service = VoiceService()
        audio_data = b"fake audio"
        filename = "test.webm"

        # Mock Groq client raising exception
        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        # Act & Assert
        with patch("app.services.voice_service.AsyncGroq", return_value=mock_client):
            with pytest.raises(TranscriptionError) as exc_info:
                await service.transcribe(audio_data, filename)

        # Should return generic error, not the API error details
        assert "service unavailable" in str(exc_info.value).lower()

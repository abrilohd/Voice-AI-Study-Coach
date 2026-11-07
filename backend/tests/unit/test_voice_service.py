"""Unit tests for VoiceService with AsyncMock (no real API calls)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.exceptions import AudioProcessingError, TranscriptionError, TTSError
from app.services.voice_service import VoiceService


@pytest.fixture
def voice_service() -> VoiceService:
    """Create a VoiceService instance for testing."""
    return VoiceService()


class TestTranscribeAudio:
    """Tests for transcribe_audio method."""

    async def test_transcribe_validates_file_size(
        self, voice_service: VoiceService
    ) -> None:
        """Test that transcription rejects files exceeding 25MB."""
        # Create audio bytes larger than 25MB
        large_audio = b"x" * (26 * 1024 * 1024)  # 26MB

        with pytest.raises(AudioProcessingError) as exc_info:
            await voice_service.transcribe_audio(large_audio, "test.mp3")

        assert "exceeds maximum size" in str(exc_info.value)
        assert "25MB" in str(exc_info.value)

    async def test_transcribe_validates_file_format(
        self, voice_service: VoiceService
    ) -> None:
        """Test that transcription rejects unsupported file formats."""
        audio_bytes = b"fake audio data"

        with pytest.raises(AudioProcessingError) as exc_info:
            await voice_service.transcribe_audio(audio_bytes, "audio.exe")

        assert "Unsupported audio format" in str(exc_info.value)
        assert ".exe" in str(exc_info.value)

    async def test_transcribe_success(self, voice_service: VoiceService) -> None:
        """Test successful audio transcription with mocked Whisper."""
        audio_bytes = b"fake audio data"
        filename = "test.wav"

        # Mock Whisper model and transcribe method
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "  Hello world  "}

        with patch.object(voice_service, "_load_whisper_model", return_value=mock_model):
            result = await voice_service.transcribe_audio(audio_bytes, filename)

        # Should return stripped text
        assert result == "Hello world"

        # Verify model was loaded
        mock_model.transcribe.assert_called_once()

    async def test_transcribe_model_load_failure(
        self, voice_service: VoiceService
    ) -> None:
        """Test that model loading failures raise TranscriptionError."""
        audio_bytes = b"fake audio data"
        filename = "test.wav"

        with patch.object(
            voice_service,
            "_load_whisper_model",
            side_effect=TranscriptionError("Failed to load Whisper model: Model not found"),
        ):
            with pytest.raises(TranscriptionError) as exc_info:
                await voice_service.transcribe_audio(audio_bytes, filename)

        assert "Failed to load Whisper model" in str(exc_info.value)

    async def test_transcribe_processing_failure(
        self, voice_service: VoiceService
    ) -> None:
        """Test that Whisper processing failures raise TranscriptionError."""
        audio_bytes = b"fake audio data"
        filename = "test.wav"

        # Mock model that fails during transcription
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Corrupted audio")

        with patch.object(voice_service, "_load_whisper_model", return_value=mock_model):
            with pytest.raises(TranscriptionError) as exc_info:
                await voice_service.transcribe_audio(audio_bytes, filename)

        assert "Whisper processing failed" in str(exc_info.value)

    async def test_transcribe_empty_result(self, voice_service: VoiceService) -> None:
        """Test transcription returns empty string for silent audio."""
        audio_bytes = b"fake audio data"
        filename = "test.wav"

        # Mock Whisper returning empty text
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "   "}

        with patch.object(voice_service, "_load_whisper_model", return_value=mock_model):
            result = await voice_service.transcribe_audio(audio_bytes, filename)

        assert result == ""


class TestSynthesizeSpeech:
    """Tests for synthesize_speech method."""

    async def test_synthesize_validates_text_length(
        self, voice_service: VoiceService
    ) -> None:
        """Test that synthesis rejects text exceeding 5000 characters."""
        # Create text longer than 5000 chars
        long_text = "x" * 5001

        with pytest.raises(TTSError) as exc_info:
            await voice_service.synthesize_speech(long_text)

        assert "exceeds maximum length" in str(exc_info.value)
        assert "5000" in str(exc_info.value)

    async def test_synthesize_success(self, voice_service: VoiceService) -> None:
        """Test successful speech synthesis with mocked ElevenLabs API."""
        text = "Hello, this is a test."
        fake_mp3 = b"fake_mp3_bytes"

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_mp3

        # Mock AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await voice_service.synthesize_speech(text)

        assert result == fake_mp3

        # Verify API was called with correct parameters
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "text-to-speech" in call_args[0][0]  # URL contains endpoint
        assert call_args[1]["json"]["text"] == text

    async def test_synthesize_with_custom_voice(
        self, voice_service: VoiceService
    ) -> None:
        """Test synthesis with custom voice_id parameter."""
        text = "Hello, this is a test."
        custom_voice_id = "custom_voice_123"
        fake_mp3 = b"fake_mp3_bytes"

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_mp3

        # Mock AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await voice_service.synthesize_speech(text, voice_id=custom_voice_id)

        assert result == fake_mp3

        # Verify custom voice_id was used in URL
        call_args = mock_client.post.call_args
        assert custom_voice_id in call_args[0][0]

    async def test_synthesize_api_failure(self, voice_service: VoiceService) -> None:
        """Test that ElevenLabs API failures raise TTSError."""
        text = "Hello, this is a test."

        # Mock httpx response with 401 error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"

        # Mock AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TTSError) as exc_info:
                await voice_service.synthesize_speech(text)

        assert "ElevenLabs API returned status 401" in str(exc_info.value)

    async def test_synthesize_timeout(self, voice_service: VoiceService) -> None:
        """Test that API timeout raises TTSError."""
        text = "Hello, this is a test."

        # Mock AsyncClient that raises timeout
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TTSError) as exc_info:
                await voice_service.synthesize_speech(text)

        assert "TTS request timed out" in str(exc_info.value)

    async def test_synthesize_network_error(self, voice_service: VoiceService) -> None:
        """Test that network errors raise TTSError."""
        text = "Hello, this is a test."

        # Mock AsyncClient that raises network error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=Exception("Network unreachable"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TTSError) as exc_info:
                await voice_service.synthesize_speech(text)

        assert "TTS processing failed" in str(exc_info.value)


class TestGetSupportedFormats:
    """Tests for get_supported_formats method."""

    def test_get_supported_formats(self, voice_service: VoiceService) -> None:
        """Test that supported formats are returned correctly."""
        formats = voice_service.get_supported_formats()

        # Should return list of supported extensions
        assert isinstance(formats, list)
        assert len(formats) == 5
        assert ".webm" in formats
        assert ".mp3" in formats
        assert ".wav" in formats
        assert ".m4a" in formats
        assert ".ogg" in formats

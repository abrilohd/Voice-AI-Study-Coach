"""Integration tests for voice endpoints with real database."""

from io import BytesIO

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
class TestVoiceTranscribe:
    """Integration tests for speech-to-text transcription."""

    async def test_transcribe_requires_auth(self, async_client: AsyncClient):
        """Test transcription endpoint requires authentication."""
        # Arrange - Create a dummy audio file
        audio_data = BytesIO(b"fake audio data")
        files = {"file": ("test.mp3", audio_data, "audio/mpeg")}

        # Act - Attempt transcription without auth token
        response = await async_client.post(
            "/api/v1/voice/transcribe",
            files=files,
        )

        # Assert
        assert response.status_code == 401
        assert "detail" in response.json()

    async def test_transcribe_invalid_format(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Test transcription rejects unsupported file formats."""
        # Arrange - Create a file with unsupported extension
        audio_data = BytesIO(b"fake executable data")
        files = {"file": ("malicious.exe", audio_data, "application/octet-stream")}

        # Act
        response = await async_client.post(
            "/api/v1/voice/transcribe",
            files=files,
            headers=auth_headers,
        )

        # Assert - Should reject with 422 Unprocessable Entity
        assert response.status_code == 422
        data = response.json()
        assert "not supported" in data["detail"].lower()
        assert ".exe" in data["detail"]

    async def test_transcribe_file_too_large(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Test transcription rejects files exceeding 25MB limit."""
        # Arrange - Create a 26MB file (exceeds 25MB limit)
        large_audio_data = BytesIO(b"\x00" * (26 * 1024 * 1024))  # 26MB of zeros
        files = {"file": ("large.mp3", large_audio_data, "audio/mpeg")}

        # Act
        response = await async_client.post(
            "/api/v1/voice/transcribe",
            files=files,
            headers=auth_headers,
        )

        # Assert - Should reject with 422
        assert response.status_code == 422
        data = response.json()
        assert "exceeds maximum" in data["detail"].lower()
        assert "25" in data["detail"]  # Should mention 25MB limit


@pytest.mark.asyncio
class TestVoiceSynthesize:
    """Integration tests for text-to-speech synthesis."""

    async def test_synthesize_requires_auth(self, async_client: AsyncClient):
        """Test synthesis endpoint requires authentication."""
        # Arrange
        payload = {"text": "Hello, this is a test"}

        # Act - Attempt synthesis without auth token
        response = await async_client.post(
            "/api/v1/voice/synthesize",
            json=payload,
        )

        # Assert
        assert response.status_code == 401
        assert "detail" in response.json()

    async def test_synthesize_text_too_long(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Test synthesis rejects text exceeding 5000 character limit."""
        # Arrange - Create text with 5001 characters
        long_text = "x" * 5001
        payload = {"text": long_text}

        # Act
        response = await async_client.post(
            "/api/v1/voice/synthesize",
            json=payload,
            headers=auth_headers,
        )

        # Assert - Should reject with 422 (Pydantic validation)
        assert response.status_code == 422
        data = response.json()
        # Pydantic validation error structure
        assert "detail" in data
        assert isinstance(data["detail"], list)
        # Check that the error is about text length
        error = data["detail"][0]
        assert error["loc"] == ["body", "text"]
        assert "5000" in str(error["msg"]).lower() or "length" in str(
            error["msg"]
        ).lower()

    async def test_synthesize_missing_api_key(
        self, async_client: AsyncClient, auth_headers: dict[str, str], monkeypatch
    ):
        """Test synthesis fails gracefully when ElevenLabs API key is missing."""
        # Arrange - Mock the VoiceService to simulate missing API key error
        from unittest.mock import AsyncMock

        from app.services.exceptions import TTSError
        from app.services.voice_service import VoiceService

        # Mock synthesize_speech to raise TTSError (simulating missing API key)
        mock_service = AsyncMock(spec=VoiceService)
        mock_service.synthesize_speech.side_effect = TTSError(
            "TTS processing failed: API key is missing or invalid"
        )

        # Patch the dependency injection
        from app.api.v1.routers import voice

        def get_mock_voice_service() -> VoiceService:
            return mock_service  # type: ignore[return-value]

        monkeypatch.setattr(voice, "get_voice_service", get_mock_voice_service)

        payload = {"text": "Hello"}

        # Act
        response = await async_client.post(
            "/api/v1/voice/synthesize",
            json=payload,
            headers=auth_headers,
        )

        # Assert - Should return 502 Bad Gateway (TTS service unavailable)
        assert response.status_code == 502
        data = response.json()
        assert "detail" in data
        # Should indicate TTS error
        assert "tts" in data["detail"].lower() or "failed" in data["detail"].lower()


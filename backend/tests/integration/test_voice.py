"""Integration tests for voice STT endpoint with real database."""

from io import BytesIO

import pytest
from httpx import AsyncClient


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
        assert "not supported" in data["detail"].lower() or "unsupported" in data["detail"].lower()

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
        assert "exceeds" in data["detail"].lower() or "25" in data["detail"]

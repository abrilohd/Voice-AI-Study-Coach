"""Voice routes for speech-to-text transcription using Groq Whisper."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.core.dependencies import get_current_user, limiter
from app.models.user import User
from app.schemas.voice import TranscribeResponse
from app.services.exceptions import AudioProcessingError, TranscriptionError
from app.services.voice_service import VoiceService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


def get_voice_service() -> VoiceService:
    """Dependency injection for VoiceService."""
    return VoiceService()


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio to text using Groq Whisper",
)
@limiter.limit("20/minute")
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    voice_service: VoiceService = Depends(get_voice_service),
) -> TranscribeResponse:
    """
    Convert audio file to text using Groq Whisper API.

    Rate limit: 20 requests per minute per user.

    Accepts audio files up to 25MB in formats: webm, mp3, mp4, m4a, wav, ogg, flac.

    Args:
        request: FastAPI request object (required for rate limiting)
        file: Uploaded audio file (multipart/form-data)
        current_user: Authenticated user from JWT token
        voice_service: Voice service for transcription

    Returns:
        TranscribeResponse with transcribed text

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 422 if file format unsupported or file too large
        HTTPException: 502 if transcription service unavailable
        HTTPException: 429 if rate limit exceeded
    """
    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required",
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to read uploaded file",
        )

    # Transcribe audio
    try:
        text = await voice_service.transcribe(file_content, file.filename)
        return TranscribeResponse(text=text)

    except AudioProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    except TranscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

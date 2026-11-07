"""Voice routes for speech-to-text and text-to-speech."""

import logging
import os

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.core.dependencies import (
    get_current_user,
    limiter,
)
from app.models.user import User
from app.schemas.voice import SynthesizeRequest, TranscribeResponse
from app.services.exceptions import (
    AudioProcessingError,
    TranscriptionError,
    TTSError,
)
from app.services.voice_service import VoiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


def get_voice_service() -> VoiceService:
    """Dependency injection for VoiceService."""
    return VoiceService()


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio to text using Whisper",
)
@limiter.limit("20/minute")  # Voice operations are expensive
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    voice_service: VoiceService = Depends(get_voice_service),
) -> TranscribeResponse:
    """
    Convert audio file to text using local Whisper model.

    Rate limit: 20 requests per minute per user.

    Accepts audio files up to 25MB in formats: WebM, MP3, WAV, M4A, OGG.
    Uses Whisper "base" model for fast, accurate transcription.

    Args:
        request: FastAPI request object (required for rate limiting)
        file: Uploaded audio file (multipart/form-data)
        current_user: Authenticated user from JWT token
        voice_service: Voice service for transcription

    Returns:
        TranscribeResponse with transcribed text and duration hint

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 422 if file format unsupported or file too large
        HTTPException: 422 if transcription fails
        HTTPException: 429 if rate limit exceeded
    """
    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required",
        )

    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    supported_formats = voice_service.get_supported_formats()

    if file_ext not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type {file_ext} not supported. Allowed: {', '.join(supported_formats)}",
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

    # Check file size
    file_size_bytes = len(file_content)
    max_size_bytes = voice_service.MAX_AUDIO_SIZE_BYTES

    if file_size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File size exceeds maximum of {max_size_bytes // (1024 * 1024)}MB",
        )

    # Transcribe audio
    try:
        text = await voice_service.transcribe_audio(file_content, file.filename)

        # Estimate duration hint based on file size
        # Rough estimate: 1MB ≈ 60s for typical speech audio
        duration_seconds = file_size_bytes / (1024 * 1024) * 60

        if duration_seconds < 10:
            duration_hint = "short"
        elif duration_seconds < 30:
            duration_hint = "medium"
        else:
            duration_hint = "long"

        return TranscribeResponse(text=text, duration_hint=duration_hint)

    except AudioProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    except TranscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post(
    "/synthesize",
    status_code=status.HTTP_200_OK,
    summary="Synthesize speech from text using ElevenLabs",
    response_class=StreamingResponse,
)
@limiter.limit("20/minute")  # Voice operations are expensive
async def synthesize_speech(
    request: Request,
    synthesis_request: SynthesizeRequest,
    current_user: User = Depends(get_current_user),
    voice_service: VoiceService = Depends(get_voice_service),
) -> StreamingResponse:
    """
    Convert text to speech using ElevenLabs API.

    Rate limit: 20 requests per minute per user.

    Accepts text up to 5000 characters (ElevenLabs free tier limit).
    Returns MP3 audio stream ready for browser playback.

    Args:
        request: FastAPI request object (required for rate limiting)
        synthesis_request: Request body with text and optional voice_id
        current_user: Authenticated user from JWT token
        voice_service: Voice service for TTS

    Returns:
        StreamingResponse with MP3 audio (audio/mpeg)

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 502 if ElevenLabs API fails
        HTTPException: 429 if rate limit exceeded
    """
    try:
        # Synthesize speech
        audio_bytes = await voice_service.synthesize_speech(
            text=synthesis_request.text,
            voice_id=synthesis_request.voice_id,
        )

        # Return audio as streaming response
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline",  # Browser can play directly
            },
        )

    except TTSError as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

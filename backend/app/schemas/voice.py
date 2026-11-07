"""Voice API request/response schemas."""

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Response from transcription endpoint."""

    text: str = Field(description="Transcribed text from audio")
    duration_hint: str = Field(
        description="Estimated audio duration category: short (<10s), medium (10-30s), long (>30s)"
    )


class SynthesizeRequest(BaseModel):
    """Request to synthesize speech from text."""

    text: str = Field(max_length=5000, description="Text to convert to speech")
    voice_id: str | None = Field(
        default=None, description="Optional voice ID to override default"
    )

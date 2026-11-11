"""Voice API request/response schemas."""

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Response from transcription endpoint."""

    text: str = Field(description="Transcribed text from audio")

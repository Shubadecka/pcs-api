"""Schemas for transcription processing."""

from datetime import date
from pydantic import BaseModel, Field


class ParsedEntry(BaseModel):
    """A single journal entry parsed from raw OCR text."""

    entry_date: date = Field(..., description="The date this entry was written")
    raw_ocr_transcription: str = Field(..., description="The raw OCR transcribed text for this entry")
    embedding: list[float] | None = Field(None, description="Vector embedding of the transcription")


class TranscriptionResult(BaseModel):
    """The output of the transcription processing service."""

    entries: list[ParsedEntry] = Field(
        default_factory=list,
        description="Ordered list of date-labelled entries parsed from a single page",
    )

"""Transcription processing service implementation."""

import json
import logging
from datetime import date
from typing import Any

from app.interfaces.services.transcription_processing import ITranscriptionProcessingService
from app.schemas.transcription import ParsedEntry, TranscriptionResult
from app.core.ollama_utils import ollama

logger = logging.getLogger("transcription_processing")


class TranscriptionProcessingService(ITranscriptionProcessingService):
    """Splits raw OCR text from a journal page into individual dated entries."""

    async def process(self, raw_text: str, page_date: date) -> TranscriptionResult:
        split_response = await self._split_page(page_date, raw_text)
        entries: list[dict[str, Any]] = json.loads(split_response)
        entries = await self._embed_entries(entries)
        return TranscriptionResult(entries=[ParsedEntry(**e) for e in entries])

    async def _split_page(self, page_date: date, raw_text: str) -> str:
        """Ask the response model to split OCR text into dated entries as JSON."""
        prompt = f"""You are part of a system processing journal pages. Your task is to split the raw OCR text from a journal page into individual dated entries.
The page date is {page_date}.
The raw OCR text is:
{raw_text}

Return ONLY a valid JSON array with no commentary. Each element must have exactly these two keys:
  "entry_date": the date of the entry in the format YYYY-MM-DD
  "transcription": the full text of that entry

Example:
[
  {{"entry_date": "2024-01-15", "transcription": "Today I went for a walk..."}},
  {{"entry_date": "2024-01-16", "transcription": "Woke up early..."}}
]"""
        return await ollama.generate(prompt)

    async def _embed_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add a vector embedding to each entry dict."""
        for entry in entries:
            entry["embedding"] = await ollama.embed(entry["transcription"])
        return entries

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
        logger.info("Transcription process starting (page_date=%s, raw_text_len=%d)", page_date, len(raw_text or ""))
        split_response = await self._split_page(page_date, raw_text)
        if split_response is None:
            logger.error(
                "Split step returned None. Check that RESPONSE_MODEL is set and Ollama is reachable; see ollama logs above."
            )
            raise ValueError(
                "Transcription split returned no response. Ensure RESPONSE_MODEL is set in .env and the Ollama service is running."
            )
        logger.info("Split response received (%d chars)", len(split_response))
        cleaned = self._strip_markdown_fences(split_response)
        try:
            entries: list[dict[str, Any]] = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Split response is not valid JSON: %s. First 500 chars: %r", e, cleaned[:500])
            raise
        logger.info("Parsed %d entries, embedding next", len(entries))
        entries = await self._embed_entries(entries)
        logger.info("Transcription process completed (%d entries)", len(entries))
        return TranscriptionResult(entries=[ParsedEntry(**e) for e in entries])

    async def _split_page(self, page_date: date, raw_text: str) -> str | None:
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
        logger.debug("Calling response model to split page (prompt_len=%d)", len(prompt))
        split_response = await ollama.generate(prompt)
        print(f"split prompt: {prompt}")
        print(f"split_response: {split_response}")
        return split_response

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove markdown code fences that LLMs often wrap JSON output in."""
        stripped = text.strip()
        if stripped.startswith("```"):
            # Drop the opening fence line (e.g. ```json or just ```)
            stripped = stripped[stripped.index("\n") + 1:] if "\n" in stripped else stripped[3:]
            # Drop the closing fence if present
            if stripped.endswith("```"):
                stripped = stripped[:-3]
        return stripped.strip()

    async def _embed_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add a vector embedding to each entry dict."""
        for entry in entries:
            entry["embedding"] = await ollama.embed(entry["transcription"])
        return entries

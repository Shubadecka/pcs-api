"""Transcription processing service implementation."""

from datetime import date

from app.interfaces.services.transcription_processing import ITranscriptionProcessingService
from app.schemas.transcription import TranscriptionResult
from app.core.ollama_utils import ollama


class TranscriptionProcessingService(ITranscriptionProcessingService):
    """Splits raw OCR text from a journal page into individual dated entries."""

    async def process(self, raw_text: str, page_date: date) -> TranscriptionResult:
        """
        Process the raw OCR text from a journal page into individual dated entries.

        Args:
            raw_text: The raw OCR text from the journal page.
            page_date: The date of the journal page.

        Returns:
            A TranscriptionResult containing the parsed and embedded entries.
        """

        split_response = await self._split_page(page_date, raw_text)
        entries = json.loads(split_response)
        embedded_entries = await self._embed_entries(entries)
        return TranscriptionResult(entries=embedded_entries)

    async def _split_page(self, page_date: date, raw_text: str) -> str:
        """
        Get a response from the ollama model.

        Args:
            prompt: The prompt to send to the ollama model.

        Returns:
            The response from the ollama model. If the response is not valid JSON, an exception is raised.
        """
        prompt = f"""
        You are part of a system processing journal pages. Your task is to split the raw OCR text from a journal page into individual dated entries.
        The page date is {page_date}.
        The raw OCR text is:
        {raw_text}

        Return the entries as a list of dictionaries, each containing the entry date and transcription.
        The entries should be in the following format:
        [
            {
                "entry_date": "date of the entry in the format YYYY-MM-DD",
                "transcription": "This is the transcription of the entry"
            },
            {
                "entry_date": "date of the entry in the format YYYY-MM-DD",
                "transcription": "This is the transcription of the entry"
            }
        ]
        """
        return await ollama.generate(settings.processing_model, prompt)

    
    async def _embed_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Embed the entries using the ollama model.

        Args:
            entries: The list of entries to embed.

        Returns:
            The list of embedded entries.
        """
        for entry in entries:
            embedding = await ollama.embed(settings.embedding_model, entry["transcription"])
            entry["embedding"] = embedding
        return entries
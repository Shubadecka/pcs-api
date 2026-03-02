"""Interface for the transcription processing service."""

from abc import ABC, abstractmethod
from datetime import date

from app.schemas.transcription import TranscriptionResult


class ITranscriptionProcessingService(ABC):
    """Abstract base class for splitting raw OCR text into dated journal entries."""

    @abstractmethod
    async def process(self, raw_text: str, page_date: date) -> TranscriptionResult:
        """
        Parse raw OCR text from a single page into one or more dated entries.

        Args:
            raw_text: The full transcribed text returned by the OCR model.
            page_date: The upload date of the page, used as a fallback when
                       entry dates cannot be inferred from the text itself.

        Returns:
            A TranscriptionResult containing the parsed entries in order.
        """
        ...

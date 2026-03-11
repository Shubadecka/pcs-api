"""Pre-loop OCR error identification pass for the agentic cleanup layer."""

import logging
from pathlib import Path

from app.core.ollama_utils import ollama

logger = logging.getLogger("agentic_cleanup.error_detection")

_PROMPT_PATH = Path(__file__).parent / "prompts" / "error_detection.md"


def _load_prompt(raw_text: str) -> str:
    """Load the error detection prompt template and inject the entry text."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{raw_text}", raw_text)


async def detect_errors(raw_text: str) -> str:
    """Identify likely OCR errors in raw_text using the response model.

    Runs a single generate() call with the error_detection prompt. The result
    is a plain-text analysis listing suspected errors, intended to seed the
    agent's initial context so it knows where to focus.

    Args:
        raw_text: The raw OCR transcription to analyse

    Returns:
        Plain-text error analysis string, or an empty string if the model is
        unavailable or the call fails (the agent loop will proceed without it).
    """
    prompt = _load_prompt(raw_text)
    result = await ollama.generate(prompt)

    if not result:
        logger.warning("Error detection returned no result — proceeding without pre-analysis")
        return ""

    logger.debug("Error detection completed (%d chars)", len(result))
    return result

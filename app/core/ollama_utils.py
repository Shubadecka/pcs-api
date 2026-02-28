"""Centralized Ollama API client."""

import base64
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("ollama")

_OCR_PROMPT = (
    "Transcribe all text visible in this image exactly as written. "
    "Output only the transcribed text with no commentary."
)


class OllamaClient:
    """Async client for the local Ollama instance.

    Each method reads its model from settings:
        ocr(file_path)   — uses settings.ocr_model
        generate(prompt) — uses settings.response_model
        embed(text)      — uses settings.embedding_model

    Returns None (and logs a warning) when the required model is not
    configured or when the request fails.
    """

    @property
    def _base_url(self) -> str:
        return f"http://{settings.ollama_host}:{settings.ollama_port}"

    async def _post(self, endpoint: str, payload: dict) -> dict:
        """POST to an Ollama endpoint and return the parsed JSON response."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self._base_url}{endpoint}", json=payload)
            response.raise_for_status()
            return response.json()

    async def ocr(self, file_path: str) -> str | None:
        """Transcribe text from an image file using settings.ocr_model.

        Returns the transcribed text, or None if not configured or on failure.
        """
        if not settings.ocr_model:
            return None

        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": settings.ocr_model,
                "prompt": _OCR_PROMPT,
                "images": [image_data],
                "stream": False,
            }
            data = await self._post("/api/generate", payload)
            return data.get("response", "").strip() or None
        except Exception as exc:
            logger.warning("OCR failed for %s: %s", file_path, exc)
            return None

    async def generate(self, prompt: str) -> str | None:
        """Get a text response from settings.response_model.

        Returns the response string, or None if not configured or on failure.
        """
        if not settings.response_model:
            return None

        try:
            payload = {
                "model": settings.response_model,
                "prompt": prompt,
                "stream": False,
            }
            data = await self._post("/api/generate", payload)
            return data.get("response", "").strip() or None
        except Exception as exc:
            logger.warning("Generate failed: %s", exc)
            return None

    async def embed(self, text: str) -> list[float] | None:
        """Get a vector embedding for a text string using settings.embedding_model.

        Returns the embedding vector, or None if not configured or on failure.
        """
        if not settings.embedding_model:
            return None

        try:
            payload = {
                "model": settings.embedding_model,
                "input": text,
            }
            data = await self._post("/api/embed", payload)
            embeddings = data.get("embeddings", [])
            return embeddings[0] if embeddings else None
        except Exception as exc:
            logger.warning("Embed failed: %s", exc)
            return None


ollama = OllamaClient()

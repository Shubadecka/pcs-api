"""Centralized Ollama API client."""

import base64
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("ollama")


class OllamaClient:
    """Async client for the local Ollama instance.

    Public methods:
        ocr(file_path)          — extract text from an image file
        generate(model, prompt) — get a text response from a generative model
        embed(model, text)      — get a vector embedding for a string
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
        """Transcribe text from an image file using the configured OCR model.

        Returns the transcribed text, or None if OCR is not configured or fails.
        """
        if not settings.ocr_model:
            return None

        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": settings.ocr_model,
                "images": [image_data],
                "stream": False,
            }
            data = await self._post("/api/generate", payload)
            return data.get("response", "").strip() or None
        except Exception as exc:
            logger.warning("OCR failed for %s: %s", file_path, exc)
            return None

    async def generate(self, model: str, prompt: str) -> str | None:
        """Get a text response from an Ollama generative model.

        Returns the response string, or None on failure.
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
            }
            data = await self._post("/api/generate", payload)
            return data.get("response", "").strip() or None
        except Exception as exc:
            logger.warning("Generate failed (model=%s): %s", model, exc)
            return None

    async def embed(self, model: str, text: str) -> list[float] | None:
        """Get a vector embedding for a text string from an Ollama embedding model.

        Returns the embedding vector, or None on failure.
        """
        try:
            payload = {
                "model": model,
                "input": text,
            }
            data = await self._post("/api/embed", payload)
            embeddings = data.get("embeddings", [])
            return embeddings[0] if embeddings else None
        except Exception as exc:
            logger.warning("Embed failed (model=%s): %s", model, exc)
            return None


ollama = OllamaClient()

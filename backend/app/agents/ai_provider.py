import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger

class BaseAIProvider(ABC):
    @abstractmethod
    async def analyze_application_map(self, prompt: str) -> Dict[str, Any]:
        """Analyzes application map text and returns parsed JSON dictionary conforming to AIAnalysisOutput."""
        pass

class GeminiProvider(BaseAIProvider):
    """Integrates directly with Google Gemini REST API using structured JSON output mode."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL

    async def analyze_application_map(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in environment.")

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        logger.info(f"Dispatching AI analysis request to Gemini model: {self.model}...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(endpoint, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Gemini API returned HTTP {response.status_code}: {response.text}")
                raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text}")

            res_json = response.json()
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini returned an empty candidate list.")

            content_text = candidates[0]["content"]["parts"][0]["text"]
            parsed_data = json.loads(content_text)
            return parsed_data


class DeterministicFallbackProvider(BaseAIProvider):
    """High-reliability deterministic QA reasoning engine used when external LLM is offline."""

    async def analyze_application_map(self, prompt: str) -> Dict[str, Any]:
        logger.info("Using Deterministic QA reasoning engine for analysis...")
        # Will be called with raw structured app map inside the analyzer
        return {}


def get_ai_provider() -> BaseAIProvider:
    """Factory returning the active AI provider based on configuration."""
    if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider()
    logger.warning("Gemini API key not configured or provider set to fallback. Using deterministic provider.")
    return DeterministicFallbackProvider()

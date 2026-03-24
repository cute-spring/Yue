from typing import Any, Dict, Optional

from app.services.config_service import config_service
from app.services.llm.utils import build_async_client, get_ssl_verify


def _normalize_openai_base_url(base_url: Optional[str]) -> str:
    cleaned = (base_url or "").strip()
    if not cleaned:
        return "https://api.openai.com/v1"
    return cleaned.rstrip("/")


class SpeechService:
    async def synthesize_openai(
        self,
        *,
        text: str,
        voice: str,
        model: str,
        audio_format: str = "mp3",
    ) -> bytes:
        llm_config: Dict[str, Any] = config_service.get_llm_config()
        api_key = llm_config.get("openai_api_key")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        base_url = _normalize_openai_base_url(llm_config.get("openai_base_url"))
        verify = get_ssl_verify()
        payload = {
            "model": model,
            "voice": voice,
            "input": text,
            "format": audio_format,
        }
        async with build_async_client(timeout=60.0, verify=verify, llm_config=llm_config) as client:
            response = await client.post(
                f"{base_url}/audio/speech",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            return response.content


speech_service = SpeechService()

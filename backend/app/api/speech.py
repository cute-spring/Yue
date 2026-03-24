from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.speech_service import speech_service

router = APIRouter()


class SpeechSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1200)
    engine: Literal["openai"] = "openai"
    voice: str = "alloy"
    model: str = "gpt-4o-mini-tts"
    format: Literal["mp3", "wav"] = "mp3"


@router.post("/synthesize")
async def synthesize(payload: SpeechSynthesizeRequest):
    if payload.engine != "openai":
        raise HTTPException(status_code=400, detail="unsupported_speech_engine")
    try:
        audio = await speech_service.synthesize_openai(
            text=payload.text,
            voice=payload.voice,
            model=payload.model,
            audio_format=payload.format,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"speech_synthesis_failed: {e}")

    media_type = "audio/mpeg" if payload.format == "mp3" else "audio/wav"
    return Response(content=audio, media_type=media_type)

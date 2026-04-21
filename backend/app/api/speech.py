from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Literal

from app.services.agent_store import agent_store
from app.services.speech_service import speech_service

router = APIRouter()


class SpeechSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1200)
    engine: Literal["openai"] = "openai"
    voice: str = "alloy"
    model: str = "gpt-4o-mini-tts"
    format: Literal["mp3", "wav"] = "mp3"


class SpeechSttTokenResponse(BaseModel):
    provider: Literal["azure"] = "azure"
    token: str
    region: str
    endpoint_id: str = ""
    expires_in_seconds: int = 540


class SpeechSttTestRequest(BaseModel):
    provider: Literal["azure"] = "azure"
    region: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    endpoint_id: str = ""


class SpeechSttTestResponse(BaseModel):
    provider: Literal["azure"] = "azure"
    ok: bool = True
    region: str
    endpoint_id: str = ""


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


@router.get("/stt/token", response_model=SpeechSttTokenResponse)
async def issue_stt_token(agent_id: str = Query(..., min_length=1)):
    agent = agent_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent_not_found")
    if getattr(agent, "voice_input_enabled", True) is False:
        raise HTTPException(status_code=400, detail="voice_input_disabled")
    if getattr(agent, "voice_input_provider", "browser") != "azure":
        raise HTTPException(status_code=400, detail="unsupported_voice_input_provider")

    azure_cfg = getattr(agent, "voice_azure_config", None) or {}
    if not isinstance(azure_cfg, dict):
        azure_cfg = {}
    region = str(azure_cfg.get("region") or "").strip()
    api_key = str(azure_cfg.get("api_key") or "").strip()
    endpoint_id = str(azure_cfg.get("endpoint_id") or "").strip()

    if not region or not api_key:
        raise HTTPException(status_code=400, detail="azure_speech_not_configured")

    try:
        token = await speech_service.issue_azure_stt_token(region=region, api_key=api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"speech_stt_token_failed: {e}")

    return SpeechSttTokenResponse(token=token, region=region, endpoint_id=endpoint_id)


@router.post("/stt/test", response_model=SpeechSttTestResponse)
async def test_stt_config(payload: SpeechSttTestRequest):
    if payload.provider != "azure":
        raise HTTPException(status_code=400, detail="unsupported_stt_provider")
    try:
        await speech_service.issue_azure_stt_token(region=payload.region, api_key=payload.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"speech_stt_test_failed: {e}")
    return SpeechSttTestResponse(region=payload.region, endpoint_id=payload.endpoint_id)

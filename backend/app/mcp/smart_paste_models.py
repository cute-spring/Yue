from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, confloat


class SmartPasteRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=8000)


class ParsedServerConfig(BaseModel):
    name: str
    transport: Literal["stdio", "streamable_http"]
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: bool = False
    timeout: float = 60.0
    min_version: Optional[str] = None
    confidence: confloat(ge=0.0, le=1.0)
    hints: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    source_index: Optional[int] = None


class SmartPasteLlmEnvelope(BaseModel):
    results: List[ParsedServerConfig] = Field(default_factory=list)


class SmartPasteResponse(BaseModel):
    ok: bool
    results: List[ParsedServerConfig] = Field(default_factory=list)
    parse_mode: Literal["rule", "ai", "hybrid"] = "ai"
    error: Optional[str] = None

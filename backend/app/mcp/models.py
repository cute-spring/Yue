from typing import List, Dict, Any, Optional
from pydantic import BaseModel, field_validator

class ServerConfig(BaseModel):
    name: str
    transport: str = "stdio"
    command: str
    args: List[str] = []
    enabled: bool = True
    env: Optional[Dict[str, str]] = None
    timeout: float = 60.0
    min_version: Optional[str] = None

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str):
        if v not in {"stdio"}:
            raise ValueError("unsupported transport")
        return v

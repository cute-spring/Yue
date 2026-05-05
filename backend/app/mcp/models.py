from typing import List, Dict, Any, Optional
from pydantic import BaseModel, model_validator
from urllib.parse import urlparse

class ServerConfig(BaseModel):
    name: str
    transport: str = "stdio"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    enabled: bool = True
    env: Optional[Dict[str, str]] = None
    timeout: float = 60.0
    min_version: Optional[str] = None

    @model_validator(mode="after")
    def validate_transport_contract(self):
        if self.transport not in {"stdio", "streamable_http"}:
            raise ValueError("unsupported transport")
        if self.transport == "stdio":
            if not self.command:
                raise ValueError("stdio transport requires command")
            if self.url is not None or self.headers is not None:
                raise ValueError("stdio transport does not allow url/headers")
        if self.transport == "streamable_http":
            if not self.url:
                raise ValueError("streamable_http transport requires url")
            if self.command is not None or self.args is not None:
                raise ValueError("streamable_http transport does not allow command/args")
            parsed = urlparse(self.url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("streamable_http transport requires a valid url")
        return self

from typing import Any, Dict, Optional
import copy


def _normalize_schema(parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(parameters, dict):
        return {"type": "object", "properties": {}}
    normalized = copy.deepcopy(parameters)
    schema_type = normalized.get("type")
    if schema_type is None:
        normalized["type"] = "object"
        schema_type = "object"
    if schema_type != "object":
        return {"type": "object", "properties": {"value": normalized}}
    properties = normalized.get("properties")
    if not isinstance(properties, dict):
        normalized["properties"] = {}
    required = normalized.get("required")
    if required is None:
        return normalized
    if isinstance(required, (set, tuple)):
        normalized["required"] = list(required)
    elif isinstance(required, str):
        normalized["required"] = [required]
    elif not isinstance(required, list):
        normalized["required"] = list(required) if required else []
    return normalized


def to_provider_schema(provider: Optional[str], parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    provider_name = (provider or "").lower()
    schema = _normalize_schema(parameters)
    if provider_name in {"openai", "deepseek"}:
        return schema
    if provider_name == "claude":
        return schema
    return schema

import json
from pathlib import Path
from typing import Any, Dict, Optional

KNOWN_TRACE_EVENTS = {
    "skill_selected",
    "skill_effectiveness",
    "tool_call_retry",
    "tool_call_retry_success",
    "tool_call_retry_failed",
    "tool_call_mismatch",
    "run.limited",
    "reasoning_toggle_ignored",
}


def _contracts_root() -> Path:
    return Path(__file__).resolve().parents[2] / "contracts"


def load_contract_schema(surface: str, name: str) -> Dict[str, Any]:
    schema_path = _contracts_root() / surface / f"{name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"contract schema not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def classify_sse_event_kind(payload: Dict[str, Any]) -> str:
    if "meta" in payload:
        return "meta"
    if "content" in payload:
        return "content"
    if "error" in payload and "event" not in payload:
        return "error"
    event_name = payload.get("event")
    if isinstance(event_name, str) and event_name.startswith("tool."):
        return "tool_event"
    if isinstance(event_name, str) and (event_name in KNOWN_TRACE_EVENTS or event_name.startswith("trace.")):
        return "trace_event"
    return "unknown"


def should_ignore_unknown_event(payload: Dict[str, Any]) -> bool:
    return classify_sse_event_kind(payload) == "unknown"


def _is_type_match(expected_type: str, value: Any) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "null":
        return value is None
    return True


def _validate_by_schema(schema: Dict[str, Any], payload: Any, path: str = "$") -> None:
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        if not _is_type_match(schema_type, payload):
            raise ValueError(f"type mismatch at {path}: expected {schema_type}")
    elif isinstance(schema_type, list):
        if not any(_is_type_match(item_type, payload) for item_type in schema_type if isinstance(item_type, str)):
            raise ValueError(f"type mismatch at {path}: expected one of {schema_type}")

    if schema_type == "object":
        required_fields = schema.get("required", [])
        for key in required_fields:
            if key not in payload:
                raise ValueError(f"missing required field at {path}: {key}")

        props = schema.get("properties", {})
        for key, prop_schema in props.items():
            if key in payload:
                _validate_by_schema(prop_schema, payload[key], f"{path}.{key}")

    if schema_type == "array":
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(payload):
                _validate_by_schema(item_schema, item, f"{path}[{idx}]")

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and payload not in enum_values:
        raise ValueError(f"enum mismatch at {path}: {payload}")


def validate_event_payload(schema: Dict[str, Any], payload: Dict[str, Any]) -> None:
    _validate_by_schema(schema, payload)


def validate_sse_payload(payload: Dict[str, Any]) -> Optional[str]:
    kind = classify_sse_event_kind(payload)
    if kind == "unknown":
        return None
    schema = load_contract_schema("sse", kind)
    validate_event_payload(schema, payload)
    return kind

from __future__ import annotations

from typing import Any


class ToolResultNormalizer:
    def normalize(
        self,
        payload: dict[str, Any] | str,
        source: str | None = None,
        source_ref: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(payload, str):
            return {
                "normalized_content": payload.strip(),
                "key_fields": {},
                "ttl_seconds": None,
                "source": source or "tool",
                "source_ref": source_ref,
            }

        key_fields: dict[str, Any] = {}
        parts: list[str] = []
        for key in sorted(payload.keys()):
            value = payload[key]
            if value is None:
                continue
            key_fields[key] = value
            parts.append(f"{key}: {value}")
        normalized = "\n".join(parts).strip()

        return {
            "normalized_content": normalized,
            "key_fields": key_fields,
            "ttl_seconds": payload.get("ttl_seconds"),
            "source": source or str(payload.get("source", "tool")),
            "source_ref": source_ref if source_ref is not None else payload.get("source_ref"),
        }

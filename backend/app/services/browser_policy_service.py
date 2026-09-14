"""Durable, local-owner policy for browser collaboration origins.

This store deliberately contains only canonical origins and policy decisions.
It must never receive browser cookies, extension tokens, page content, or other
authentication material.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4


class BrowserPolicyError(ValueError):
    """A policy error that is safe to expose to the local owner."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_https_origin(value: str) -> str:
    if not isinstance(value, str):
        raise BrowserPolicyError("origin must be a string.")
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise BrowserPolicyError("origin must be an exact https origin.")
    if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise BrowserPolicyError("origin must not include credentials, a path, query, or fragment.")
    if "*" in parsed.netloc:
        raise BrowserPolicyError("origin must not contain a wildcard.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise BrowserPolicyError("origin contains an invalid port.") from exc
    if port is not None and not 1 <= port <= 65535:
        raise BrowserPolicyError("origin contains an invalid port.")
    canonical = f"https://{parsed.netloc}".lower()
    if value.strip().rstrip("/").lower() != canonical:
        raise BrowserPolicyError("origin must be a canonical exact https origin.")
    return canonical


class BrowserPolicyService:
    """A JSON-backed policy store owned by the local Yue user."""

    _PURPOSES = {"business", "sso_handoff"}
    _POLICY_VERSION = 1

    def __init__(self, policy_path: str | Path | None = None) -> None:
        if policy_path is None:
            data_dir = Path(os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")))
            policy_path = data_dir / "browser_origin_policy.json"
        self.policy_path = Path(policy_path)
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._suppress_writes = False
        self._requests: dict[str, dict[str, Any]] = {}
        self._origins: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.policy_path.exists():
            return
        try:
            payload = json.loads(self.policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BrowserPolicyError("Browser origin policy could not be read.") from exc
        payload = self._migrate_payload(payload)
        for record in payload["origins"]:
            if not isinstance(record, dict):
                continue
            try:
                origin = canonical_https_origin(record.get("origin"))
            except BrowserPolicyError:
                continue
            purpose = record.get("purpose")
            if purpose in self._PURPOSES:
                self._origins[origin] = {"origin": origin, "purpose": purpose, "approved_at": record.get("approved_at")}

    def _migrate_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise BrowserPolicyError("Browser origin policy has an invalid format.")
        version = payload.get("version", 0)
        if version == 0:
            origins = payload.get("origins", [])
            if not isinstance(origins, list):
                raise BrowserPolicyError("Browser origin policy has an invalid legacy format.")
            return {"version": self._POLICY_VERSION, "origins": origins}
        if version != self._POLICY_VERSION:
            raise BrowserPolicyError("Browser origin policy version is unsupported.")
        origins = payload.get("origins", [])
        if not isinstance(origins, list):
            raise BrowserPolicyError("Browser origin policy has an invalid format.")
        return {"version": version, "origins": origins}

    def _save(self) -> None:
        if self._suppress_writes:
            return
        payload = {"version": self._POLICY_VERSION, "origins": self.list_origins()}
        temporary_path = self.policy_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_path, self.policy_path)

    def list_origins(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(record) for record in sorted(self._origins.values(), key=lambda item: item["origin"])]

    def request_origin(self, *, origin: str, purpose: str) -> dict[str, Any]:
        normalized = canonical_https_origin(origin)
        if purpose not in self._PURPOSES:
            raise BrowserPolicyError("purpose must be business or sso_handoff.")
        with self._lock:
            request = {
                "id": f"browser_origin_request_{uuid4().hex}",
                "origin": normalized,
                "purpose": purpose,
                "status": "awaiting_approval",
                "created_at": _utc_now().isoformat(),
            }
            self._requests[request["id"]] = request
            return dict(request)

    def decide_origin_request(self, *, request_id: str, approved: bool) -> dict[str, Any]:
        with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                raise BrowserPolicyError("Browser origin request not found.")
            if request["status"] != "awaiting_approval":
                raise BrowserPolicyError("Browser origin request has already been decided.")
            request["status"] = "approved" if approved else "rejected"
            request["decided_at"] = _utc_now().isoformat()
            if approved:
                self._origins[request["origin"]] = {
                    "origin": request["origin"],
                    "purpose": request["purpose"],
                    "approved_at": request["decided_at"],
                }
                self._save()
            return dict(request)

    def revoke_origin(self, *, origin: str) -> None:
        normalized = canonical_https_origin(origin)
        with self._lock:
            if normalized not in self._origins:
                raise BrowserPolicyError("Browser origin is not allowed.")
            del self._origins[normalized]
            self._save()

    def purpose_for(self, origin: str) -> str | None:
        normalized = canonical_https_origin(origin)
        with self._lock:
            record = self._origins.get(normalized)
            return record["purpose"] if record else None

    def require_business_origin(self, origin: str) -> None:
        if self.purpose_for(origin) != "business":
            raise BrowserPolicyError("The origin is not approved for browser collaboration.")

    def replace_origins_for_tests(self, records: list[dict[str, str]]) -> None:
        """Install an in-memory policy fixture without writing a user policy file."""
        with self._lock:
            self._suppress_writes = True
            self._origins = {}
            for record in records:
                origin = canonical_https_origin(record["origin"])
                purpose = record["purpose"]
                if purpose not in self._PURPOSES:
                    raise BrowserPolicyError("purpose must be business or sso_handoff.")
                self._origins[origin] = {"origin": origin, "purpose": purpose, "approved_at": "test"}
            self._requests = {}


browser_policy_service = BrowserPolicyService()

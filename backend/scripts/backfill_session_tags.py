#!/usr/bin/env python3
"""Backfill session tags for existing chat history."""

from __future__ import annotations

import json
from typing import Tuple

from app.core.database import SessionLocal
from app.models.chat import Session as SessionModel
from app.services.chat_service import chat_service


def _has_tags(raw: str | None) -> bool:
    if not raw:
        return False
    try:
        parsed = json.loads(raw)
    except Exception:
        return False
    return isinstance(parsed, list) and len(parsed) > 0


def backfill_tags(only_missing: bool = True) -> Tuple[int, int]:
    scanned = 0
    updated = 0
    with SessionLocal() as db:
        sessions = db.query(SessionModel).all()

    for session in sessions:
        scanned += 1
        if only_missing and _has_tags(getattr(session, "tags_json", None)):
            continue
        tags = chat_service.generate_chat_tags(session.id)
        if tags is not None:
            updated += 1
            print(f"[updated] session={session.id} tags={tags}")

    return scanned, updated


if __name__ == "__main__":
    scanned_count, updated_count = backfill_tags(only_missing=True)
    print(f"[done] scanned={scanned_count} updated={updated_count}")

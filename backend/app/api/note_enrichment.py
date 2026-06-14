from typing import Any, Dict, List, Optional

from app.services.session_meta_service import session_meta_service


async def generate_note_enrichment(
    *,
    content: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    tags: Optional[List[str]] = None,
    note_type: Optional[str] = None,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    generated = await session_meta_service.generate_note_enrichment(
        content=content,
        title=title,
        summary=summary,
        tags=tags,
        note_type=note_type,
        source_metadata=source_metadata,
    )
    return generated or {}

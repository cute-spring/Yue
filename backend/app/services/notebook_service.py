import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError

from app.core.database import Base, SessionLocal, engine
from app.models.chat import WorkspaceNote as WorkspaceNoteModel

logger = logging.getLogger(__name__)

DATA_DIR = os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")

NOTE_TYPES = {
    "decision",
    "fact",
    "insight",
    "preference",
    "reference",
    "summary",
    "todo",
}
DEFAULT_NOTE_TYPE = "summary"

EN_TAG_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}
EN_TAG_SYNONYMS = {
    "authentication": "auth",
    "authorize": "auth",
    "authorization": "auth",
    "frontend": "ui-ux",
    "memory": "memory",
    "memories": "memory",
    "note": "note",
    "notes": "note",
    "notebook": "note",
    "prompt": "prompt",
    "prompts": "prompt",
    "retrieval": "recall",
    "workspace": "workspace",
}
ZH_TAG_STOPWORDS = {
    "一个",
    "一些",
    "这个",
    "这样",
    "这些",
    "那个",
    "那些",
    "以及",
    "还有",
    "因为",
    "所以",
    "然后",
    "如果",
    "需要",
    "可以",
    "我们",
    "你们",
    "他们",
}
ZH_TAG_KEYWORDS = {
    "标签": "标签",
    "笔记": "笔记",
    "工作区": "工作区",
    "计划": "计划",
    "记忆": "记忆",
    "需求": "需求",
    "设计": "设计",
    "总结": "总结",
    "摘要": "摘要",
    "来源": "来源",
    "标题": "标题",
    "回链": "回链",
    "召回": "召回",
    "上下文": "上下文",
    "功能": "功能",
    "项目": "项目",
    "决策": "决策",
    "偏好": "偏好",
    "实现": "实现",
    "架构": "架构",
    "保存": "保存",
}


class Note(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: Optional[str] = None
    title: str
    summary: str = ""
    content: str
    tags: List[str] = Field(default_factory=list)
    note_type: str = DEFAULT_NOTE_TYPE
    capture_type: str = "manual"
    status: str = "saved"
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    source_message_ids: List[int] = Field(default_factory=list)
    citation_refs: List[Dict[str, Any]] = Field(default_factory=list)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    promoted_memory_id: Optional[str] = None
    promotion_hint: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspacePromptNote(BaseModel):
    id: str
    title: str
    summary: str = ""
    content: str
    note_type: str = DEFAULT_NOTE_TYPE
    tags: List[str] = Field(default_factory=list)
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None


class WorkspaceNotePromptContext(BaseModel):
    workspace_id: str
    loaded_note_ids: List[str] = Field(default_factory=list)
    loaded_notes: List[WorkspacePromptNote] = Field(default_factory=list)
    prompt_block: str = ""


class NotebookService:
    def __init__(self):
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            Base.metadata.create_all(bind=engine)
        except OperationalError as exc:
            logger.warning("NotebookService create_all skipped due to database operational error: %s", exc)
        self._migrate_legacy_notes_if_needed()

    @staticmethod
    def _to_api_datetime(value: Optional[datetime]) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _parse_json_list(raw: Optional[str]) -> List[Any]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        return parsed if isinstance(parsed, list) else []

    @staticmethod
    def _parse_json_dict(raw: Optional[str]) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _normalize_tag(tag: str) -> str:
        cleaned = (tag or "").strip()
        if not cleaned:
            return ""
        if re.search(r"[\u4e00-\u9fff]", cleaned):
            cleaned = re.sub(r"\s+", "", cleaned)
            cleaned = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9_-]", "", cleaned)
            return cleaned[:12]
        lowered = cleaned.lower()
        lowered = EN_TAG_SYNONYMS.get(lowered, lowered)
        lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
        return lowered[:32]

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        seen: set[str] = set()
        normalized: List[str] = []
        for tag in tags:
            item = self._normalize_tag(tag)
            if not item:
                continue
            if item in EN_TAG_STOPWORDS or item in ZH_TAG_STOPWORDS:
                continue
            if item in seen:
                continue
            seen.add(item)
            normalized.append(item)
            if len(normalized) >= 8:
                break
        return normalized

    def _extract_en_tags(self, text: str) -> List[str]:
        hits: List[str] = []
        for word in re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b", text.lower()):
            normalized = EN_TAG_SYNONYMS.get(word, word)
            if normalized in EN_TAG_STOPWORDS:
                continue
            hits.append(normalized)
        return hits

    def _extract_zh_tags(self, text: str) -> List[str]:
        hits: List[str] = []
        for keyword, tag in ZH_TAG_KEYWORDS.items():
            if keyword in text:
                hits.append(tag)
        for chunk in re.findall(r"[\u4e00-\u9fff]{2,8}", text):
            if chunk in ZH_TAG_STOPWORDS:
                continue
            hits.append(chunk)
        return hits

    def _derive_tags_from_texts(self, texts: List[str]) -> List[str]:
        tags: List[str] = []
        for block in texts:
            if not block:
                continue
            tags.extend(self._extract_en_tags(block))
            tags.extend(self._extract_zh_tags(block))
        return self._normalize_tags(tags)

    @staticmethod
    def _strip_markdown_prefix(line: str) -> str:
        line = re.sub(r"^\s{0,3}(#{1,6}|\-|\*|\d+\.)\s*", "", line.strip())
        line = re.sub(r"^>\s*", "", line)
        return line.strip()

    def _derive_title(self, content: str, fallback_title: Optional[str] = None) -> str:
        if fallback_title and fallback_title.strip():
            return fallback_title.strip()[:80]
        for raw_line in content.splitlines():
            line = self._strip_markdown_prefix(raw_line)
            if not line:
                continue
            line = re.sub(r"\s+", " ", line).strip()
            return line[:80]
        compact = re.sub(r"\s+", " ", content).strip()
        return (compact[:80] or "Untitled Note").strip()

    def _derive_summary(self, content: str) -> str:
        compact = re.sub(r"\s+", " ", content).strip()
        if not compact:
            return ""
        sentences = re.split(r"(?<=[。！？.!?])\s+", compact)
        summary = " ".join([item.strip() for item in sentences[:2] if item.strip()])
        if not summary:
            summary = compact
        return summary[:180].strip()

    def _infer_note_type(self, title: str, content: str, source_metadata: Optional[Dict[str, Any]] = None) -> str:
        haystack = f"{title}\n{content}".lower()
        raw_haystack = f"{title}\n{content}"
        if any(token in haystack for token in ["todo", "follow up", "action item"]) or any(
            token in raw_haystack for token in ["待办", "下一步", "行动项"]
        ):
            return "todo"
        if any(token in haystack for token in ["prefer", "preference", "avoid"]) or any(
            token in raw_haystack for token in ["偏好", "希望", "不要", "倾向"]
        ):
            return "preference"
        if any(token in haystack for token in ["decision", "decide", "agreed", "chosen"]) or any(
            token in raw_haystack for token in ["决定", "结论", "采用", "定为", "确认"]
        ):
            return "decision"
        if any(token in haystack for token in ["reference", "citation", "source"]) or any(
            token in raw_haystack for token in ["参考", "引用", "来源"]
        ):
            return "reference"
        if source_metadata and source_metadata.get("captured_from") == "assistant_message":
            return "insight"
        if any(token in haystack for token in ["fact", "constraint"]) or any(
            token in raw_haystack for token in ["事实", "约束", "规则"]
        ):
            return "fact"
        return DEFAULT_NOTE_TYPE

    def _enrich_note_fields(
        self,
        *,
        title: Optional[str],
        summary: Optional[str],
        content: str,
        tags: Optional[List[str]],
        note_type: Optional[str],
        source_metadata: Optional[Dict[str, Any]] = None,
        preserve_title: bool = False,
    ) -> Dict[str, Any]:
        derived_title = title.strip() if title and title.strip() else ""
        if not derived_title or not preserve_title:
            derived_title = self._derive_title(content, fallback_title=derived_title or None)
        derived_summary = summary.strip() if isinstance(summary, str) else ""
        if not derived_summary:
            derived_summary = self._derive_summary(content)
        derived_tags = self._normalize_tags(tags or [])
        if not derived_tags:
            derived_tags = self._derive_tags_from_texts([derived_title, derived_summary, content])
        derived_note_type = (note_type or "").strip().lower()
        if derived_note_type not in NOTE_TYPES:
            derived_note_type = self._infer_note_type(derived_title, content, source_metadata)
        return {
            "title": derived_title or "Untitled Note",
            "summary": derived_summary,
            "tags": derived_tags,
            "note_type": derived_note_type or DEFAULT_NOTE_TYPE,
        }

    @staticmethod
    def _tokenize_query(text: Optional[str]) -> List[str]:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return []
        return [token for token in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", normalized) if len(token) >= 2]

    @staticmethod
    def _note_type_priority(note_type: Optional[str]) -> int:
        priority = {
            "preference": 0,
            "decision": 1,
            "fact": 2,
            "reference": 3,
            "insight": 4,
            "summary": 5,
            "todo": 6,
        }
        return priority.get(str(note_type or "").strip().lower(), 9)

    def _note_relevance_score(
        self,
        note: Note,
        *,
        current_query: Optional[str],
        query_tokens: List[str],
    ) -> int:
        base_score = 15 - self._note_type_priority(note.note_type)
        haystack = " ".join(
            [
                note.title or "",
                note.summary or "",
                note.content or "",
                " ".join(note.tags or []),
                json.dumps(note.source_metadata or {}, ensure_ascii=False),
            ]
        ).lower()
        query_text = str(current_query or "").strip().lower()
        if query_text and len(query_text) >= 4 and query_text in haystack:
            base_score += 6
        if query_tokens:
            base_score += sum(2 for token in query_tokens if token in haystack)
        if note.promoted_memory_id:
            base_score -= 4
        return base_score

    def _build_workspace_note_prompt_lines(
        self,
        notes: List[Note],
    ) -> tuple[List[WorkspacePromptNote], List[str]]:
        prompt_notes: List[WorkspacePromptNote] = []
        lines: List[str] = []
        for note in notes:
            prompt_note = WorkspacePromptNote(
                id=note.id,
                title=note.title,
                summary=note.summary,
                content=note.content,
                note_type=note.note_type,
                tags=list(note.tags or []),
                source_session_id=note.source_session_id,
                source_message_id=note.source_message_id,
            )
            prompt_notes.append(prompt_note)
            source_bits: List[str] = []
            if note.source_session_id:
                source_bits.append(f"chat={note.source_session_id}")
            if note.source_message_id is not None:
                source_bits.append(f"message={note.source_message_id}")
            if note.tags:
                source_bits.append(f"tags={','.join(note.tags[:4])}")
            source_suffix = f" ({'; '.join(source_bits)})" if source_bits else ""
            primary_text = note.summary.strip() or note.content.strip()
            lines.append(
                f"- {note.id} [{note.note_type}] {note.title}: {primary_text[:240]}{source_suffix}"
            )
        return prompt_notes, lines

    def _to_note(self, record: WorkspaceNoteModel) -> Note:
        return Note(
            id=record.id,
            workspace_id=record.workspace_id,
            title=record.title,
            summary=record.summary or "",
            content=record.content,
            tags=self._normalize_tags([str(item) for item in self._parse_json_list(record.tags_json) if isinstance(item, str)]),
            note_type=record.note_type or DEFAULT_NOTE_TYPE,
            capture_type=record.capture_type or "manual",
            status=record.status or "saved",
            source_session_id=record.source_session_id,
            source_message_id=record.source_message_id,
            source_message_ids=[
                int(item)
                for item in self._parse_json_list(record.source_message_ids_json)
                if isinstance(item, (int, float)) or (isinstance(item, str) and item.isdigit())
            ],
            citation_refs=[
                item for item in self._parse_json_list(record.citation_refs_json) if isinstance(item, dict)
            ],
            source_metadata=self._parse_json_dict(record.source_metadata_json),
            promoted_memory_id=record.promoted_memory_id,
            created_at=self._to_api_datetime(record.created_at),
            updated_at=self._to_api_datetime(record.updated_at),
        )

    def _migrate_legacy_notes_if_needed(self) -> None:
        if not os.path.exists(NOTES_FILE):
            return
        with SessionLocal() as db:
            existing_count = db.query(WorkspaceNoteModel).count()
            if existing_count > 0:
                return
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as handle:
                raw_notes = json.load(handle)
        except Exception:
            return
        if not isinstance(raw_notes, list) or not raw_notes:
            return
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            for item in raw_notes:
                if not isinstance(item, dict):
                    continue
                note_id = str(item.get("id") or uuid.uuid4())
                content = str(item.get("content") or "").strip()
                title = str(item.get("title") or "").strip()
                enriched = self._enrich_note_fields(
                    title=title,
                    summary=item.get("summary"),
                    content=content,
                    tags=item.get("tags") if isinstance(item.get("tags"), list) else None,
                    note_type=item.get("note_type"),
                )
                created_at_raw = item.get("created_at")
                updated_at_raw = item.get("updated_at")
                try:
                    created_at = self._to_api_datetime(datetime.fromisoformat(created_at_raw)) if created_at_raw else now
                except Exception:
                    created_at = now
                try:
                    updated_at = self._to_api_datetime(datetime.fromisoformat(updated_at_raw)) if updated_at_raw else created_at
                except Exception:
                    updated_at = created_at
                db.add(
                    WorkspaceNoteModel(
                        id=note_id,
                        workspace_id=item.get("workspace_id"),
                        title=enriched["title"],
                        summary=enriched["summary"],
                        content=content,
                        tags_json=json.dumps(enriched["tags"], ensure_ascii=False),
                        note_type=enriched["note_type"],
                        capture_type=str(item.get("capture_type") or "legacy_import"),
                        status=str(item.get("status") or "saved"),
                        source_session_id=item.get("source_session_id"),
                        source_message_id=item.get("source_message_id"),
                        source_message_ids_json=json.dumps(item.get("source_message_ids") or [], ensure_ascii=False),
                        citation_refs_json=json.dumps(item.get("citation_refs") or [], ensure_ascii=False),
                        source_metadata_json=json.dumps(item.get("source_metadata") or {"legacy_imported": True}, ensure_ascii=False),
                        promoted_memory_id=item.get("promoted_memory_id"),
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )
            db.commit()

    def list_notes(
        self,
        *,
        workspace_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        note_type: Optional[str] = None,
        capture_type: Optional[str] = None,
        source_session_id: Optional[str] = None,
    ) -> List[Note]:
        normalized_tags = self._normalize_tags(tags or [])
        with SessionLocal() as db:
            query = db.query(WorkspaceNoteModel)
            if workspace_id:
                query = query.filter(WorkspaceNoteModel.workspace_id == workspace_id)
            if note_type:
                query = query.filter(WorkspaceNoteModel.note_type == note_type)
            if capture_type:
                query = query.filter(WorkspaceNoteModel.capture_type == capture_type)
            if source_session_id:
                query = query.filter(WorkspaceNoteModel.source_session_id == source_session_id)
            rows = query.order_by(WorkspaceNoteModel.updated_at.desc(), WorkspaceNoteModel.created_at.desc()).all()

        notes = [self._to_note(row) for row in rows]
        if normalized_tags:
            notes = [note for note in notes if any(tag in note.tags for tag in normalized_tags)]
        return notes

    def get_note(self, note_id: str) -> Optional[Note]:
        with SessionLocal() as db:
            row = db.query(WorkspaceNoteModel).filter(WorkspaceNoteModel.id == note_id).first()
        return self._to_note(row) if row else None

    def build_prompt_context(
        self,
        workspace_id: Optional[str],
        *,
        current_query: Optional[str] = None,
    ) -> Optional[WorkspaceNotePromptContext]:
        if not workspace_id:
            return None

        notes = self.list_notes(workspace_id=workspace_id)
        if not notes:
            return None

        eligible_notes = [
            note
            for note in notes
            if str(note.status or "").strip().lower() != "archived" and not note.promoted_memory_id
        ]
        if not eligible_notes:
            return None

        query_tokens = self._tokenize_query(current_query)
        ranked_notes = sorted(
            eligible_notes,
            key=lambda note: (
                self._note_relevance_score(note, current_query=current_query, query_tokens=query_tokens),
                note.updated_at,
            ),
            reverse=True,
        )
        selected_notes = ranked_notes[:5]
        prompt_notes, note_lines = self._build_workspace_note_prompt_lines(selected_notes)
        lines = [
            "### Relevant Workspace Notes",
            "Use these saved workspace notes as lower-authority recall context. "
            "Prefer newer user instructions and reviewed workspace memory if they conflict.",
            *note_lines,
        ]
        return WorkspaceNotePromptContext(
            workspace_id=workspace_id,
            loaded_note_ids=[note.id for note in selected_notes],
            loaded_notes=prompt_notes,
            prompt_block="\n".join(lines).strip(),
        )

    def create_note(
        self,
        title: Optional[str],
        content: str,
        *,
        workspace_id: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        note_type: Optional[str] = None,
        capture_type: str = "manual",
        status: str = "saved",
        source_session_id: Optional[str] = None,
        source_message_id: Optional[int] = None,
        source_message_ids: Optional[List[int]] = None,
        citation_refs: Optional[List[Dict[str, Any]]] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        promoted_memory_id: Optional[str] = None,
    ) -> Note:
        enriched = self._enrich_note_fields(
            title=title,
            summary=summary,
            content=content,
            tags=tags,
            note_type=note_type,
            source_metadata=source_metadata,
        )
        now = datetime.now(timezone.utc)
        row = WorkspaceNoteModel(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            title=enriched["title"],
            summary=enriched["summary"],
            content=content,
            tags_json=json.dumps(enriched["tags"], ensure_ascii=False),
            note_type=enriched["note_type"],
            capture_type=(capture_type or "manual").strip() or "manual",
            status=(status or "saved").strip() or "saved",
            source_session_id=source_session_id,
            source_message_id=source_message_id,
            source_message_ids_json=json.dumps(source_message_ids or [], ensure_ascii=False),
            citation_refs_json=json.dumps(citation_refs or [], ensure_ascii=False),
            source_metadata_json=json.dumps(source_metadata or {}, ensure_ascii=False),
            promoted_memory_id=promoted_memory_id,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_note(row)

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        *,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        note_type: Optional[str] = None,
        capture_type: Optional[str] = None,
        status: Optional[str] = None,
        workspace_id: Optional[str] = None,
        source_session_id: Optional[str] = None,
        source_message_id: Optional[int] = None,
        source_message_ids: Optional[List[int]] = None,
        citation_refs: Optional[List[Dict[str, Any]]] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        promoted_memory_id: Optional[str] = None,
    ) -> Optional[Note]:
        with SessionLocal() as db:
            row = db.query(WorkspaceNoteModel).filter(WorkspaceNoteModel.id == note_id).first()
            if row is None:
                return None

            next_content = content if content is not None else row.content
            existing_metadata = self._parse_json_dict(row.source_metadata_json)
            merged_metadata = dict(existing_metadata)
            if source_metadata is not None:
                merged_metadata.update(source_metadata)

            enriched = self._enrich_note_fields(
                title=title if title is not None else row.title,
                summary=summary,
                content=next_content,
                tags=tags,
                note_type=note_type,
                source_metadata=merged_metadata,
                preserve_title=title is None,
            )

            if workspace_id is not None:
                row.workspace_id = workspace_id
            row.title = enriched["title"] if title is not None else row.title
            row.summary = enriched["summary"]
            row.content = next_content
            row.tags_json = json.dumps(enriched["tags"], ensure_ascii=False)
            row.note_type = enriched["note_type"]
            if capture_type is not None:
                row.capture_type = (capture_type or row.capture_type).strip() or row.capture_type
            if status is not None:
                row.status = (status or row.status).strip() or row.status
            if source_session_id is not None:
                row.source_session_id = source_session_id
            if source_message_id is not None:
                row.source_message_id = source_message_id
            if source_message_ids is not None:
                row.source_message_ids_json = json.dumps(source_message_ids, ensure_ascii=False)
            if citation_refs is not None:
                row.citation_refs_json = json.dumps(citation_refs, ensure_ascii=False)
            row.source_metadata_json = json.dumps(merged_metadata, ensure_ascii=False)
            if promoted_memory_id is not None:
                row.promoted_memory_id = promoted_memory_id
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            return self._to_note(row)

    def delete_note(self, note_id: str) -> bool:
        with SessionLocal() as db:
            row = db.query(WorkspaceNoteModel).filter(WorkspaceNoteModel.id == note_id).first()
            if row is None:
                return False
            db.delete(row)
            db.commit()
            return True


notebook_service = NotebookService()

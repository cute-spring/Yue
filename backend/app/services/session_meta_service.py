import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Literal
from pydantic_ai import Agent, UsageLimits
from app.services.chat_service import chat_service, ChatSession
from app.services.config_service import config_service
from app.services.model_factory import get_model

logger = logging.getLogger(__name__)

MetaTask = Literal["title", "summary"]
NOTE_TYPES = {
    "decision",
    "fact",
    "insight",
    "preference",
    "reference",
    "summary",
    "todo",
}

TITLE_PROMPT = """你是对话标题生成器。
请根据用户首条消息与助手首段回复，生成一个简洁标题。
要求：
1) 输出仅标题，不要解释；
2) 中文控制在 2-8 字，英文控制在 3-5 词；
3) 去掉客套话，保留任务核心意图。"""

SUMMARY_PROMPT = """你是对话摘要生成器。
请输出 1-2 句摘要，说明用户诉求与当前结论。
要求：
1) 输出纯文本，不要列表；
2) 避免细节噪音，突出可检索关键词；
3) 80 字以内（英文 40 词以内）。"""

NOTE_ENRICHMENT_PROMPT = """你是工作区笔记整理器。
请根据输入内容，输出一个 JSON 对象，用于结构化保存工作区笔记。

输出要求：
1) 只输出 JSON，不要解释，不要 Markdown；
2) JSON 字段固定为：title, summary, tags, note_type；
3) title 要简洁明确，中文 4-14 字，英文 3-6 词；
4) summary 用 1-2 句概括可复用结论，尽量便于后续召回；
5) tags 输出 3-5 个短标签，优先主题词，避免空泛词；
6) note_type 只能是 decision, fact, insight, preference, reference, summary, todo 之一；
7) 保持与输入内容相同的主语言。"""


class SessionMetaService:
    def _resolve_meta_runtime(
        self,
        *,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        llm_config = config_service.get_llm_config()
        if not llm_config.get("meta_enabled", False):
            return None
        provider = provider_override or llm_config.get("meta_provider")
        model_name = model_override or llm_config.get("meta_model")
        if not provider or not model_name:
            return None
        return {
            "provider": provider,
            "model_name": model_name,
            "timeout_ms": int(llm_config.get("meta_timeout_ms") or 1800),
            "max_tokens": int(llm_config.get("meta_max_tokens") or 96),
        }

    async def generate_session_meta(
        self,
        chat_id: str,
        task: MetaTask,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> Optional[str]:
        if task not in {"title", "summary"}:
            raise ValueError("task must be title or summary")
        runtime = self._resolve_meta_runtime(
            provider_override=provider_override,
            model_override=model_override,
        )
        if runtime is None:
            return None
        chat = chat_service.get_chat(chat_id)
        if not chat:
            return None
        user_prompt = self._build_task_prompt(chat, task)
        if not user_prompt:
            return None
        system_prompt = TITLE_PROMPT if task == "title" else SUMMARY_PROMPT
        try:
            generated = await asyncio.wait_for(
                self._generate_text(
                    provider=runtime["provider"],
                    model_name=runtime["model_name"],
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=runtime["max_tokens"]
                ),
                timeout=runtime["timeout_ms"] / 1000.0
            )
            return self._normalize_output(generated, task)
        except Exception:
            logger.debug("generate_session_meta failed", exc_info=True)
            return None

    async def generate_note_enrichment(
        self,
        *,
        content: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        note_type: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        runtime = self._resolve_meta_runtime(
            provider_override=provider_override,
            model_override=model_override,
        )
        if runtime is None:
            return None
        user_prompt = self._build_note_enrichment_prompt(
            content=content,
            title=title,
            summary=summary,
            tags=tags,
            note_type=note_type,
            source_metadata=source_metadata,
        )
        if not user_prompt:
            return None
        try:
            generated = await asyncio.wait_for(
                self._generate_text(
                    provider=runtime["provider"],
                    model_name=runtime["model_name"],
                    system_prompt=NOTE_ENRICHMENT_PROMPT,
                    user_prompt=user_prompt,
                    max_tokens=max(runtime["max_tokens"], 160),
                ),
                timeout=runtime["timeout_ms"] / 1000.0,
            )
            return self._parse_note_enrichment_output(generated)
        except Exception:
            logger.debug("generate_note_enrichment failed", exc_info=True)
            return None

    def _build_task_prompt(self, chat: ChatSession, task: MetaTask) -> Optional[str]:
        user_messages = [m.content.strip() for m in chat.messages if m.role == "user" and m.content and m.content.strip()]
        assistant_messages = [m.content.strip() for m in chat.messages if m.role == "assistant" and m.content and m.content.strip()]
        if task == "title":
            if not user_messages or not assistant_messages:
                return None
            user_msg = user_messages[0][:1200]
            assistant_msg = assistant_messages[0][:1200]
            return f"用户首条消息：\n{user_msg}\n\n助手首段回复：\n{assistant_msg}\n"
        if not chat.messages:
            return None
        lines = []
        for msg in chat.messages[-12:]:
            role = "用户" if msg.role == "user" else "助手"
            content = (msg.content or "").strip()
            if not content:
                continue
            lines.append(f"{role}: {content[:500]}")
        if not lines:
            return None
        return "\n".join(lines)

    def _build_note_enrichment_prompt(
        self,
        *,
        content: str,
        title: Optional[str],
        summary: Optional[str],
        tags: Optional[List[str]],
        note_type: Optional[str],
        source_metadata: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        compact_content = (content or "").strip()
        if not compact_content:
            return None
        source_bits: List[str] = []
        if title and title.strip():
            source_bits.append(f"已有标题: {title.strip()[:120]}")
        if summary and summary.strip():
            source_bits.append(f"已有摘要: {summary.strip()[:240]}")
        if tags:
            normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
            if normalized_tags:
                source_bits.append(f"已有标签: {', '.join(normalized_tags[:8])}")
        if note_type and note_type.strip():
            source_bits.append(f"已有类型: {note_type.strip().lower()}")
        if source_metadata:
            captured_from = source_metadata.get("captured_from")
            if captured_from:
                source_bits.append(f"来源类型: {captured_from}")
        prompt_lines = [
            *source_bits,
            "笔记正文:",
            compact_content[:4000],
        ]
        return "\n".join(prompt_lines).strip()

    async def _generate_text(
        self,
        provider: str,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int
    ) -> str:
        model = get_model(provider, model_name)
        agent = Agent(model=model, system_prompt=system_prompt)
        usage_limits = UsageLimits(output_tokens_limit=max_tokens) if max_tokens > 0 else None
        final_text = ""
        async with agent.run_stream(user_prompt, usage_limits=usage_limits) as result:
            async for chunk in result.stream_text():
                final_text = chunk
        return final_text

    def _normalize_output(self, text: str, task: MetaTask) -> Optional[str]:
        cleaned = (text or "").strip()
        if not cleaned:
            return None
        cleaned = cleaned.strip("'\"")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if task == "title":
            cleaned = cleaned.splitlines()[0].strip()
            return cleaned[:60] if cleaned else None
        return cleaned[:240]

    @staticmethod
    def _extract_json_payload(text: str) -> Optional[Dict[str, Any]]:
        cleaned = (text or "").strip()
        if not cleaned:
            return None
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        candidates = [cleaned]
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            candidates.insert(0, match.group(0))
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _parse_note_enrichment_output(self, text: str) -> Optional[Dict[str, Any]]:
        payload = self._extract_json_payload(text)
        if not payload:
            return None
        normalized_title = self._normalize_output(str(payload.get("title") or ""), "title")
        normalized_summary = self._normalize_output(str(payload.get("summary") or ""), "summary")
        normalized_tags: List[str] = []
        raw_tags = payload.get("tags")
        if isinstance(raw_tags, list):
            for item in raw_tags:
                cleaned = re.sub(r"\s+", " ", str(item or "")).strip().strip(",")
                if not cleaned or cleaned in normalized_tags:
                    continue
                normalized_tags.append(cleaned[:24])
                if len(normalized_tags) >= 5:
                    break
        normalized_type = str(payload.get("note_type") or "").strip().lower()
        if normalized_type not in NOTE_TYPES:
            normalized_type = None
        if not any([normalized_title, normalized_summary, normalized_tags, normalized_type]):
            return None
        return {
            "title": normalized_title,
            "summary": normalized_summary,
            "tags": normalized_tags,
            "note_type": normalized_type,
        }


session_meta_service = SessionMetaService()

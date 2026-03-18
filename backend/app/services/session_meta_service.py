import asyncio
import logging
import re
from typing import Optional, Literal
from pydantic_ai import Agent, UsageLimits
from app.services.chat_service import chat_service, ChatSession
from app.services.config_service import config_service
from app.services.model_factory import get_model

logger = logging.getLogger(__name__)

MetaTask = Literal["title", "summary"]

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


class SessionMetaService:
    async def generate_session_meta(
        self,
        chat_id: str,
        task: MetaTask,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> Optional[str]:
        if task not in {"title", "summary"}:
            raise ValueError("task must be title or summary")
        llm_config = config_service.get_llm_config()
        if not llm_config.get("meta_enabled", False):
            return None
        provider = provider_override or llm_config.get("meta_provider")
        model_name = model_override or llm_config.get("meta_model")
        if not provider or not model_name:
            return None
        timeout_ms = int(llm_config.get("meta_timeout_ms") or 1800)
        max_tokens = int(llm_config.get("meta_max_tokens") or 96)
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
                    provider=provider,
                    model_name=model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens
                ),
                timeout=timeout_ms / 1000.0
            )
            return self._normalize_output(generated, task)
        except Exception:
            logger.debug("generate_session_meta failed", exc_info=True)
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
        usage_limits = UsageLimits(response_tokens_limit=max_tokens) if max_tokens > 0 else None
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


session_meta_service = SessionMetaService()

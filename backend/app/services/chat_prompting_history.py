from typing import Any, Callable, List

from pydantic_ai.messages import ImageUrl, ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.services.chat_prompting_env import (
    EST_CHARS_PER_TOKEN,
    estimate_tokens,
    prompt_history_max_context_tokens,
    prompt_history_max_single_message_tokens,
)


def build_history_from_chat(
    existing_chat: Any,
    *,
    load_image_to_base64: Callable[[str], str],
    logger: Any,
) -> List[Any]:
    if not existing_chat:
      return []

    current_tokens = 0
    max_context_tokens = prompt_history_max_context_tokens()
    max_single_msg_tokens = prompt_history_max_single_message_tokens()
    temp_history: List[Any] = []

    for message in reversed(existing_chat.messages):
        content = message.content or ""
        msg_tokens = estimate_tokens(content)

        if msg_tokens > max_single_msg_tokens:
            keep_chars = max_single_msg_tokens * EST_CHARS_PER_TOKEN
            content = content[:keep_chars] + "\n... (content truncated due to length)"
            msg_tokens = max_single_msg_tokens

        if current_tokens + msg_tokens > max_context_tokens:
            logger.info("Context limit reached. Dropping older messages. Current tokens: %s", current_tokens)
            break

        current_tokens += msg_tokens

        if message.role == "user":
            if message.images:
                parts = []
                content_text = (message.content or "").strip()
                if content_text:
                    parts.append(content_text)
                for img in message.images:
                    parts.append(ImageUrl(url=load_image_to_base64(img)))
                temp_history.append(ModelRequest(parts=[UserPromptPart(content=parts)]))
            else:
                temp_history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif message.role == "assistant":
            temp_history.append(ModelResponse(parts=[TextPart(content=content)]))

    return list(reversed(temp_history))

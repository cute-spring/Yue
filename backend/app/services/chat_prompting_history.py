from typing import Any, Callable, List

from pydantic_ai.messages import (
    ImageUrl,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

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
            tool_calls = list(getattr(message, "tool_calls", None) or [])
            tool_call_parts = []
            tool_return_parts = []
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                tool_name = tool_call.get("tool_name")
                tool_call_id = tool_call.get("call_id")
                if not isinstance(tool_name, str) or not tool_name or not isinstance(tool_call_id, str) or not tool_call_id:
                    continue
                tool_call_parts.append(
                    ToolCallPart(
                        tool_name=tool_name,
                        args=tool_call.get("args") or {},
                        tool_call_id=tool_call_id,
                    )
                )
                tool_result = tool_call.get("result")
                if tool_result is None:
                    tool_result = tool_call.get("error") or tool_call.get("status") or ""
                tool_return_parts.append(
                    ToolReturnPart(
                        tool_name=tool_name,
                        content=tool_result,
                        tool_call_id=tool_call_id,
                    )
                )
            temp_history.append(ModelResponse(parts=[TextPart(content=content)]))
            if tool_call_parts:
                temp_history.append(ModelRequest(parts=tool_return_parts))
                temp_history.append(ModelResponse(parts=tool_call_parts))

    return list(reversed(temp_history))

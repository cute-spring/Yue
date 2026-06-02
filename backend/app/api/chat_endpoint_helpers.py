from typing import Any, Optional

from fastapi import HTTPException

from app.api.chat_schemas import ActionStateResponse


def require_chat(chat_id: str, *, chat_service: Any) -> Any:
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def normalize_action_state_response(state: Any) -> ActionStateResponse:
    if hasattr(state, "model_dump"):
        return ActionStateResponse.model_validate(state.model_dump())
    return ActionStateResponse.model_validate(state)


def resolve_action_state_lookup(
    *,
    chat_id: str,
    skill_name: Optional[str],
    action_id: Optional[str],
    invocation_id: Optional[str],
    approval_token: Optional[str],
    chat_service: Any,
) -> Any:
    require_chat(chat_id, chat_service=chat_service)

    if invocation_id:
        if skill_name or action_id or approval_token:
            raise HTTPException(
                status_code=400,
                detail="Use exactly one lookup mode: invocation_id, approval_token, or skill_name + action_id",
            )
        state = chat_service.get_action_state_by_invocation_id(
            chat_id,
            invocation_id=invocation_id,
        )
    elif approval_token:
        if skill_name or action_id:
            raise HTTPException(
                status_code=400,
                detail="Use exactly one lookup mode: invocation_id, approval_token, or skill_name + action_id",
            )
        state = chat_service.get_action_state_by_approval_token(
            chat_id,
            approval_token=approval_token,
        )
    else:
        if bool(skill_name) != bool(action_id):
            raise HTTPException(
                status_code=400,
                detail="skill_name and action_id are required together when approval_token is not provided",
            )
        if not skill_name or not action_id:
            raise HTTPException(
                status_code=400,
                detail="Provide invocation_id, approval_token, or skill_name + action_id",
            )
        state = chat_service.get_action_state(
            chat_id,
            skill_name=skill_name,
            action_id=action_id,
        )

    if state is None:
        raise HTTPException(status_code=404, detail="Action state not found")
    return state

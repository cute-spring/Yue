from __future__ import annotations

from app.modules.session_context.models import PromptContextBlock


def apply_token_budget(blocks: list[PromptContextBlock], token_budget: int) -> list[PromptContextBlock]:
    ordered = sorted(blocks, key=lambda block: block.priority, reverse=True)
    kept: list[PromptContextBlock] = []
    used = 0
    for block in ordered:
        if used + block.token_count > token_budget:
            continue
        kept.append(block)
        used += block.token_count
    return kept

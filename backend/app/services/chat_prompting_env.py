import os
from typing import Any, Optional, Tuple


EST_CHARS_PER_TOKEN = 3
DISCOVERY_EXTENSIONS = [".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".xltx", ".xltm", ".csv", ".md", ".txt"]


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(text) // EST_CHARS_PER_TOKEN


def env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def safe_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def prompt_history_max_context_tokens() -> int:
    return safe_int_env("PROMPT_HISTORY_MAX_CONTEXT_TOKENS", 100000)


def prompt_history_max_single_message_tokens() -> int:
    return safe_int_env("PROMPT_HISTORY_MAX_SINGLE_MESSAGE_TOKENS", 20000)


def env_flag_with_fallback(primary: str, legacy: str, default: bool) -> bool:
    raw_primary = os.getenv(primary)
    if raw_primary is not None:
        return raw_primary.strip().lower() in {"1", "true", "yes", "on"}
    return env_flag(legacy, default)


def safe_int_env_with_fallback(primary: str, legacy: str, default: int) -> int:
    raw_primary = os.getenv(primary)
    if raw_primary is not None:
        try:
            value = int(raw_primary)
        except Exception:
            return default
        return value if value > 0 else default
    return safe_int_env(legacy, default)


def has_document_discovery_capability(agent_config: Any) -> bool:
    tools = getattr(agent_config, "enabled_tools", []) or []
    for tool in tools:
        if not isinstance(tool, str):
            continue
        if "docs_" in tool or "excel_" in tool or tool in {"builtin:exec", "exec"}:
            return True
    return False


def mask_scope_root(path: str, *, doc_retrieval: Any) -> str:
    if not path:
        return path
    project_root = doc_retrieval.get_project_root()
    path_real = os.path.realpath(path)
    project_real = os.path.realpath(project_root)
    try:
        if os.path.commonpath([project_real, path_real]) == project_real:
            rel = os.path.relpath(path_real, project_real).replace(os.sep, "/")
            return rel if rel != "." else "."
    except Exception:
        pass
    parts = [p for p in path_real.replace("\\", "/").split("/") if p]
    tail = "/".join(parts[-2:]) if len(parts) >= 2 else (parts[0] if parts else path_real)
    return f".../{tail}" if tail else path_real


def build_scope_summary_block(
    agent_config: Any,
    *,
    config_service: Any,
    doc_retrieval: Any,
) -> Tuple[Optional[str], int]:
    if not agent_config or not has_document_discovery_capability(agent_config):
        return None, 0
    if not env_flag("PROMPT_SCOPE_SUMMARY_ENABLED", True):
        return None, 0
    reveal_paths = env_flag("PROMPT_SCOPE_SUMMARY_REVEAL_PATHS", True)
    max_roots = safe_int_env("PROMPT_SCOPE_SUMMARY_MAX_ROOTS", 3)
    doc_roots = getattr(agent_config, "doc_roots", None) or []
    doc_access = config_service.get_doc_access()
    allow_roots = doc_access.get("allow_roots") or []
    deny_roots = doc_access.get("deny_roots") or []
    try:
        effective_roots = doc_retrieval.resolve_docs_roots_for_search(
            None,
            doc_roots=doc_roots,
            allow_roots=allow_roots,
            deny_roots=deny_roots,
        )
    except Exception:
        effective_roots = []
    if not effective_roots:
        return None, 0
    shown = effective_roots[:max_roots]
    display_roots = shown if reveal_paths else [mask_scope_root(p, doc_retrieval=doc_retrieval) for p in shown]
    lines = ["### Scope Summary", f"- Effective roots: {len(effective_roots)}"]
    lines.extend(f"- {root}" for root in display_roots)
    if len(effective_roots) > len(shown):
        lines.append(f"- ... and {len(effective_roots) - len(shown)} more")
    lines.append("### Document Discovery Hints")
    lines.append("- For document filename/path/extension discovery, prefer OS-native search commands through exec or use docs_list first.")
    lines.append("- If the system-ops-expert skill is visible, prefer it first for document discovery workflows before file-specific readers such as excel_profile or docs_read.")
    lines.append("- Use exact absolute root paths above when building exec/docs/excel paths; avoid guessing with unrelated relative prefixes such as ./Desktop/...")
    lines.append(f"- Common document extensions: {', '.join(DISCOVERY_EXTENSIONS)}")
    lines.append("- Use exec for any efficient shell task when appropriate; document discovery is only one high-value use case.")
    lines.append("- For file-specific readers such as excel_read/excel_query/docs_read, locate a concrete file path before calling the tool.")
    lines.append("- Preferred roots above are guidance for document-oriented tasks; exec itself is not limited to search-only usage.")
    return "\n".join(lines), len(effective_roots)

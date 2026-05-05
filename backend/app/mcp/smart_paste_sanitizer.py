import re
from typing import Optional


SECRET_KEYWORDS = ("token", "secret", "password", "api-key", "api_key", "authorization")

SENSITIVE_HEADER_KEYS = {"authorization", "x-api-key", "api-key", "x-auth-token", "cookie", "set-cookie"}

BLOCKED_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"Bearer [a-zA-Z0-9\-_\.]+", re.IGNORECASE),
    re.compile(r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+"),
]


def is_sensitive_key(key: str) -> bool:
    key_lower = key.lower().replace("_", "-")
    if key_lower in SENSITIVE_HEADER_KEYS:
        return True
    for kw in SECRET_KEYWORDS:
        if kw in key_lower:
            return True
    return False


def is_placeholder(value: str) -> bool:
    return bool(re.match(r"^\$\{[A-Z_][A-Z0-9_]*\}$", value.strip()))


def to_env_placeholder(name: str, fallback: str = "MCP_SECRET") -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
    return f"${{{normalized or fallback}}}"


def sanitize_headers(headers: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
    if not headers:
        return headers
    result = {}
    for key, value in headers.items():
        if is_sensitive_key(key) and not is_placeholder(value):
            result[key] = "${" + key.upper().replace("-", "_") + "_TOKEN}"
        else:
            result[key] = value
    return result


def sanitize_env(env: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
    if not env:
        return env
    result = {}
    for key, value in env.items():
        if is_sensitive_key(key) and not is_placeholder(value):
            result[key] = to_env_placeholder(key)
        else:
            result[key] = value
    return result


def contains_blocked_secret_material(text: str) -> bool:
    for pattern in BLOCKED_SECRET_PATTERNS:
        if pattern.search(text):
            return True
    return False


def scan_for_blocked_material(text: str) -> list[str]:
    warnings = []
    for pattern in BLOCKED_SECRET_PATTERNS:
        if pattern.search(text):
            warnings.append("Blocked secret material detected and replaced with environment placeholders.")
            break
    return warnings

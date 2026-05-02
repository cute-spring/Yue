import pytest
from pydantic import ValidationError


def test_smart_paste_request_rejects_oversized_input():
    from app.mcp.smart_paste_models import SmartPasteRequest

    with pytest.raises(ValidationError):
        SmartPasteRequest(raw_text="x" * 8001)


def test_smart_paste_request_rejects_empty():
    from app.mcp.smart_paste_models import SmartPasteRequest

    with pytest.raises(ValidationError):
        SmartPasteRequest(raw_text="")


def test_parsed_server_config_defaults_to_disabled():
    from app.mcp.smart_paste_models import ParsedServerConfig

    item = ParsedServerConfig(name="demo", transport="stdio", command="npx", confidence=1.0)
    assert item.enabled is False


def test_parsed_server_config_confidence_range():
    from app.mcp.smart_paste_models import ParsedServerConfig

    with pytest.raises(ValidationError):
        ParsedServerConfig(name="demo", transport="stdio", command="npx", confidence=1.5)

    with pytest.raises(ValidationError):
        ParsedServerConfig(name="demo", transport="stdio", command="npx", confidence=-0.1)


def test_parsed_server_config_transport_must_be_valid():
    from app.mcp.smart_paste_models import ParsedServerConfig

    with pytest.raises(ValidationError):
        ParsedServerConfig(name="demo", transport="invalid", command="npx", confidence=1.0)


def test_smart_paste_response_defaults():
    from app.mcp.smart_paste_models import SmartPasteResponse

    response = SmartPasteResponse(ok=True, results=[], parse_mode="ai")
    assert response.ok is True
    assert response.results == []
    assert response.parse_mode == "ai"
    assert response.error is None


# --- Sanitizer tests ---


def test_redacts_bearer_header_values():
    from app.mcp.smart_paste_sanitizer import sanitize_headers

    sanitized = sanitize_headers({"Authorization": "Bearer sk-secret"})
    assert sanitized["Authorization"] == "${AUTHORIZATION_TOKEN}"


def test_rejects_private_key_input():
    from app.mcp.smart_paste_sanitizer import contains_blocked_secret_material

    assert contains_blocked_secret_material("-----BEGIN PRIVATE KEY-----") is True


def test_preserves_placeholder_values():
    from app.mcp.smart_paste_sanitizer import sanitize_headers

    sanitized = sanitize_headers({"Authorization": "${MCP_TOKEN}"})
    assert sanitized["Authorization"] == "${MCP_TOKEN}"


def test_to_env_placeholder_normalizes_name():
    from app.mcp.smart_paste_sanitizer import to_env_placeholder

    assert to_env_placeholder("api-key") == "${API_KEY}"
    assert to_env_placeholder("token") == "${TOKEN}"


def test_sanitize_env_vars():
    from app.mcp.smart_paste_sanitizer import sanitize_env

    sanitized = sanitize_env({"JIRA_TOKEN": "sk-secret-value"})
    assert sanitized["JIRA_TOKEN"] == "${JIRA_TOKEN}"


def test_sanitize_env_preserves_non_secret():
    from app.mcp.smart_paste_sanitizer import sanitize_env

    sanitized = sanitize_env({"HOME": "/home/user", "PATH": "/usr/bin"})
    assert sanitized["HOME"] == "/home/user"
    assert sanitized["PATH"] == "/usr/bin"

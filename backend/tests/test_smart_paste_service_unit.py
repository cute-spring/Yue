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


# --- Rule parser tests ---


def test_parse_claude_desktop_json_to_stdio_result():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste('{"mcpServers":{"fs":{"command":"npx","args":["-y","pkg"]}}}')
    assert response.ok is True
    assert response.parse_mode == "rule"
    assert response.results[0].transport == "stdio"
    assert response.results[0].command == "npx"


def test_parse_single_url_to_streamable_http_result():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste("MCP endpoint: https://mcp.example.com/stream")
    assert response.results[0].transport == "streamable_http"
    assert response.results[0].url == "https://mcp.example.com/stream"


def test_parse_npx_command_snippet():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste("npx -y @company/mcp-server --port 8080")
    assert response.ok is True
    assert response.parse_mode == "rule"
    assert response.results[0].transport == "stdio"
    assert response.results[0].command == "npx"
    assert "-y" in response.results[0].args
    assert "@company/mcp-server" in response.results[0].args


def test_parse_uvx_command_snippet():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste("uvx my-mcp-package --verbose")
    assert response.ok is True
    assert response.results[0].transport == "stdio"
    assert response.results[0].command == "uvx"


def test_parse_json_array():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste('[{"name":"srv","transport":"stdio","command":"node","args":["s.js"]}]')
    assert response.ok is True
    assert response.results[0].name == "srv"


def test_parse_returns_ok_false_when_nothing_extractable():
    from app.mcp.smart_paste_service import parse_smart_paste, SmartPasteServiceUnavailable
    import pytest

    with pytest.raises(SmartPasteServiceUnavailable):
        parse_smart_paste("hello world this is not a config")


def test_parse_json_single_object():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste('{"name":"test","transport":"streamable_http","url":"https://example.com/stream"}')
    assert response.ok is True
    assert response.results[0].transport == "streamable_http"
    assert response.results[0].url == "https://example.com/stream"


# --- Edge case tests ---


def test_preprocess_rejects_illegal_control_chars():
    from app.mcp.smart_paste_service import preprocess_raw_text

    cleaned = preprocess_raw_text("hello\x00world\x01\n")
    assert "\x00" not in cleaned
    assert "\x01" not in cleaned
    assert "\n" in cleaned


def test_parse_redacts_authorization_header():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste('{"name":"srv","transport":"streamable_http","url":"https://example.com","headers":{"Authorization":"Bearer sk-abc123"}}')
    assert response.results[0].headers["Authorization"] == "${AUTHORIZATION_TOKEN}"


def test_parse_returns_ok_false_when_empty_after_clean():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste("\x00\x01\x02")
    assert response.ok is False


def test_parse_claude_desktop_multiple_servers():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste('{"mcpServers":{"srv1":{"command":"npx","args":["a"]},"srv2":{"command":"node","args":["b"]}}}')
    assert len(response.results) == 2
    names = {r.name for r in response.results}
    assert names == {"srv1", "srv2"}


def test_parse_command_with_env_vars_in_input():
    from app.mcp.smart_paste_service import parse_smart_paste

    response = parse_smart_paste("npx -y @test/pkg")
    assert response.ok is True
    assert response.results[0].transport == "stdio"


# --- LLM envelope tests ---


def test_smart_paste_llm_envelope_accepts_empty_results():
    from app.mcp.smart_paste_models import SmartPasteLlmEnvelope

    envelope = SmartPasteLlmEnvelope(results=[])
    assert envelope.results == []


def test_smart_paste_llm_envelope_validates_nested_model():
    from app.mcp.smart_paste_models import SmartPasteLlmEnvelope

    envelope = SmartPasteLlmEnvelope(
        results=[{
            "name": "test-srv",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "pkg"],
            "confidence": 0.9,
        }]
    )
    assert len(envelope.results) == 1
    assert envelope.results[0].name == "test-srv"
    assert envelope.results[0].transport == "stdio"


def test_system_prompt_contains_security_rules():
    from app.mcp.smart_paste_service import SMART_PASTE_SYSTEM_PROMPT

    assert "安全" in SMART_PASTE_SYSTEM_PROMPT or "secret" in SMART_PASTE_SYSTEM_PROMPT.lower()
    assert "ENV_NAME" in SMART_PASTE_SYSTEM_PROMPT or "占位符" in SMART_PASTE_SYSTEM_PROMPT
    assert len(SMART_PASTE_SYSTEM_PROMPT) > 200

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

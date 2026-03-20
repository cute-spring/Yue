from fastapi.testclient import TestClient

from app.main import app


def test_export_txt_response_plain_text():
    client = TestClient(app)
    response = client.post("/api/export", json={"content": "# Hello\n\n- item", "format": "txt"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# Hello" not in response.text
    assert "Hello" in response.text
    assert "item" in response.text


def test_export_docx_response_binary():
    client = TestClient(app)
    response = client.post("/api/export", json={"content": "# Hello\n\n- item", "format": "docx"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.content[:2] == b"PK"


def test_export_invalid_format_returns_422():
    client = TestClient(app)
    response = client.post("/api/export", json={"content": "hello", "format": "md"})
    assert response.status_code == 422

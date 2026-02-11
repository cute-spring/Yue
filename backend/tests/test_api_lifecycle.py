import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.observability import TRACE_HEADER

@pytest.fixture
def client():
    return TestClient(app)

def test_root_endpoint(client):
    response = client.get("/")
    # If static files not found, it returns the welcome message
    assert response.status_code == 200
    assert "message" in response.json() or response.headers.get("content-type") == "text/html"

def test_trace_id_middleware(client):
    response = client.get("/")
    assert TRACE_HEADER in response.headers
    trace_id = response.headers[TRACE_HEADER]
    assert len(trace_id) > 0

def test_cors_headers(client):
    origin = "http://localhost:3000"
    response = client.options(
        "/api/config/llm",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    # FastAPI CORSMiddleware echoes the origin when allow_origins=["*"]
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin == "*" or allow_origin == origin

def test_api_docs_available(client):
    response = client.get("/docs")
    assert response.status_code == 200

def test_files_mount(client):
    # Test that the /files mount exists
    response = client.get("/files/non-existent-file")
    assert response.status_code == 404

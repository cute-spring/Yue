import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_upload_files_success_persists_to_yue_data_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("YUE_DATA_DIR", tmp)
        client = TestClient(app)

        response = client.post(
            "/api/files",
            files=[("files", ("report.pdf", b"%PDF-1.4\n", "application/pdf"))],
        )

        assert response.status_code == 200
        payload = response.json()
        assert "files" in payload
        assert len(payload["files"]) == 1
        item = payload["files"][0]
        assert item["display_name"] == "report.pdf"
        assert item["mime_type"] == "application/pdf"
        assert item["url"].startswith("/files/chat/")
        assert item["storage_path"].startswith("uploads/chat/")

        stored_path = Path(tmp) / item["storage_path"]
        assert stored_path.exists()


def test_upload_files_rejects_unsupported_type(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("YUE_DATA_DIR", tmp)
        client = TestClient(app)

        response = client.post(
            "/api/files",
            files=[("files", ("notes.txt", b"hello", "text/plain"))],
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["code"] == "unsupported_file_type"


def test_upload_files_rejects_too_many_files(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("YUE_DATA_DIR", tmp)
        monkeypatch.setenv("YUE_MAX_UPLOAD_FILES", "6")
        client = TestClient(app)

        files = [("files", (f"f{i}.pdf", b"%PDF-1.4\n", "application/pdf")) for i in range(7)]
        response = client.post("/api/files", files=files)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["code"] == "too_many_files"
        assert detail["max_files"] == 6


def test_upload_files_rejects_file_too_large(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("YUE_DATA_DIR", tmp)
        monkeypatch.setenv("YUE_MAX_UPLOAD_FILE_SIZE_BYTES", "10")
        client = TestClient(app)

        response = client.post(
            "/api/files",
            files=[("files", ("big.csv", b"01234567890", "text/csv"))],
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["code"] == "file_too_large"
        assert detail["max_file_size_bytes"] == 10


def test_upload_files_policy_returns_runtime_limits(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("YUE_DATA_DIR", tmp)
        monkeypatch.setenv("YUE_MAX_UPLOAD_FILES", "6")
        monkeypatch.setenv("YUE_MAX_UPLOAD_FILE_SIZE_BYTES", str(8 * 1024 * 1024))
        client = TestClient(app)

        response = client.get("/api/files/policy")

        assert response.status_code == 200
        payload = response.json()
        assert payload["max_files"] == 6
        assert payload["max_file_size_bytes"] == 8 * 1024 * 1024
        assert "application/pdf" in payload["allowed_mime_types"]
        assert ".pdf" in payload["allowed_extensions"]

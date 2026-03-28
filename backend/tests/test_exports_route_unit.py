import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path / "runtime-data"))
    from app.main import app

    try:
        return TestClient(app)
    except TypeError:
        pytest.skip("TestClient incompatible with installed httpx/starlette")


def test_exports_route_serves_legacy_backend_exports_file(client):
    from app import main as main_module

    legacy_root = Path(main_module.legacy_exports_dir)
    legacy_root.mkdir(parents=True, exist_ok=True)
    export_file = legacy_root / "route_test_export.pptx"
    export_file.write_bytes(b"ppt-test")

    try:
        response = client.get("/exports/route_test_export.pptx")
        assert response.status_code == 200
        assert response.content == b"ppt-test"
    finally:
        if export_file.exists():
            export_file.unlink()

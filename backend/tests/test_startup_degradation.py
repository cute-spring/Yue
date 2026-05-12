from fastapi.testclient import TestClient


async def _raise_init_error():
    raise RuntimeError("startup init boom")


async def _noop_async():
    return None


def test_lifespan_startup_survives_mcp_initialize_exception(monkeypatch):
    from app import main as main_module

    monkeypatch.setattr(main_module.mcp_manager, "initialize", _raise_init_error)
    monkeypatch.setattr(main_module.mcp_manager, "cleanup", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "start", _noop_async)
    monkeypatch.setattr(main_module.health_monitor, "stop", _noop_async)

    with TestClient(main_module.app) as client:
        response = client.get("/api/health/")

    assert response.status_code == 200


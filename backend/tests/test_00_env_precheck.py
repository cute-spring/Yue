import pytest
import httpx
import starlette
from fastapi.testclient import TestClient

from app.main import app


def test_env_precheck_testclient_compatibility():
    try:
        TestClient(app)
    except TypeError as exc:
        pytest.skip(
            f"ENV_PRECHECK TestClient incompatible with current runtime: "
            f"starlette={starlette.__version__}, httpx={httpx.__version__}, error={exc}"
        )

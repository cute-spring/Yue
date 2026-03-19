from fastapi.testclient import TestClient

from app.main import app


def test_skill_groups_crud_api_flow():
    client = TestClient(app)

    create_resp = client.post(
        "/api/skill-groups/",
        json={
            "name": "backend-debug",
            "description": "backend bundle",
            "skill_refs": ["backend-api-debugger:1.0.0"],
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["name"] == "backend-debug"

    list_resp = client.get("/api/skill-groups/")
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert any(group["id"] == created["id"] for group in listed)

    update_resp = client.put(
        f"/api/skill-groups/{created['id']}",
        json={"description": "updated", "skill_refs": ["backend-api-debugger:1.1.0"]},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "updated"

    delete_resp = client.delete(f"/api/skill-groups/{created['id']}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "success"

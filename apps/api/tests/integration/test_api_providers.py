"""Tests for /api/providers/ endpoints."""
import pytest


@pytest.fixture()
def sample_provider(client):
    """Create a custom (non-builtin) provider."""
    resp = client.post("/api/providers/", json={
        "name": "Test Provider",
        "protocol": "openai",
        "base_url": "https://api.test.com",
        "api_key": "sk-test-key-123",
    })
    assert resp.status_code == 200
    return resp.json()


class TestListProviders:
    def test_list_returns_list(self, client):
        resp = client.get("/api/providers/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestCreateProvider:
    def test_create_provider(self, client):
        resp = client.post("/api/providers/", json={
            "name": "My Provider",
            "protocol": "openai",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Provider"
        assert data["protocol"] == "openai"
        assert data["is_builtin"] is False
        assert len(data["id"]) == 8

    def test_create_with_api_key_masks_it(self, client):
        resp = client.post("/api/providers/", json={
            "name": "Keyed",
            "protocol": "anthropic",
            "api_key": "sk-ant-secret-key-1234567890",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_api_key"] is True
        assert "secret" not in data["api_key_masked"]


class TestUpdateProvider:
    def test_update_name(self, client, sample_provider):
        pid = sample_provider["id"]
        resp = client.patch(f"/api/providers/{pid}", json={"name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    def test_update_nonexistent(self, client):
        resp = client.patch("/api/providers/nonexist", json={"name": "x"})
        assert resp.status_code == 404


class TestDeleteProvider:
    def test_delete_custom(self, client, sample_provider):
        pid = sample_provider["id"]
        resp = client.delete(f"/api/providers/{pid}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/providers/nonexist")
        assert resp.status_code == 404


class TestProviderModels:
    def test_add_model(self, client, sample_provider):
        pid = sample_provider["id"]
        resp = client.post(f"/api/providers/{pid}/models", json={
            "model_id": "gpt-4o-test",
            "display_name": "GPT-4o Test",
            "is_default": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "gpt-4o-test"
        assert data["is_default"] is True

    def test_list_models(self, client, sample_provider):
        pid = sample_provider["id"]
        client.post(f"/api/providers/{pid}/models", json={
            "model_id": "m1",
            "display_name": "Model 1",
        })
        resp = client.get(f"/api/providers/{pid}/models")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_delete_model(self, client, sample_provider):
        pid = sample_provider["id"]
        create_resp = client.post(f"/api/providers/{pid}/models", json={
            "model_id": "to-delete",
            "display_name": "Delete Me",
        })
        mid = create_resp.json()["id"]
        resp = client.delete(f"/api/providers/{pid}/models/{mid}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_set_default_unsets_others(self, client, sample_provider):
        pid = sample_provider["id"]
        client.post(f"/api/providers/{pid}/models", json={
            "model_id": "m1", "display_name": "M1", "is_default": True,
        })
        client.post(f"/api/providers/{pid}/models", json={
            "model_id": "m2", "display_name": "M2", "is_default": True,
        })
        models = client.get(f"/api/providers/{pid}/models").json()
        defaults = [m for m in models if m["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["model_id"] == "m2"

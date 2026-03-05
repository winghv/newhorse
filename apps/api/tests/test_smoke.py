"""Smoke test to verify test infrastructure works."""


def test_client_works(client):
    """Test that the test client can reach the API."""
    resp = client.get("/api/projects/")
    assert resp.status_code == 200
    # Butler project is auto-seeded on startup
    data = resp.json()
    assert isinstance(data, list)
    butler_ids = [p["id"] for p in data if p.get("preferred_cli") == "butler"]
    assert len(butler_ids) == 1

"""Smoke test to verify test infrastructure works."""


def test_client_works(client):
    """Test that the test client can reach the API."""
    resp = client.get("/api/projects/")
    assert resp.status_code == 200
    assert resp.json() == []

"""Integration tests for /api/skills endpoints."""


class TestListSkills:
    """GET /api/skills — list built-in and project skills."""

    def test_lists_media_ops_skills(self, client):
        """The built-in media operations workflow skills are discoverable."""
        resp = client.get("/api/skills")
        assert resp.status_code == 200

        skill_ids = {skill["id"] for skill in resp.json()["skills"]}
        assert "media-ops-orchestration" in skill_ids
        assert "content-research" in skill_ids
        assert "multi-platform-publishing" in skill_ids
        assert "publishing-security-guard" in skill_ids

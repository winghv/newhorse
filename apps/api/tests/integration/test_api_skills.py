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
        assert "benchmark-analysis" in skill_ids
        assert "angle-design" in skill_ids
        assert "competitive-review" in skill_ids
        assert "multi-platform-publishing" in skill_ids
        assert "publishing-security-guard" in skill_ids
        assert "performance-retrospective" in skill_ids
        assert "short-video-production" in skill_ids
        assert "midlong-video-production" in skill_ids
        assert "video-asset-planning" in skill_ids
        assert "minimax-narration-postproduction" in skill_ids
        assert "licensed-footage-sourcing" in skill_ids
        assert "video-postproduction-assembly" in skill_ids
        assert "xiaohongshu-short-video-packaging" in skill_ids
        assert "douyin-short-video-packaging" in skill_ids
        assert "kuaishou-short-video-packaging" in skill_ids
        assert "bilibili-midform-video-packaging" in skill_ids

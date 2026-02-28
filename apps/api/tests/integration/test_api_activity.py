"""Tests for /api/activity/ endpoints."""
import uuid
from app.models.messages import Message


class TestRecentActivity:
    def test_empty_activity(self, client):
        resp = client.get("/api/activity/recent")
        assert resp.status_code == 200
        assert resp.json()["activities"] == []

    def test_returns_chat_messages_with_project(self, client, sample_project, db_session):
        pid = sample_project["id"]
        msg = Message(
            id=str(uuid.uuid4())[:8],
            project_id=pid,
            role="user",
            message_type="chat",
            content="Hello world",
        )
        db_session.add(msg)
        db_session.commit()

        resp = client.get("/api/activity/recent")
        assert resp.status_code == 200
        activities = resp.json()["activities"]
        assert len(activities) == 1
        assert activities[0]["project_name"] == "Test Project"
        assert activities[0]["content"] == "Hello world"

    def test_truncates_long_content(self, client, sample_project, db_session):
        pid = sample_project["id"]
        long_text = "A" * 200
        msg = Message(
            id=str(uuid.uuid4())[:8],
            project_id=pid,
            role="assistant",
            message_type="chat",
            content=long_text,
        )
        db_session.add(msg)
        db_session.commit()

        resp = client.get("/api/activity/recent")
        content = resp.json()["activities"][0]["content"]
        assert len(content) <= 84  # 80 + "..."

    def test_respects_limit(self, client, sample_project, db_session):
        pid = sample_project["id"]
        for i in range(5):
            db_session.add(Message(
                id=str(uuid.uuid4())[:8],
                project_id=pid,
                role="user",
                message_type="chat",
                content=f"Message {i}",
            ))
        db_session.commit()

        resp = client.get("/api/activity/recent?limit=2")
        assert len(resp.json()["activities"]) == 2

    def test_excludes_non_chat_messages(self, client, sample_project, db_session):
        pid = sample_project["id"]
        db_session.add(Message(
            id=str(uuid.uuid4())[:8],
            project_id=pid,
            role="assistant",
            message_type="tool_use",
            content="tool output",
        ))
        db_session.commit()

        resp = client.get("/api/activity/recent")
        assert resp.json()["activities"] == []

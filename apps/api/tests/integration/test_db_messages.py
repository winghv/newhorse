"""Database integration tests for Message model."""

import pytest
from app.models.messages import Message
from app.models.projects import Project


class TestMessageModel:
    """Direct DB tests for Message ORM."""

    def test_create_message(self, db_session):
        """Can create a message directly in DB."""
        project = Project(id="msg-test-001", name="Test", status="active")
        db_session.add(project)
        db_session.commit()

        import uuid
        message = Message(
            id=str(uuid.uuid4()),
            project_id="msg-test-001",
            role="user",
            message_type="chat",
            content="Test content",
        )
        db_session.add(message)
        db_session.commit()

        result = db_session.query(Message).filter(Message.id == message.id).first()
        assert result is not None
        assert result.content == "Test content"

    def test_message_types(self, db_session):
        """Different message types are stored correctly."""
        project = Project(id="msg-test-002", name="Test", status="active")
        db_session.add(project)
        db_session.commit()

        import uuid

        user_msg = Message(
            id=str(uuid.uuid4()),
            project_id="msg-test-002",
            role="user",
            message_type="chat",
            content="User input",
        )
        db_session.add(user_msg)

        assistant_msg = Message(
            id=str(uuid.uuid4()),
            project_id="msg-test-002",
            role="assistant",
            message_type="chat",
            content="Assistant response",
        )
        db_session.add(assistant_msg)
        db_session.commit()

        messages = db_session.query(Message).filter(
            Message.project_id == "msg-test-002"
        ).all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_message_metadata(self, db_session):
        """Message metadata is stored correctly."""
        project = Project(id="msg-test-003", name="Test", status="active")
        db_session.add(project)
        db_session.commit()

        import uuid
        message = Message(
            id=str(uuid.uuid4()),
            project_id="msg-test-003",
            role="assistant",
            message_type="tool_use",
            content="Using tool",
            metadata_json={"tool_name": "read_file", "tool_input": {"path": "test.py"}},
        )
        db_session.add(message)
        db_session.commit()

        result = db_session.query(Message).filter(Message.id == message.id).first()
        assert result.metadata_json is not None
        assert result.metadata_json["tool_name"] == "read_file"

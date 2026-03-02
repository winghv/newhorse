"""Database integration tests for Project model."""

import pytest
from app.models.projects import Project


class TestProjectModel:
    """Direct DB tests for Project ORM."""

    def test_create_project(self, db_session):
        """Can create a project directly in DB."""
        project = Project(
            id="test-001",
            name="DB Test Project",
            description="Testing DB directly",
            preferred_cli="hello",
            selected_model="claude-sonnet-4-5-20250929",
            status="active",
        )
        db_session.add(project)
        db_session.commit()

        result = db_session.query(Project).filter(Project.id == "test-001").first()
        assert result is not None
        assert result.name == "DB Test Project"

    def test_update_project(self, db_session):
        """Can update a project in DB."""
        project = Project(
            id="test-002",
            name="Original Name",
            status="active",
        )
        db_session.add(project)
        db_session.commit()

        project.name = "Updated Name"
        db_session.commit()

        result = db_session.query(Project).filter(Project.id == "test-002").first()
        assert result.name == "Updated Name"

    def test_delete_project(self, db_session):
        """Can delete a project from DB."""
        project = Project(
            id="test-003",
            name="To Delete",
            status="active",
        )
        db_session.add(project)
        db_session.commit()

        db_session.delete(project)
        db_session.commit()

        result = db_session.query(Project).filter(Project.id == "test-003").first()
        assert result is None


class TestProjectRelationships:
    """Test project relationships."""

    def test_project_messages_relationship(self, db_session):
        """Project can have multiple messages."""
        from app.models.messages import Message
        import uuid

        project = Project(
            id="test-004",
            name="Message Test",
            status="active",
        )
        db_session.add(project)

        for i in range(3):
            msg = Message(
                id=str(uuid.uuid4()),
                project_id="test-004",
                role="user",
                message_type="chat",
                content=f"Message {i}",
            )
            db_session.add(msg)
        db_session.commit()

        messages = db_session.query(Message).filter(Message.project_id == "test-004").all()
        assert len(messages) == 3

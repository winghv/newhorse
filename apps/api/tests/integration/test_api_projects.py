"""
Integration tests for /api/projects/ endpoints.
"""


class TestListProjects:
    """GET /api/projects/ — list all projects."""

    def test_empty_list(self, client):
        """Returns an empty list when no projects exist."""
        resp = client.get("/api/projects/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lists_created_projects(self, client, sample_project):
        """Returns projects that have been created."""
        resp = client.get("/api/projects/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        ids = [p["id"] for p in data]
        assert sample_project["id"] in ids


class TestCreateProject:
    """POST /api/projects/ — create a project."""

    def test_create_with_defaults(self, client):
        """Creates a project with only the required 'name' field."""
        resp = client.post("/api/projects/", json={"name": "Minimal Project"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Minimal Project"
        assert data["description"] is None
        assert data["preferred_cli"] == "hello"
        assert data["selected_model"] == "claude-sonnet-4-5-20250929"
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data

    def test_create_with_all_fields(self, client):
        """Creates a project supplying every optional field."""
        payload = {
            "name": "Full Project",
            "description": "A fully specified project",
            "preferred_cli": "claude",
            "selected_model": "claude-opus-4-20250514",
        }
        resp = client.post("/api/projects/", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Full Project"
        assert data["description"] == "A fully specified project"
        assert data["preferred_cli"] == "claude"
        assert data["selected_model"] == "claude-opus-4-20250514"


class TestGetProject:
    """GET /api/projects/{project_id} — get a single project."""

    def test_get_existing(self, client, sample_project):
        """Returns the correct project by ID."""
        project_id = sample_project["id"]
        resp = client.get(f"/api/projects/{project_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == project_id
        assert data["name"] == sample_project["name"]

    def test_get_nonexistent(self, client):
        """Returns 404 for a non-existent project ID."""
        resp = client.get("/api/projects/nonexist")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"


class TestUpdateProject:
    """PATCH /api/projects/{project_id} — partial update."""

    def test_update_name(self, client, sample_project):
        """Updates only the name field."""
        project_id = sample_project["id"]
        resp = client.patch(
            f"/api/projects/{project_id}",
            json={"name": "Renamed Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Renamed Project"
        # Other fields should remain unchanged
        assert data["description"] == sample_project["description"]

    def test_update_nonexistent(self, client):
        """Returns 404 when updating a non-existent project."""
        resp = client.patch(
            "/api/projects/nonexist",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_partial_update(self, client, sample_project):
        """Updates description and selected_model without touching other fields."""
        project_id = sample_project["id"]
        resp = client.patch(
            f"/api/projects/{project_id}",
            json={
                "description": "Updated description",
                "selected_model": "claude-opus-4-20250514",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Updated description"
        assert data["selected_model"] == "claude-opus-4-20250514"
        # Name should remain the original value
        assert data["name"] == sample_project["name"]


class TestDeleteProject:
    """DELETE /api/projects/{project_id} — delete a project."""

    def test_delete_existing(self, client, sample_project):
        """Deletes a project and verifies it is truly gone."""
        project_id = sample_project["id"]
        resp = client.delete(f"/api/projects/{project_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "deleted"
        assert data["id"] == project_id

        # Verify the project is gone
        get_resp = client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent(self, client):
        """Returns 404 when deleting a non-existent project."""
        resp = client.delete("/api/projects/nonexist")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"


class TestListProjectsEdgeCases:
    """Edge cases for project listing."""

    def test_pagination(self, client):
        """Projects should be paginated."""
        # Create multiple projects
        for i in range(15):
            client.post("/api/projects/", json={"name": f"Project {i}"})

        resp = client.get("/api/projects/?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

        resp = client.get("/api/projects/?limit=5&offset=10")
        assert len(data) == 5

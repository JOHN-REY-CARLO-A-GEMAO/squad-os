import os
import pytest
from dashboard import list_projects

def test_list_projects_with_data(tmp_path, monkeypatch):
    # Setup temporary directories
    projects_dir = tmp_path / "projects"
    archives_dir = tmp_path / "archives"
    projects_dir.mkdir()
    archives_dir.mkdir()

    # Create dummy projects
    (projects_dir / "active1").mkdir()
    (projects_dir / "active2").mkdir()
    (projects_dir / "not_a_dir_active").touch()

    (archives_dir / "archived1").mkdir()
    (archives_dir / "not_a_dir_archived").touch()

    monkeypatch.setattr("dashboard.PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr("dashboard.ARCHIVES_DIR", str(archives_dir))

    active, archived = list_projects()

    # Check if they are sorted and only directories are included
    assert active == ["active2", "active1"]
    assert archived == ["archived1"]

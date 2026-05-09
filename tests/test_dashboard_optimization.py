import os
import shutil
import pytest
from dashboard import list_projects, PROJECTS_DIR, ARCHIVES_DIR

@pytest.fixture
def setup_test_dirs(tmp_path, monkeypatch):
    # Use tmp_path to avoid messing with real workspace
    test_projects_dir = tmp_path / "projects"
    test_archives_dir = tmp_path / "archives"
    test_projects_dir.mkdir()
    test_archives_dir.mkdir()

    # Monkeypatch the constants in dashboard.py
    monkeypatch.setattr("dashboard.PROJECTS_DIR", str(test_projects_dir))
    monkeypatch.setattr("dashboard.ARCHIVES_DIR", str(test_archives_dir))

    return test_projects_dir, test_archives_dir

def test_list_projects_empty(setup_test_dirs):
    active, archived = list_projects()
    assert active == []
    assert archived == []

def test_list_projects_with_dirs(setup_test_dirs):
    projects_dir, archives_dir = setup_test_dirs

    # Create some project dirs
    (projects_dir / "proj1").mkdir()
    (projects_dir / "proj2").mkdir()
    (projects_dir / "file1.txt").touch() # Should be ignored

    # Create some archive dirs
    (archives_dir / "arch1").mkdir()
    (archives_dir / "arch2").mkdir()

    active, archived = list_projects()

    assert active == ["proj2", "proj1"] # Sorted reverse
    assert archived == ["arch2", "arch1"] # Sorted reverse
    assert "file1.txt" not in active

def test_list_projects_missing_dir(tmp_path, monkeypatch):
    missing_dir = tmp_path / "non_existent"
    monkeypatch.setattr("dashboard.PROJECTS_DIR", str(missing_dir))
    monkeypatch.setattr("dashboard.ARCHIVES_DIR", str(missing_dir))

    active, archived = list_projects()
    assert active == []
    assert archived == []

def test_visual_artifacts_filtering(tmp_path, monkeypatch):
    import streamlit as st
    from dashboard import PROJECTS_DIR

    project_dir = tmp_path / "projects" / "test_proj"
    visuals_dir = project_dir / "visuals"
    visuals_dir.mkdir(parents=True)

    (visuals_dir / "img1.png").touch()
    (visuals_dir / "img2.jpg").touch()
    (visuals_dir / "vid1.mp4").touch()
    (visuals_dir / "doc1.pdf").touch() # Should be ignored

    monkeypatch.setattr("dashboard.PROJECTS_DIR", str(tmp_path / "projects"))

    img_exts = ('.png', '.jpg', '.jpeg', '.webp')
    vid_exts = ('.mp4', '.webm')
    all_exts = img_exts + vid_exts

    with os.scandir(str(visuals_dir)) as it:
        visual_files = sorted(
            [e.name for e in it if e.is_file() and e.name.lower().endswith(all_exts)],
            reverse=True
        )

    assert "img1.png" in visual_files
    assert "img2.jpg" in visual_files
    assert "vid1.mp4" in visual_files
    assert "doc1.pdf" not in visual_files
    assert visual_files == sorted(["img1.png", "img2.jpg", "vid1.mp4"], reverse=True)

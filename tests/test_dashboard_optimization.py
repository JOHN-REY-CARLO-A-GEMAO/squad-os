import os
import shutil
import pytest
import dashboard

def test_list_projects_optimized(tmp_path):
    # Setup temporary directories
    projects_dir = tmp_path / "projects"
    archives_dir = tmp_path / "archives"
    projects_dir.mkdir()
    archives_dir.mkdir()

    # Mock the constants in dashboard module
    original_projects_dir = dashboard.PROJECTS_DIR
    original_archives_dir = dashboard.ARCHIVES_DIR
    dashboard.PROJECTS_DIR = str(projects_dir)
    dashboard.ARCHIVES_DIR = str(archives_dir)

    try:
        active_test = ["proj_2", "proj_1"]
        archived_test = ["arch_2", "arch_1"]

        for p in active_test:
            (projects_dir / p).mkdir()
        for p in archived_test:
            (archives_dir / p).mkdir()

        # Test
        active, archived = dashboard.list_projects()

        assert active == active_test
        assert archived == archived_test
    finally:
        # Restore original constants
        dashboard.PROJECTS_DIR = original_projects_dir
        dashboard.ARCHIVES_DIR = original_archives_dir

if __name__ == "__main__":
    # If run directly without pytest, use a local temp dir
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        test_list_projects_optimized(Path(tmpdir))
        print("Test list_projects_optimized: PASSED")

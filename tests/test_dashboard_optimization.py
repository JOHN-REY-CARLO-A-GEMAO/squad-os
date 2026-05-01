import os
import shutil
import dashboard
from unittest.mock import MagicMock
import sys

def test_list_projects_optimized():
    test_workspace = "test_pytest_workspace"
    test_projects = os.path.join(test_workspace, "projects")
    test_archives = os.path.join(test_workspace, "archives")

    os.makedirs(test_projects, exist_ok=True)
    os.makedirs(test_archives, exist_ok=True)

    # Setup dummy data
    active_dirs = ["proj_c", "proj_a", "proj_b"]
    archived_dirs = ["arch_2", "arch_1"]

    for d in active_dirs:
        os.makedirs(os.path.join(test_projects, d), exist_ok=True)
    for d in archived_dirs:
        os.makedirs(os.path.join(test_archives, d), exist_ok=True)

    # File that should be ignored
    with open(os.path.join(test_projects, "not_a_dir.txt"), "w") as f:
        f.write("ignore me")

    # Patch dashboard directories
    original_projects_dir = dashboard.PROJECTS_DIR
    original_archives_dir = dashboard.ARCHIVES_DIR
    dashboard.PROJECTS_DIR = test_projects
    dashboard.ARCHIVES_DIR = test_archives

    try:
        active, archived = dashboard.list_projects()

        expected_active = sorted(active_dirs, reverse=True)
        expected_archived = sorted(archived_dirs, reverse=True)

        assert active == expected_active
        assert archived == expected_archived
    finally:
        dashboard.PROJECTS_DIR = original_projects_dir
        dashboard.ARCHIVES_DIR = original_archives_dir
        shutil.rmtree(test_workspace)

import logging
import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any
from squad_os.database.session import DB_PATH
import aiosqlite

logger = logging.getLogger(__name__)

class ProjectBranch:
    def __init__(self, task_id: str, base_dir: str = "workspace"):
        self.task_id = task_id
        self.base_dir = base_dir
        self.project_path = os.path.join(self.base_dir, "projects", self.task_id)
        self.visuals_path = os.path.join(self.project_path, "visuals")
        self.log_path = os.path.join(self.project_path, "session_log.jsonl")
        self.memory_path = os.path.join(self.project_path, "project_memory.md")
        self.is_active = False

    @classmethod
    def create_id(cls, slug: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Remove characters that might be problematic for file systems
        safe_slug = "".join([c if c.isalnum() or c in (" ", "_", "-") else "_" for c in slug])
        # Strip trailing underscores
        safe_slug = safe_slug.strip("_")
        return f"{timestamp}_{safe_slug.replace(' ', '_')}"

    def fork(self):
        os.makedirs(self.project_path, exist_ok=True)
        os.makedirs(self.visuals_path, exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                pass  # Initialize empty JSONL file
        if not os.path.exists(self.memory_path):
            with open(self.memory_path, "w") as f:
                f.write(f"# Project Memory: {self.task_id}\n\n")
        self.is_active = True
        return self.project_path

    def log_tool_call(self, tool_name: str, inputs: Dict[str, Any], output: str):
        log_path = self.log_path
        if not os.path.exists(self.project_path):
            # If the branch is archived, try to find log in archives
            archive_path = os.path.join(self.base_dir, "archives", self.task_id)
            log_path = os.path.join(archive_path, "session_log.jsonl")
            if not os.path.exists(log_path):
                logger.warning(
                    "ProjectBranch.log_tool_call: no log file found for task '%s' at '%s'. "
                    "Expected archived log at '%s'.",
                    self.task_id,
                    self.project_path,
                    log_path,
                )
                return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "inputs": inputs,
            "output": output
        }

        # Optimized: O(1) append instead of O(N) read/write
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    async def commit(self, artifacts: List[str]):

        final_outputs_dir = os.path.join(self.base_dir, "final_outputs")
        os.makedirs(final_outputs_dir, exist_ok=True)

        committed_paths = []
        for artifact in artifacts:
            # Handle both exact matches and glob-like behavior for artifacts in visuals
            possible_sources = []
            if os.path.exists(os.path.join(self.project_path, artifact)):
                possible_sources.append(os.path.join(self.project_path, artifact))
            else:
                # Try to find file by name if it's a direct filename but located in a subfolder like visuals/
                artifact_name = os.path.basename(artifact)
                for root, dirs, files in os.walk(self.project_path):
                    for f in files:
                        # Only accept an exact filename match or files that start with the artifact name.
                        # This avoids overly permissive substring matching that can select unintended files.
                        if f == artifact_name or f.startswith(artifact_name):
                            possible_sources.append(os.path.join(root, f))

            if not possible_sources:
                raise FileNotFoundError(
                    f"Artifact '{artifact}' not found in project path '{self.project_path}' "
                    f"for task '{self.task_id}'. Commit aborted."
                )

            for src in possible_sources:
                dest = os.path.join(final_outputs_dir, f"{self.task_id}_{os.path.basename(src)}")
                if os.path.isdir(src):
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dest)
                committed_paths.append(dest)

        # Update SQLite with project metadata
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    status TEXT,
                    artifacts TEXT,
                    committed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute(
                "INSERT OR REPLACE INTO projects (id, status, artifacts) VALUES (?, ?, ?)",
                (self.task_id, "COMMITTED", json.dumps(committed_paths))
            )
            await db.commit()

        await self.archive()
        return committed_paths

    async def archive(self):
        archive_dir = os.path.join(self.base_dir, "archives")
        os.makedirs(archive_dir, exist_ok=True)

        dest = os.path.join(archive_dir, self.task_id)
        if os.path.exists(self.project_path):
            if os.path.exists(dest):
                # If the archive destination already exists, preserve the existing archive
                # by generating a deterministic unique suffix instead of overwriting it.
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                suffix = 0
                unique_dest = f"{dest}_{timestamp}"
                while os.path.exists(unique_dest):
                    suffix += 1
                    unique_dest = f"{dest}_{timestamp}_{suffix}"
                dest = unique_dest

            shutil.move(self.project_path, dest)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE projects SET status = ? WHERE id = ?",
                ("ARCHIVED", self.task_id)
            )
            await db.commit()
        self.is_active = False

"""
AgentPackageLoader — install, validate, register, and remove .sqad packages.

A .sqad (Squad OS Agent Package) is a zip bundle containing:
  - manifest.json       — metadata
  - workflow.json       — DAG definition (required unless tools-only)
  - tools/              — custom tool Python modules
  - agents/             — custom agent persona JSON definitions
  - assets/             — static resources (prompts, icons, etc.)
  - requirements.txt    — pip dependencies

You can author a package as a single squad.yaml file and compile it with:
    squad build ./squad.yaml
"""
import json
import os
import re
import shutil
import yaml
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from squad_os.tools.base import BaseTool
from squad_os.core.utils import is_safe_path


PACKAGES_DIR = os.path.join("workspace", "packages")
MINIMUM_MANIFEST_FIELDS = {"id", "name", "version"}
SAFE_MODULE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class PackageValidationResult:
    def __init__(self, valid: bool, errors: List[str], warnings: List[str] = None):
        self.valid = valid
        self.errors = errors
        self.warnings = warnings or []

    def __bool__(self):
        return self.valid


class AgentPackage:
    """Represents a loaded and validated .sqad package in memory."""

    def __init__(self, manifest: Dict, source_path: str):
        self.manifest = manifest
        self.package_id: str = manifest["id"]
        self.name: str = manifest["name"]
        self.version: str = manifest["version"]
        self.source_path: str = source_path
        self.workflow: Optional[Dict] = None
        self.custom_tools: List[Dict] = []
        self.custom_agents: List[Dict] = []
        self.dependencies: List[str] = []
        self.assets: List[str] = []


class AgentPackageLoader:
    """Handles loading, validation, registration, and removal of .sqad packages."""

    @staticmethod
    def validate_manifest(data: Dict) -> PackageValidationResult:
        errors = []
        missing = MINIMUM_MANIFEST_FIELDS - set(data.keys())
        if missing:
            errors.append(f"Missing required manifest fields: {', '.join(sorted(missing))}")

        pkg_id = data.get("id", "")
        if not re.match(r'^[a-zA-Z0-9_-]+$', pkg_id):
            errors.append(f"Invalid package id '{pkg_id}': must match [a-zA-Z0-9_-]+")

        version = data.get("version", "")
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            errors.append(f"Invalid version '{version}': must be semver (X.Y.Z)")

        return PackageValidationResult(len(errors) == 0, errors)

    @staticmethod
    def validate_workflow(data: Dict) -> PackageValidationResult:
        errors = []
        if "tasks" not in data or not isinstance(data["tasks"], list):
            errors.append("workflow.json must contain a 'tasks' array")
            return PackageValidationResult(False, errors)

        for i, task in enumerate(data["tasks"]):
            if "description" not in task:
                errors.append(f"Task {i} is missing 'description'")
            if "assigned_agent_role" not in task:
                errors.append(f"Task {i} is missing 'assigned_agent_role'")
            if not isinstance(task.get("depends_on", []), list):
                errors.append(f"Task {i} 'depends_on' must be a list")

        # Check that depends_on indices are valid
        task_count = len(data["tasks"])
        for i, task in enumerate(data["tasks"]):
            for dep in task.get("depends_on", []):
                if not isinstance(dep, int) or dep < 0 or dep >= task_count or dep >= i:
                    errors.append(f"Task {i} has invalid depends_on index {dep}")

        return PackageValidationResult(len(errors) == 0, errors)

    @staticmethod
    def validate_tool_source(module_name: str, source_code: str) -> PackageValidationResult:
        errors = []
        warnings = []

        if not SAFE_MODULE_NAME_RE.match(module_name):
            errors.append(f"Invalid tool module name '{module_name}'")

        if "os.system" in source_code or "subprocess.call" in source_code:
            warnings.append(f"Tool '{module_name}' uses dangerous calls (os.system, subprocess.call) — requires user approval")

        forbidden = ["eval(", "exec(", "compile(", "__import__"]
        for pattern in forbidden:
            if pattern in source_code:
                errors.append(f"Tool '{module_name}' contains forbidden pattern: {pattern}")

        return PackageValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def load_sqad(file_path: str) -> Optional[AgentPackage]:
        if not os.path.exists(file_path):
            print(f"  [PackageLoader] File not found: {file_path}")
            return None

        if not file_path.endswith(".sqad"):
            print(f"  [PackageLoader] Invalid extension: {file_path} (must be .sqad)")
            return None

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Validate structure
                all_files = zf.namelist()

                if "manifest.json" not in all_files:
                    print(f"  [PackageLoader] Missing manifest.json in {file_path}")
                    return None

                manifest = json.loads(zf.read("manifest.json"))

                pkg = AgentPackage(manifest, file_path)

                # Workflow (optional — a package could be tools-only)
                if "workflow.json" in all_files:
                    pkg.workflow = json.loads(zf.read("workflow.json"))

                # Custom tools
                tool_files = [f for f in all_files if f.startswith("tools/") and f.endswith(".py")]
                for tf in tool_files:
                    module_name = os.path.splitext(os.path.basename(tf))[0]
                    source = zf.read(tf).decode("utf-8")
                    pkg.custom_tools.append({
                        "module_name": module_name,
                        "source": source,
                        "path": tf
                    })

                # Custom agents
                agent_files = [f for f in all_files if f.startswith("agents/") and f.endswith(".json")]
                for af in agent_files:
                    agent_data = json.loads(zf.read(af))
                    pkg.custom_agents.append(agent_data)

                # Dependencies
                if "requirements.txt" in all_files:
                    deps_text = zf.read("requirements.txt").decode("utf-8").strip()
                    if deps_text:
                        pkg.dependencies = [d.strip() for d in deps_text.splitlines() if d.strip()]

                # Assets
                pkg.assets = [f for f in all_files if f.startswith("assets/")]

            return pkg

        except json.JSONDecodeError as e:
            print(f"  [PackageLoader] JSON error in {file_path}: {e}")
            return None
        except zipfile.BadZipFile as e:
            print(f"  [PackageLoader] Bad zip in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"  [PackageLoader] Failed to load {file_path}: {e}")
            return None

    @staticmethod
    def validate_package(pkg: AgentPackage) -> PackageValidationResult:
        all_errors = []
        all_warnings = []

        result = AgentPackageLoader.validate_manifest(pkg.manifest)
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)

        if pkg.workflow:
            result = AgentPackageLoader.validate_workflow(pkg.workflow)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

            # Check required tools exist in the manifest
            required_tools = pkg.workflow.get("required_tools", [])
            for tool_name in required_tools:
                if tool_name not in pkg.manifest.get("assumes_tools", []):
                    all_warnings.append(f"Workflow requires tool '{tool_name}' but manifest does not list it in 'assumes_tools'")

        for tool in pkg.custom_tools:
            result = AgentPackageLoader.validate_tool_source(tool["module_name"], tool["source"])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        for agent in pkg.custom_agents:
            if "role" not in agent or "goal" not in agent:
                all_errors.append(f"Custom agent definition missing 'role' or 'goal': {agent.get('role', 'unknown')}")

        return PackageValidationResult(len(all_errors) == 0, all_errors, all_warnings)

    @staticmethod
    async def install_package(pkg: AgentPackage, approval_func=None) -> bool:
        """Install a validated package: extract, register, persist.

        approval_func is an optional async callable(pkg) -> bool for HITL.
        """
        # Validate first
        validation = AgentPackageLoader.validate_package(pkg)
        if not validation:
            print(f"  [PackageLoader] Package '{pkg.package_id}' validation failed:")
            for err in validation.errors:
                print(f"    ERROR: {err}")
            for warn in validation.warnings:
                print(f"    WARNING: {warn}")
            if validation.errors:
                return False

        # HITL approval gate
        if approval_func:
            approved = await approval_func(pkg)
            if not approved:
                print(f"  [PackageLoader] Package '{pkg.package_id}' installation rejected by user.")
                return False

        # Extract to workspace
        install_dir = os.path.join(PACKAGES_DIR, f"{pkg.package_id}__{pkg.version}")
        os.makedirs(install_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(pkg.source_path, "r") as zf:
                zf.extractall(install_dir)
            print(f"  [PackageLoader] Extracted '{pkg.package_id}' to {install_dir}")
        except Exception as e:
            print(f"  [PackageLoader] Extraction failed: {e}")
            shutil.rmtree(install_dir, ignore_errors=True)
            return False

        # Persist to SQLite
        await AgentPackageLoader._save_to_db(pkg, install_dir)

        # Register custom tools into SkillRegistry
        from squad_os.tools.marketplace import SkillRegistry
        SkillRegistry._instance = None  # Force re-discovery on next access
        print(f"  [PackageLoader] SkillRegistry invalidated — tools will be re-discovered.")
        return True

    @staticmethod
    async def _save_to_db(pkg: AgentPackage, install_dir: str):
        from squad_os.database.session import DB_PATH
        import aiosqlite

        async with aiosqlite.connect(DB_PATH) as db:
            # Ensure store tables exist
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS store_packages (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    author TEXT,
                    description TEXT,
                    min_squad_os_version TEXT,
                    tags TEXT,
                    source_url TEXT,
                    install_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS installed_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    install_path TEXT NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES store_packages(id)
                );
                CREATE TABLE IF NOT EXISTS store_tools (
                    id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    parameters TEXT,
                    entry_point TEXT,
                    dependencies TEXT,
                    FOREIGN KEY (package_id) REFERENCES store_packages(id)
                );
                CREATE TABLE IF NOT EXISTS store_workflows (
                    id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    workflow TEXT NOT NULL,
                    FOREIGN KEY (package_id) REFERENCES store_packages(id)
                );
            """)

            # Upsert store_packages
            await db.execute("""
                INSERT OR REPLACE INTO store_packages
                    (id, name, version, author, description, min_squad_os_version, tags, source_url, install_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                    COALESCE((SELECT install_count FROM store_packages WHERE id = ?), 0) + 1)
            """, (
                pkg.package_id, pkg.name, pkg.version,
                pkg.manifest.get("author", ""),
                pkg.manifest.get("description", ""),
                pkg.manifest.get("min_squad_os_version", ""),
                json.dumps(pkg.manifest.get("tags", [])),
                pkg.source_path,
                pkg.package_id
            ))

            # Record installation
            await db.execute("""
                INSERT INTO installed_packages (package_id, version, install_path, status)
                VALUES (?, ?, ?, 'ACTIVE')
            """, (pkg.package_id, pkg.version, install_dir))

            # Save workflow if present
            if pkg.workflow:
                wf_name = pkg.workflow.get("name") or f"{pkg.package_id} workflow"
                wf_desc = pkg.workflow.get("description") or ""
                await db.execute("""
                    INSERT OR REPLACE INTO store_workflows (id, package_id, name, description, workflow)
                    VALUES (?, ?, ?, ?, ?)
                """, (f"{pkg.package_id}__workflow", pkg.package_id, wf_name, wf_desc,
                      json.dumps(pkg.workflow)))

            # Save custom tools
            for tool in pkg.custom_tools:
                tool_id = f"{pkg.package_id}.{tool['module_name']}"
                await db.execute("""
                    INSERT OR REPLACE INTO store_tools (id, package_id, name, description, parameters, entry_point, dependencies)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tool_id, pkg.package_id, tool['module_name'],
                    pkg.manifest.get("description", ""),
                    "{}",
                    f"tools/{tool['module_name']}.py",
                    json.dumps(pkg.dependencies)
                ))

            # Save custom agents (inline to avoid DB locking from separate connection)
            for agent in pkg.custom_agents:
                await db.execute(
                    "INSERT OR REPLACE INTO agent_personas (role, goal, backstory, tools) VALUES (?, ?, ?, ?)",
                    (agent["role"], agent.get("goal", ""), agent.get("backstory", ""),
                     json.dumps(agent.get("tools", [])))
                )

            await db.commit()

        print(f"  [PackageLoader] Package '{pkg.package_id}' v{pkg.version} registered in database.")

    @staticmethod
    async def uninstall_package(package_id: str) -> bool:
        """Remove a package and its artifacts."""
        from squad_os.database.session import DB_PATH
        import aiosqlite

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT install_path FROM installed_packages WHERE package_id = ? AND status = 'ACTIVE'", (package_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                print(f"  [PackageLoader] Package '{package_id}' not installed.")
                return False

            install_path = row[0]

            # Remove files
            if os.path.exists(install_path):
                shutil.rmtree(install_path, ignore_errors=True)

            # Update DB
            await db.execute("DELETE FROM store_workflows WHERE package_id = ?", (package_id,))
            await db.execute("DELETE FROM store_tools WHERE package_id = ?", (package_id,))
            await db.execute("DELETE FROM installed_packages WHERE package_id = ?", (package_id,))
            await db.execute("DELETE FROM store_packages WHERE id = ?", (package_id,))
            await db.commit()

        # Force SkillRegistry re-discovery
        from squad_os.tools.marketplace import SkillRegistry
        SkillRegistry._instance = None

        print(f"  [PackageLoader] Package '{package_id}' fully removed.")
        return True

    @staticmethod
    def get_tool_discovery_paths() -> List[str]:
        """Return list of directories where custom tool modules live.
        Called by SkillRegistry during discovery."""
        if not os.path.exists(PACKAGES_DIR):
            return []
        paths = []
        for entry in os.listdir(PACKAGES_DIR):
            tools_dir = os.path.join(PACKAGES_DIR, entry, "tools")
            if os.path.isdir(tools_dir):
                paths.append(tools_dir)
        return paths

    @staticmethod
    def build_sqad_from_yaml(yaml_path: str, output_path: Optional[str] = None) -> str:
        """Compile a squad.yaml file into a .sqad package zip.

        Args:
            yaml_path: Path to the squad.yaml file.
            output_path: Output .sqad path (default: <yaml_dir>/<id>.sqad).

        Returns:
            Path to the generated .sqad file.
        """
        from squad_os.store.schema import SquadManifest

        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        manifest = SquadManifest(**raw)
        bundle = manifest.to_bundle()

        yaml_dir = os.path.dirname(os.path.abspath(yaml_path))
        if not output_path:
            output_path = os.path.join(yaml_dir, f"{manifest.id}.sqad")

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(bundle["manifest"], indent=2))

            if bundle["workflow"]:
                zf.writestr("workflow.json", json.dumps(bundle["workflow"], indent=2))

            for agent in bundle["agents"]:
                safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', agent["role"])
                zf.writestr(f"agents/{safe_name}.json", json.dumps(agent, indent=2))

            yaml_dir_path = Path(yaml_dir)
            tools_dir = yaml_dir_path / "tools"
            if tools_dir.is_dir():
                for tf in sorted(tools_dir.iterdir()):
                    if tf.suffix == ".py" and not tf.name.startswith("_"):
                        zf.write(str(tf), f"tools/{tf.name}")

            assets_dir = yaml_dir_path / "assets"
            if assets_dir.is_dir():
                for af in sorted(assets_dir.rglob("*")):
                    if af.is_file():
                        zf.write(str(af), f"assets/{af.relative_to(assets_dir)}")

            req_file = yaml_dir_path / "requirements.txt"
            if req_file.is_file():
                zf.write(str(req_file), "requirements.txt")

            readme_file = yaml_dir_path / "README.md"
            if readme_file.is_file():
                zf.write(str(readme_file), "README.md")

        print(f"  [PackageLoader] Built {output_path} ({os.path.getsize(output_path):,} bytes)")
        return output_path

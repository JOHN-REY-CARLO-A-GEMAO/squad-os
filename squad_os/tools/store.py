"""
Store tools — browse, install, run, and remove .sqad Agent Store packages.
"""
import json
import os
from typing import Optional, List
from squad_os.tools.base import BaseTool



class BrowseStoreTool(BaseTool):
    name = "browse_store"
    description = (
        "Browse the Agent Store for available workflow packages. "
        "Filter by search query or tag. Returns package names, versions, authors, and install counts."
    )
    parameters = {
        "type": "object",
        "properties": {
            "search": {
                "type": "string",
                "description": "Search package names and descriptions"
            },
            "tag": {
                "type": "string",
                "description": "Filter by tag (e.g. 'code-review', 'test', 'deployment')"
            },
            "installed_only": {
                "type": "boolean",
                "description": "Only show already-installed packages"
            }
        },
        "required": []
    }
    category = "marketplace"

    async def execute(self, search: Optional[str] = None, tag: Optional[str] = None, installed_only: bool = False) -> str:
        from squad_os.database.session import DB_PATH
        import aiosqlite

        async with aiosqlite.connect(DB_PATH) as db:
            query = """
                SELECT p.id, p.name, p.version, p.author, p.description, p.tags, p.install_count,
                       COALESCE(i.status, 'NOT_INSTALLED') as install_status, i.version as installed_version
                FROM store_packages p
                LEFT JOIN installed_packages i ON p.id = i.package_id AND i.status = 'ACTIVE'
                WHERE 1=1
            """
            params = []

            if installed_only:
                query += " AND i.status = 'ACTIVE'"
            if tag:
                query += " AND p.tags LIKE ?"
                params.append(f"%{tag}%")
            if search:
                query += " AND (p.name LIKE ? OR p.description LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            query += " ORDER BY p.install_count DESC, p.name ASC"

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                columns = [d[0] for d in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]

        if not results:
            return "No packages found in the Agent Store."

        lines = [f"Agent Store — {len(results)} package(s):"]
        for r in results:
            tags_list = json.loads(r["tags"]) if r["tags"] else []
            tag_str = f" [{', '.join(tags_list[:3])}]" if tags_list else ""
            installs = r["install_count"] or 0
            status = "✅ INSTALLED" if r["install_status"] == "ACTIVE" else "⬇️ AVAILABLE"
            lines.append(
                f"  {status} {r['name']} v{r['version']} by {r['author'] or 'unknown'}{tag_str}"
                f" — {r['description'] or ''[:80]} ({installs} installs)"
            )

        return "\n".join(lines)


class InstallPackageTool(BaseTool):
    name = "install_package"
    description = (
        "Install a .sqad Agent Store package from a local file path or from the store catalog by package ID. "
        "Validates the package, checks for dangerous patterns, and registers it in the system. "
        "Installation ALWAYS requires human approval (HITL) — it cannot be skipped by an agent."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Path to a .sqad file, or a package ID already in the store catalog"
            }
        },
        "required": ["source"]
    }
    category = "marketplace"

    async def execute(self, source: str) -> str:
        from squad_os.database.session import DB_PATH
        import aiosqlite

        from squad_os.store.loader import AgentPackageLoader
        pkg = None

        if source.endswith(".sqad") and os.path.exists(source):
            pkg = AgentPackageLoader.load_sqad(source)
            if not pkg:
                return f"Failed to load package from {source}."
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT source_url FROM store_packages WHERE id = ?", (source,)
                ) as cursor:
                    row = await cursor.fetchone()
            if row:
                pkg_path = row[0]
                if os.path.exists(pkg_path):
                    pkg = AgentPackageLoader.load_sqad(pkg_path)
            if not pkg:
                return f"Package '{source}' not found. Use 'browse_store' to list available packages."

        validation = AgentPackageLoader.validate_package(pkg)
        warnings_str = ""
        if validation.warnings:
            warnings_str = "\nWarnings:\n" + "\n".join(f"  ⚠️ {w}" for w in validation.warnings)

        if not validation:
            errors_str = "\n".join(f"  ❌ {e}" for e in validation.errors)
            return f"Package '{pkg.package_id}' validation FAILED:{errors_str}{warnings_str}"

        async def approval_fn(p):
            from squad_os.database.session import create_approval_request, get_approval_status
            details = (
                f"Install package '{p.name}' v{p.version} by {p.manifest.get('author', 'unknown')}?\n"
                f"  Description: {p.manifest.get('description', 'N/A')}\n"
                f"  Custom tools: {len(p.custom_tools)}\n"
                f"  Custom agents: {len(p.custom_agents)}\n"
                f"  Dependencies: {len(p.dependencies)}\n"
                f"  Warnings: {warnings_str[:200] if warnings_str else 'None'}"
            )
            approval_id = await create_approval_request(mission_id=0, task_id=0, message=details)
            print(f"  [InstallPackage]: HITL approval #{approval_id} created — waiting for response...")
            import asyncio
            import time
            timeout = float(os.getenv("SQUAD_OS_INSTALL_APPROVAL_TIMEOUT", "600"))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                response = await get_approval_status(approval_id)
                if response and response["status"] != "PENDING":
                    if response["status"] == "APPROVED":
                        print(f"  [InstallPackage]: HITL approved.")
                        return True
                    print(f"  [InstallPackage]: HITL rejected: {response.get('feedback', 'No reason given')}")
                    return False
                await asyncio.sleep(2)
            print(f"  [InstallPackage]: HITL approval #{approval_id} timed out after {int(timeout)}s — aborting install.")
            return False

        # Package installation executes arbitrary code (custom tools are
        # imported at discovery) — human approval is ALWAYS required and can
        # never be skipped by an agent.
        success = await AgentPackageLoader.install_package(pkg, approval_func=approval_fn)

        if success:
            msg = f"✅ Package '{pkg.name}' v{pkg.version} installed successfully."
            if pkg.workflow:
                msg += f"\n   Workflow '{pkg.workflow.get('name', 'default')}' is ready. Run it with 'run_workflow({pkg.package_id})'."
            return msg
        return f"❌ Package '{pkg.package_id}' installation failed."


class RunWorkflowTool(BaseTool):
    name = "run_workflow"
    description = (
        "Execute a stored workflow from an installed Agent Store package as a mission. "
        "Provide the package ID to run its workflow. Optionally provide custom input data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "package_id": {
                "type": "string",
                "description": "Package ID of the installed workflow to run"
            },
            "custom_goal": {
                "type": "string",
                "description": "Override the mission goal with custom instructions"
            }
        },
        "required": ["package_id"]
    }
    category = "marketplace"

    async def execute(self, package_id: str, custom_goal: Optional[str] = None) -> str:
        from squad_os.database.session import DB_PATH, create_mission, update_mission, get_all_personas
        from squad_os.agents.base import BaseAgent
        from squad_os.tools.marketplace import SkillRegistry
        from squad_os.orchestrator.manager import Manager
        import aiosqlite

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT w.workflow, i.install_path FROM store_workflows w "
                "JOIN installed_packages i ON w.package_id = i.package_id "
                "WHERE w.package_id = ? AND i.status = 'ACTIVE'",
                (package_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return f"Workflow for package '{package_id}' not found or not installed."

        workflow = json.loads(row[0])
        workflow_name = workflow.get("name", package_id)
        goal = custom_goal or workflow.get("description") or f"Execute workflow: {workflow_name}"

        registry = SkillRegistry.get_instance()
        tool_inventory = {t["name"]: registry.get_tool(t["name"]) for t in registry.list_tools()}
        tool_inventory = {k: v for k, v in tool_inventory.items() if v is not None}

        model_name = os.environ.get("SQUAD_OS_MODEL", "ollama/glm-4.7")
        manager = Manager(tool_inventory=list(tool_inventory.values()), model_name=model_name)
        manager.active_agents = {}

        required_roles = workflow.get("required_agents", [])
        for task in workflow.get("tasks", []):
            role = task.get("assigned_agent_role", "Assistant")
            if role not in required_roles:
                required_roles.append(role)

        for role in required_roles:
            manager.active_agents[role] = BaseAgent(
                role=role,
                goal=f"Execute your assigned task for workflow: {workflow_name}",
                backstory=f"You are a {role} executing a workflow from the Agent Store.",
                tools=list(tool_inventory.values()),
                model_name=model_name
            )

        mission_id = await create_mission(goal)
        print(f"  [RunWorkflow] Starting mission {mission_id} for workflow '{workflow_name}'...")

        try:
            from squad_os.core.projects import ProjectBranch
            branch_id = ProjectBranch.create_id(goal[:30])
            shared_branch = ProjectBranch(branch_id)
            shared_branch.fork()

            for agent in manager.active_agents.values():
                agent.active_branch = shared_branch

            from squad_os.orchestrator.manager import TaskPlan, MissionPlan
            task_plans = []
            for i, t in enumerate(workflow.get("tasks", [])):
                task_plans.append(TaskPlan(
                    description=t["description"],
                    assigned_agent_role=t.get("assigned_agent_role", "Assistant"),
                    depends_on=t.get("depends_on", []),
                    priority=t.get("priority", 1),
                    estimated_complexity=t.get("estimated_complexity", "medium"),
                    is_swarm=t.get("is_swarm", False),
                    swarm_roles=t.get("swarm_roles", [])
                ))

            plan = MissionPlan(
                tasks=task_plans,
                suggested_parallelism=workflow.get("suggested_parallelism", 2)
            )
            manager.plan_mission_obj = plan

            await manager.execute_dag(
                plan.tasks, mission_id, goal, shared_branch
            )
            await update_mission(mission_id, "COMPLETED")
            return f"✅ Workflow '{workflow_name}' completed as mission #{mission_id}."
        except Exception as e:
            await update_mission(mission_id, "FAILED")
            return f"❌ Workflow '{workflow_name}' failed: {e}"


class UninstallPackageTool(BaseTool):
    name = "uninstall_package"
    description = "Remove an installed package from the system. Deletes files and database entries."
    parameters = {
        "type": "object",
        "properties": {
            "package_id": {
                "type": "string",
                "description": "Package ID to uninstall"
            }
        },
        "required": ["package_id"]
    }
    category = "marketplace"

    async def execute(self, package_id: str) -> str:
        from squad_os.store.loader import AgentPackageLoader
        success = await AgentPackageLoader.uninstall_package(package_id)
        if success:
            return f"✅ Package '{package_id}' uninstalled successfully."
        return f"❌ Package '{package_id}' not found or could not be uninstalled."

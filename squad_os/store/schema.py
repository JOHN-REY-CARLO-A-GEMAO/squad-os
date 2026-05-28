"""
Pydantic models for the squad.yaml manifest format.

A squad.yaml is the human-authored entry point for .sqad packages.
The `squad build` CLI compiles it into a .sqad zip for distribution.

Schema version: 1.0.0
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


# ─── Top-Level Metadata ───────────────────────────────────────────────

class MetadataDef(BaseModel):
    """Package identity — name, version, author, license."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = ""


# ─── Topology: Agents ─────────────────────────────────────────────────

class AgentDef(BaseModel):
    """A single node in the execution DAG."""

    id: str
    role: str
    system_prompt: str = ""
    llm_default: str = ""
    tools: List[str] = Field(default_factory=list)


# ─── Topology: Dependencies (DAG edges) ───────────────────────────────

class DependencyDef(BaseModel):
    """A directed edge between two agent nodes, gated by an optional condition.

    The condition expression is evaluated at runtime against the shared
    mission context. Only when the condition resolves to true is the child
    agent dispatched.
    """

    parent: str
    child: str
    condition: str = ""


class TopologyDef(BaseModel):
    """Describes the execution graph and its participant agents."""

    engine: str = "dag"
    agents: List[AgentDef] = Field(default_factory=list)
    dependencies: List[DependencyDef] = Field(default_factory=list)


# ─── Runtime Constraints ──────────────────────────────────────────────

class RequiredToolDef(BaseModel):
    """A tool that must be available in the runtime environment."""

    name: str
    min_version: str = ""


class RuntimeDef(BaseModel):
    """Sandbox and environment requirements for the squad execution."""

    required_tools: List[RequiredToolDef] = Field(default_factory=list)
    environment_defaults: Dict[str, str] = Field(default_factory=dict)


# ─── Top-Level Manifest ───────────────────────────────────────────────

class SquadManifest(BaseModel):
    """Top-level schema for squad.yaml (spec v1.0.0).

    This is the *human-facing* format.  It is intentionally richer than the
    internal .sqad bundle representation.  The ``to_bundle()`` method
    translates it down to the compact format the runtime engine expects.
    """

    spec_version: str = "1.0.0"
    metadata: MetadataDef
    topology: TopologyDef = Field(default_factory=TopologyDef)
    runtime: RuntimeDef = Field(default_factory=RuntimeDef)

    # ── helpers ────────────────────────────────────────────────────

    def _agent_by_id(self, agent_id: str) -> Optional[AgentDef]:
        for a in self.topology.agents:
            if a.id == agent_id:
                return a
        return None

    def to_bundle(self) -> Dict[str, Any]:
        """Translate to the internal .sqad bundle representation.

        The bundle contains three top-level keys:
          - ``manifest`` – package metadata
          - ``agents``   – list of agent persona dicts (CrewAI-compatible)
          - ``workflow`` – task graph with ``depends_on`` as int indices
        """
        m = self.metadata

        # ── manifest ────────────────────────────────────────────────
        manifest = {
            "id": m.name.lower().replace(" ", "_").replace("-", "_"),
            "name": m.name,
            "version": m.version,
            "author": m.author,
            "description": m.description,
            "license": m.license,
            "min_squad_os_version": "",
            "tags": [],
            "assumes_tools": list(dict.fromkeys(
                tool for agent in self.topology.agents for tool in agent.tools
            )),
        }

        # ── agents ──────────────────────────────────────────────────
        agents_data = []
        for agent in self.topology.agents:
            agents_data.append({
                "role": agent.role,
                "goal": agent.system_prompt,
                "backstory": "",
                "tools": agent.tools,
                "llm_default": agent.llm_default,
            })

        # ── workflow (translate string IDs → int indices) ──────────
        id_to_idx: Dict[str, int] = {
            a.id: i for i, a in enumerate(self.topology.agents)
        }

        tasks = []
        for agent in self.topology.agents:
            depends_on: List[int] = []
            for dep in self.topology.dependencies:
                if dep.child == agent.id:
                    parent_idx = id_to_idx.get(dep.parent)
                    if parent_idx is not None:
                        depends_on.append(parent_idx)

            task = {
                "description": agent.system_prompt,
                "assigned_agent_role": agent.role,
                "depends_on": sorted(set(depends_on)),
                "priority": 1,
                "estimated_complexity": "medium",
                "is_swarm": False,
                "swarm_roles": [],
                "llm_default": agent.llm_default,
            }
            # Attach conditions so the DAG runner can gate execution
            conditions = [
                dep.condition
                for dep in self.topology.dependencies
                if dep.child == agent.id and dep.condition
            ]
            if conditions:
                task["conditions"] = conditions

            tasks.append(task)

        workflow = {
            "name": f"{m.name} workflow",
            "description": m.description,
            "suggested_parallelism": len(self.topology.agents),
            "tasks": tasks,
            "required_tools": manifest["assumes_tools"],
            "required_agents": [a.role for a in self.topology.agents],
            "environment_defaults": self.runtime.environment_defaults,
        }

        return {
            "manifest": manifest,
            "agents": agents_data,
            "workflow": workflow,
        }


# ─── Registry Entry (packages.json) ───────────────────────────────────

class RegistryPackageEntry(BaseModel):
    """A single entry in the community package registry (``packages.json``).

    Validated by CI — every PR touching ``packages.json`` runs
    ``validate-package.yml`` which ensures each entry matches this schema
    and that its ``squad.yaml`` is parseable by ``SquadManifest``.
    """

    id: str = Field(..., description="Unique lowercase alphanumeric slug (e.g. devops-self-healer)")
    name: str
    description: str = ""
    source_url: str
    manifest_path: str = "main/squad.yaml"

    @field_validator("id")
    @classmethod
    def validate_id_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9\-]+$", v):
            raise ValueError(
                "Registry ID must be lowercase, alphanumeric, with hyphens only."
            )
        return v

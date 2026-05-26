"""
Pydantic models for the squad.yaml manifest format.

A squad.yaml is the human-authored entry point for .sqad packages.
The `squad build` CLI compiles it into a .sqad zip for distribution.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AuthorInfo(BaseModel):
    handle: str = ""
    url: str = ""


class AgentDef(BaseModel):
    role: str
    goal: str
    backstory: str = ""
    tools: List[str] = Field(default_factory=list)


class TaskDef(BaseModel):
    description: str
    assigned_agent_role: str
    depends_on: List[int] = Field(default_factory=list)
    priority: int = 1
    estimated_complexity: str = "medium"
    is_swarm: bool = False
    swarm_roles: List[str] = Field(default_factory=list)


class WorkflowDef(BaseModel):
    name: str = ""
    description: str = ""
    suggested_parallelism: int = 2
    tasks: List[TaskDef]


class SquadManifest(BaseModel):
    """Top-level schema for squad.yaml."""

    id: str
    name: str
    version: str
    author: Optional[AuthorInfo] = None
    description: str = ""
    min_squad_os_version: str = ""
    tags: List[str] = Field(default_factory=list)
    assumes_tools: List[str] = Field(default_factory=list)
    agents: List[AgentDef] = Field(default_factory=list)
    workflow: Optional[WorkflowDef] = None

    def to_bundle(self) -> Dict[str, Any]:
        """Convert to the internal bundle representation (manifest.json + workflow.json)."""
        manifest = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author.handle if self.author else "",
            "description": self.description,
            "min_squad_os_version": self.min_squad_os_version,
            "tags": self.tags,
            "assumes_tools": self.assumes_tools,
        }

        agents_data = []
        for a in self.agents:
            agents_data.append({
                "role": a.role,
                "goal": a.goal,
                "backstory": a.backstory,
                "tools": a.tools,
            })

        workflow_data = None
        if self.workflow:
            workflow_data = {
                "name": self.workflow.name or f"{self.name} workflow",
                "description": self.workflow.description or self.description,
                "suggested_parallelism": self.workflow.suggested_parallelism,
                "tasks": [t.model_dump() for t in self.workflow.tasks],
                "required_tools": self.assumes_tools,
                "required_agents": list(dict.fromkeys(
                    [t.assigned_agent_role for t in self.workflow.tasks]
                )),
            }

        return {
            "manifest": manifest,
            "agents": agents_data,
            "workflow": workflow_data,
        }

import os
from squad_os.tools.base import BaseTool

class FetchPRDiffTool(BaseTool):
    name = "fetch_pr_diff"
    description = "Fetches the diff for a specified GitHub Pull Request."
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "Repo name (owner/repo)"},
            "pr_number": {"type": "integer", "description": "PR number"}
        },
        "required": ["repo", "pr_number"]
    }

    async def execute(self, repo: str, pr_number: int) -> str:
        # Mock implementation for demo
        return f"Fetched diff for {repo} PR #{pr_number}. Content: + def safe_query(q): pass"

from typing import Any, Dict

class BaseTool:
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    async def execute(self, **kwargs) -> str:
        raise NotImplementedError("Subclasses must implement execute")

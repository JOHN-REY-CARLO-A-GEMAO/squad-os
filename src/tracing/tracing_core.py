import uuid
import time
from typing import List, Dict, Any, Optional

class RunRegistry:
    _registry: Dict[str, Dict[str, Any]] = {}
    @classmethod
    def register_run(cls, run_id: str, initial_context: Dict[str, Any]):
        cls._registry[run_id] = initial_context
    @classmethod
    def get_run(cls, run_id: str) -> Optional[Dict[str, Any]]:
        return cls._registry.get(run_id)

class TraceCollector:
    def __init__(self, run_id: str, task_id: str, source_component: str, initial_payload: Dict[str, Any]):
        self.run_id, self.task_id, self.source_component = run_id, task_id, source_component
        self.context = RunRegistry.get_run(run_id)

    def record_event(self, event_type: str, description: str, dependencies: List[str] = None, payload: Dict[str, Any] = None):
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "source_component": self.source_component,
            "description": description,
            "dependencies": dependencies or [],
            "metadata": {"task_id": self.task_id},
            "payload": payload or {},
            "child_events": []
        }
        return event
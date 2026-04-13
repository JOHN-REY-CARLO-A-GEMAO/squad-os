import uuid
import time
from typing import List, Dict, Any, Optional

class RunRegistry:
    _registry: Dict[str, Dict[str, Any]] = {}
    @classmethod
    def register_run(cls, run_id: str, initial_context: Dict[str, Any]):
        """
        Store or overwrite the execution context for a given run identifier in the class-level registry.
        
        Parameters:
            run_id (str): Unique identifier for the run.
            initial_context (Dict[str, Any]): Context dictionary to associate with `run_id`.
        """
        cls._registry[run_id] = initial_context
    @classmethod
    def get_run(cls, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the stored context for the specified run identifier.
        
        Parameters:
            run_id (str): Identifier of the run to look up.
        
        Returns:
            The context dictionary associated with the given `run_id`, or `None` if no context is registered.
        """
        return cls._registry.get(run_id)

class TraceCollector:
    def __init__(self, run_id: str, task_id: str, source_component: str, initial_payload: Dict[str, Any]):
        """
        Initialize a TraceCollector for a specific run, task, and source component.
        
        Stores the provided `run_id`, `task_id`, and `source_component` on the instance and loads the associated run context from RunRegistry into `self.context` (may be `None` if the run is not registered). The `initial_payload` parameter is accepted for API compatibility but is not retained or used by the instance.
        
        Parameters:
            run_id (str): Identifier of the run whose context should be associated with this collector.
            task_id (str): Identifier of the task that generated events recorded by this collector.
            source_component (str): Name of the component producing events.
            initial_payload (Dict[str, Any]): Initial payload supplied at construction; accepted but ignored.
        """
        self.run_id, self.task_id, self.source_component = run_id, task_id, source_component
        self.context = RunRegistry.get_run(run_id)

    def record_event(self, event_type: str, description: str, dependencies: List[str] = None, payload: Dict[str, Any] = None):
        """
        Create a structured trace event record for the current task and source component.
        
        Parameters:
            event_type (str): Type or category of the event (for example, "start", "progress", "error").
            description (str): Human-readable description of the event.
            dependencies (List[str], optional): List of event IDs this event depends on; defaults to an empty list.
            payload (Dict[str, Any], optional): Arbitrary event-specific data; defaults to an empty dict.
        
        Returns:
            dict: A trace event dictionary containing the following keys:
                - event_id (str): Unique event identifier.
                - timestamp (str): UTC timestamp in "YYYY-MM-DDTHH:MM:SSZ" format.
                - event_type (str)
                - source_component (str)
                - description (str)
                - dependencies (List[str])
                - metadata (dict): Includes at least `task_id`.
                - payload (dict)
                - child_events (List)
        """
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
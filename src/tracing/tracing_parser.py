import json
from typing import List, Dict, Any

class TraceParser:
    def __init__(self, tracing_context: Dict[str, Any]):
        """
        Initialize the TraceParser with a tracing context and prepare internal containers used to build a Mermaid graph.
        
        Parameters:
            tracing_context (Dict[str, Any]): A dictionary representing the tracing context; expected to contain an "events" list of event dictionaries used to generate nodes and connections.
        
        Attributes:
            context (Dict[str, Any]): The provided tracing context.
            mermaid_nodes (List[str]): Accumulated Mermaid node definition strings.
            mermaid_connections (List[str]): Accumulated Mermaid connection/edge definition strings.
            event_nodes (Dict[str, str]): Mapping from event_id to its Mermaid node identifier/definition.
        """
        self.context = tracing_context
        self.mermaid_nodes, self.mermaid_connections, self.event_nodes = [], [], {}

    def _get_node_label(self, event: Dict[str, Any]) -> str:
        """
        Builds a Mermaid node label for an event.
        
        Parameters:
            event (Dict[str, Any]): Event dictionary; must contain the keys
                `source_component` and `event_type`.
        
        Returns:
            label (str): Mermaid node label in the format "(<source_component>) | <event_type>".
        """
        return f'({event["source_component"]}) | {event["event_type"]}'

    def _define_nodes(self, event: Dict[str, Any]):
        """
        Add Mermaid node definitions for `event` and all nested child events to the parser's internal collections.
        
        This method creates a Mermaid node ID of the form `N_{event_id}`, constructs the node definition string (using the event's label), stores it in `self.event_nodes` keyed by `event_id`, and appends the definition to `self.mermaid_nodes`. It then recursively processes any events found in `event.get("child_events", [])`.
        
        Parameters:
            event (dict): Event dictionary expected to contain:
                - 'event_id' (hashable): Unique identifier for the event.
                - 'child_events' (list): Optional list of nested event dicts.
                - fields used for the node label (e.g., 'source_component', 'event_type').
        """
        eid = event['event_id']
        nid = f"N_{eid}"
        self.event_nodes[eid] = f'{nid}["{self._get_node_label(event)}"]'
        self.mermaid_nodes.append(self.event_nodes[eid])
        for child in event.get("child_events", []):
            self._define_nodes(child)

    def _draw_connections(self, event: Dict[str, Any]):
        """
        Add Mermaid edge definitions for an event's dependencies and child-event relationships to the parser's connection list.
        
        This updates the instance's connection definitions by:
        - Adding "Requires" edges from each existing dependency node to this event's node.
        - Linking the parent node to the first child and creating sequential edges between consecutive children.
        - Recursing into each child event to add their connections.
        
        Parameters:
            event (Dict[str, Any]): Event dictionary containing at least `event_id`. May include
                `dependencies` (list of event IDs) and `child_events` (list of child event dicts).
        """
        nid = f"N_{event['event_id']}"
        for dep_id in event.get('dependencies', []):
            if dep_id in self.event_nodes:
                self.mermaid_connections.append(f"N_{dep_id} --> |Requires| {nid}")
        
        children = event.get("child_events", [])
        if children:
            self.mermaid_connections.append(f"{nid} --> N_{children[0]['event_id']}")
            for i in range(len(children)):
                if i > 0:
                    self.mermaid_connections.append(f"N_{children[i-1]['event_id']} --> N_{children[i]['event_id']}")
                self._draw_connections(children[i])

    def to_mermaid(self) -> str:
        """
        Convert the tracing context into a Mermaid "graph TD" diagram string.
        
        Builds node definitions and connection edges from the events in the stored tracing context (including nested child events and declared dependencies) and returns a single Mermaid graph text.
        
        Returns:
            mermaid (str): Mermaid graph starting with "graph TD;" followed by newline-separated node and edge definitions.
        """
        for event in self.context.get("events", []): self._define_nodes(event)
        for event in self.context.get("events", []): self._draw_connections(event)
        return "graph TD;\n" + "\n".join(self.mermaid_nodes + self.mermaid_connections)
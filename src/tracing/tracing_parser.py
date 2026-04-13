import json
from typing import List, Dict, Any

class TraceParser:
    def __init__(self, tracing_context: Dict[str, Any]):
        self.context = tracing_context
        self.mermaid_nodes, self.mermaid_connections, self.event_nodes = [], [], {}

    def _get_node_label(self, event: Dict[str, Any]) -> str:
        return f'({event["source_component"]}) | {event["event_type"]}'

    def _define_nodes(self, event: Dict[str, Any]):
        eid = event['event_id']
        nid = f"N_{eid}"
        self.event_nodes[eid] = f'{nid}["{self._get_node_label(event)}"]'
        self.mermaid_nodes.append(self.event_nodes[eid])
        for child in event.get("child_events", []):
            self._define_nodes(child)

    def _draw_connections(self, event: Dict[str, Any]):
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
        for event in self.context.get("events", []): self._define_nodes(event)
        for event in self.context.get("events", []): self._draw_connections(event)
        return "graph TD;\n" + "\n".join(self.mermaid_nodes + self.mermaid_connections)
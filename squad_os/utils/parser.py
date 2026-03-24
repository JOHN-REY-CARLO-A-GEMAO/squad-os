import json
import re
from typing import Any, Dict, List, Optional

def extract_tool_calls_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Attempts to extract tool/function call intents from unstructured text.
    Looks for XML tags <call:tool_name>{json_args}</call:tool_name>, JSON blocks,
    or patterns like 'Action: name' and 'Action Input: {...}'
    """
    tool_calls = []

    # 0. Look for XML tags <call:tool_name>arguments</call:tool_name>
    xml_calls = re.findall(r"<call:(\w+)>(.*?)</call:\1>", text, re.DOTALL)
    for tool_name, arguments in xml_calls:
        try:
            # Try to parse arguments as JSON, if it fails, treat it as a string input
            try:
                args_dict = json.loads(arguments.strip())
            except json.JSONDecodeError:
                args_dict = {"input": arguments.strip()}

            tool_calls.append({
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(args_dict)
                },
                "type": "function",
                "id": f"call_xml_{len(tool_calls)}"
            })
        except Exception:
            continue

    if tool_calls:
        return tool_calls

    # 1. Look for code blocks with JSON
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    for block in json_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and "name" in data and "arguments" in data:
                tool_calls.append({
                    "function": {
                        "name": data["name"],
                        "arguments": json.dumps(data["arguments"])
                    },
                    "type": "function",
                    "id": f"call_{len(tool_calls)}"
                })
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "name" in item:
                         tool_calls.append({
                            "function": {
                                "name": item["name"],
                                "arguments": json.dumps(item.get("arguments", {}))
                            },
                            "type": "function",
                            "id": f"call_{len(tool_calls)}"
                        })
        except json.JSONDecodeError:
            continue

    if tool_calls:
        return tool_calls

    # 2. Look for "Action: <name>" and "Action Input: <json/text>"
    action_match = re.search(r"Action:\s*(\w+)", text)
    if action_match:
        tool_name = action_match.group(1)
        action_input_match = re.search(r"Action Input:\s*(.*)", text, re.DOTALL)
        if action_input_match:
            action_input = action_input_match.group(1).strip()
            try:
                # Ensure it's valid JSON
                args = json.loads(action_input)
                tool_calls.append({
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args)
                    },
                    "type": "function",
                    "id": f"call_{len(tool_calls)}"
                })
            except json.JSONDecodeError:
                # If it's not JSON, maybe it's just a single argument?
                tool_calls.append({
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps({"input": action_input})
                    },
                    "type": "function",
                    "id": f"call_{len(tool_calls)}"
                })

    return tool_calls

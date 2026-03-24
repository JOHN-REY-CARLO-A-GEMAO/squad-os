import asyncio
import os
import json
from squad_os.utils.parser import extract_tool_calls_from_text

def test_parser_json_block():
    text = """
Here is the tool call:
```json
{
  "name": "web_scraper",
  "arguments": {"url": "https://example.com"}
}
```
"""
    calls = extract_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "web_scraper"
    assert json.loads(calls[0]["function"]["arguments"]) == {"url": "https://example.com"}
    print("test_parser_json_block passed")

def test_parser_action_pattern():
    text = """
I need to search for something.
Action: search
Action Input: {"query": "ollama local ai"}
"""
    calls = extract_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "search"
    assert json.loads(calls[0]["function"]["arguments"]) == {"query": "ollama local ai"}
    print("test_parser_action_pattern passed")

def test_parser_action_pattern_text_input():
    text = """
Action: search
Action Input: ollama local ai
"""
    calls = extract_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "search"
    assert json.loads(calls[0]["function"]["arguments"]) == {"input": "ollama local ai"}
    print("test_parser_action_pattern_text_input passed")

if __name__ == "__main__":
    test_parser_json_block()
    test_parser_action_pattern()
    test_parser_action_pattern_text_input()

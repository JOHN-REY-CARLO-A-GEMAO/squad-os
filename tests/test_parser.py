import json
import unittest
from squad_os.utils.parser import extract_tool_calls_from_text

class TestParser(unittest.TestCase):
    def test_extract_xml_tool_call(self):
        text = """
        <thought>I need to search for the recipe.</thought>
        <call:web_search>{"query": "chocolate cake recipe"}</call:web_search>
        """
        calls = extract_tool_calls_from_text(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "web_search")
        self.assertEqual(json.loads(calls[0]["function"]["arguments"]), {"query": "chocolate cake recipe"})

    def test_extract_xml_tool_call_plain_text(self):
        text = "<call:web_search>chocolate cake recipe</call:web_search>"
        calls = extract_tool_calls_from_text(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "web_search")
        self.assertEqual(json.loads(calls[0]["function"]["arguments"]), {"input": "chocolate cake recipe"})

    def test_multiple_xml_calls(self):
        text = """
        <call:write_file>{"filepath": "test.txt", "content": "hi"}</call:write_file>
        <call:web_scrape>{"url": "https://example.com"}</call:web_scrape>
        """
        calls = extract_tool_calls_from_text(text)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["function"]["name"], "write_file")
        self.assertEqual(calls[1]["function"]["name"], "web_scrape")

if __name__ == "__main__":
    unittest.main()

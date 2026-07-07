import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.lc_tools import ALL_TOOLS

class TestAgentsHealth(unittest.TestCase):
    def test_all_tools_loaded(self):
        """Test that all 11 tools are successfully wrapped by LangChain."""
        tool_names = [t.name for t in ALL_TOOLS]
        self.assertEqual(len(tool_names), 11, f"Expected 11 tools, but got {len(tool_names)}")
        
        expected_tools = [
            "web_scraper", "search_agent", "sentiment_analysis", "ner_agent", 
            "topic_modeling", "page_classifier", "link_extractor", 
            "deep_research_agent", "data_exporter_agent", "meta_agent", 
            "code_executor_agent"
        ]
        
        for name in expected_tools:
            self.assertIn(name, tool_names)

    def test_tool_schemas(self):
        """Test that tool schemas are successfully parsed."""
        for tool in ALL_TOOLS:
            schema = tool.args_schema.model_json_schema()
            self.assertIn("properties", schema)
            # Ensure the function docstring became the tool description
            self.assertTrue(bool(tool.description))

if __name__ == '__main__':
    unittest.main()

"""
Dynamic Agent Testing Utility
-----------------------------
Runs interactive, dynamic tests on all swarm agents (both legacy and new).
Verifies safety rails, API logic, and error handling.
"""

import os
import sys

# Ensure the root project directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Core 10 Advanced Agents
from agents.sql_db_agent import sql_db_agent
from agents.api_discovery_agent import api_discovery_agent
from agents.email_agent import email_agent
from agents.calendar_agent import calendar_agent
from agents.social_media_agent import social_media_agent
from agents.pdf_ocr_agent import pdf_ocr_agent
from agents.audio_transcription_agent import audio_transcription_agent
from agents.github_agent import github_agent
from agents.file_system_agent import file_system_agent
from agents.self_reflection_agent import self_reflection_agent

# Legacy & System Agents
from agents.link_extractor import link_extractor
from agents.memory_agent import memory_agent
from agents.page_classifier import page_classifier
from agents.vision_agent import vision_agent
from agents.deep_research_agent import deep_research_agent
from agents.search_agent import search_agent
from agents.code_executor_agent import code_executor_agent
from agents.external_service_agent import external_service_agent
from agents.ner_agent import ner_agent
from agents.sentiment_analysis import sentiment_analysis
from agents.data_exporter_agent import data_exporter_agent
from agents.qa_agent import qa_agent
from agents.auth_agent import auth_agent
from agents.topic_modeling import topic_modeling
from agents.meta_agent import meta_agent
from agents.web_scraper import web_scraper
# Not importing browser_agent as get_browser requires playwright headless state management which might block

def run_test(name, func, kwargs, expected_fail=False):
    """Runs a single test case with error capturing."""
    print(f"\n[Running Test] {name} ...")
    print(f"Inputs: {kwargs}")
    try:
        result = func(**kwargs)
        # Handle dict or string return values appropriately
        if isinstance(result, dict) and "error" in result:
            if expected_fail:
                print(f"✅ PASSED (Expected Error Triggered): {result['error']}")
                return True
            else:
                print(f"❌ FAILED (Unexpected Error): {result['error']}")
                return False
        else:
            if expected_fail:
                print(f"❌ FAILED (Expected to fail, but succeeded!): {result}")
                return False
            else:
                print(f"✅ PASSED: Success")
                # Truncate output for readability
                str_res = str(result)
                print(f"Output: {str_res[:200] + '...' if len(str_res) > 200 else str_res}")
                return True
    except Exception as e:
        if expected_fail:
            print(f"✅ PASSED (Expected Crash Triggered): {str(e)}")
            return True
        print(f"🚨 CRASHED: {str(e)}")
        return False

# Define all agents and their dynamic test suites
AGENT_TESTS = [
    {
        "name": "sql_db_agent",
        "description": "System of Record: Database querying and safety rails",
        "tests": [
            ("Schema Fetch", sql_db_agent, {"action": "get_schema"}),
            ("Safety Check (DROP)", sql_db_agent, {"action": "execute_query", "query_or_table": "DROP TABLE users;"}, True),
        ]
    },
    {
        "name": "api_discovery_agent",
        "description": "System of Record: Dynamic REST API fetching",
        "tests": [
            ("Public API Fetch", api_discovery_agent, {"action": "send_request", "url": "https://dummyjson.com/test", "method": "GET"}),
        ]
    },
    {
        "name": "email_agent",
        "description": "The Communicator: IMAP/SMTP integration",
        "tests": [
            ("Missing Credentials Check", email_agent, {"action": "read_inbox"}, True) # Will fail gracefully without .env
        ]
    },
    {
        "name": "calendar_agent",
        "description": "The Communicator: Local JSON scheduling mock",
        "tests": [
            ("Check Availability", calendar_agent, {"action": "check_availability", "date": "2099-01-01"}),
        ]
    },
    {
        "name": "social_media_agent",
        "description": "The Communicator: Mentions and Posting",
        "tests": [
            ("Read Mentions", social_media_agent, {"action": "read_mentions", "platform": "twitter"}),
        ]
    },
    {
        "name": "pdf_ocr_agent",
        "description": "The Archivist: PDF parsing and searching",
        "tests": [
            ("Missing File Error", pdf_ocr_agent, {"action": "extract_text", "file_path": "/fake/path/missing.pdf"}, True)
        ]
    },
    {
        "name": "audio_transcription_agent",
        "description": "The Archivist: Whisper Audio processing",
        "tests": [
            ("Missing Audio File", audio_transcription_agent, {"action": "transcribe_audio", "file_path": "/fake/audio.mp3"}, True)
        ]
    },
    {
        "name": "github_agent",
        "description": "The Local Admin: Git CLI Sandbox",
        "tests": [
            ("Clone Repo", github_agent, {"action": "clone_repo", "repo_url": "https://github.com/octocat/Hello-World.git"}),
        ]
    },
    {
        "name": "file_system_agent",
        "description": "The Local Admin: Path Jail enforcement",
        "tests": [
            ("Search Safe Files", file_system_agent, {"action": "search_files", "pattern_or_source": "*.json"}),
            ("Path Traversal Attack Block", file_system_agent, {"action": "move_file", "pattern_or_source": "test.txt", "destination": "../../../../../etc/passwd"}, True)
        ]
    },
    {
        "name": "self_reflection_agent",
        "description": "The Optimizer: Log analysis and system patching",
        "tests": [
            ("Analyze Missing Logs", self_reflection_agent, {"action": "analyze_logs", "agent_name": "dummy_agent"})
        ]
    },
    {
        "name": "link_extractor",
        "description": "Legacy: Extract links from HTML",
        "tests": [
            ("Extract Links", link_extractor, {"url": "https://example.com"}),
        ]
    },
    {
        "name": "memory_agent",
        "description": "Vector DB for long term memory",
        "tests": [
            ("Save Memory", memory_agent, {"action": "save", "query_or_data": "User likes dark mode", "tags": "ui"}),
            ("Retrieve Memory", memory_agent, {"action": "retrieve", "query_or_data": "What does user like?", "tags": "ui"}),
        ]
    },
    {
        "name": "page_classifier",
        "description": "Legacy: Classify webpage text",
        "tests": [
            ("Classify Text", page_classifier, {"text": "This is a blog post about AI."}),
        ]
    },
    {
        "name": "vision_agent",
        "description": "Multimodal: Vision capabilities",
        "tests": [
            ("Missing Image Test", vision_agent, {"image_path": "/fake/image.png", "prompt": "Describe this"}, True),
        ]
    },
    {
        "name": "search_agent",
        "description": "Web Search (DuckDuckGo)",
        "tests": [
            ("Search DDG", search_agent, {"query": "Latest AI news", "backend": "duckduckgo"}),
        ]
    },
    {
        "name": "code_executor_agent",
        "description": "Local Code Execution",
        "tests": [
            ("Execute Python", code_executor_agent, {"code": "print('hello from sandbox')"})
        ]
    },
    {
        "name": "external_service_agent",
        "description": "Apify / BrightData API integrations",
        "tests": [
            ("Missing Platform Error", external_service_agent, {"action": "run_actor", "query": "scrape", "platform": "invalid_platform"}, True)
        ]
    },
    {
        "name": "ner_agent",
        "description": "Legacy: Named Entity Recognition",
        "tests": [
            ("NER Test", ner_agent, {"text": "Apple CEO Tim Cook visited London."}),
        ]
    },
    {
        "name": "sentiment_analysis",
        "description": "Legacy: Sentiment Analysis",
        "tests": [
            ("Sentiment Test", sentiment_analysis, {"text": "I absolutely love this new framework!"}),
        ]
    },
    {
        "name": "data_exporter_agent",
        "description": "Exports JSON to CSV/JSON files",
        "tests": [
            ("Export JSON", data_exporter_agent, {"data_json": '[{"name": "test"}]', "filename_prefix": "test_export", "format": "json"}),
        ]
    },
    {
        "name": "qa_agent",
        "description": "Quality Assurance & Evaluation",
        "tests": [
            ("QA Validate", qa_agent, {"original_requirement": "Extract email address", "generated_output": "The email is test@example.com"}),
        ]
    },
    {
        "name": "auth_agent",
        "description": "Interactive Authentication",
        "tests": [
            ("Auth Mock Error", auth_agent, {"platform": "invalid", "login_url": "https://example.com/login"}, True),
        ]
    },
    {
        "name": "topic_modeling",
        "description": "Legacy: Topic Modeling",
        "tests": [
            ("Topic Test", topic_modeling, {"text": "The stock market crashed due to high interest rates."}),
        ]
    },
    {
        "name": "meta_agent",
        "description": "Legacy: Orchestrator Python code generation",
        "tests": [
            ("Meta Code Gen", meta_agent, {"tool_name": "test_tool", "python_code": "def func(): pass"}),
        ]
    },
    {
        "name": "web_scraper",
        "description": "Legacy: Static BS4 Web Scraper",
        "tests": [
            ("Static Scrape", web_scraper, {"url": "https://example.com"}),
        ]
    }
]

def print_menu():
    os.system('clear' if os.name == 'posix' else 'cls')
    print("==========================================================")
    print("      Autonomous Swarm: Detailed Agent Testing Suite      ")
    print("==========================================================")
    print("\nPre-requisites for full functionality:")
    print("- Ensure PyPDF2, openai-whisper, and ffmpeg are installed for Phase 3.")
    print("- Ensure EMAIL_USER and EMAIL_PASS are set in .env for Email Agent.")
    print("- Ensure Git is installed for GitHub Agent.\n")
    
    for idx, agent in enumerate(AGENT_TESTS):
        print(f"  [{idx}] {agent['name'].ljust(25)} | {agent['description']}")
        
    print("==========================================================")
    print("Options:")
    print("  Enter 'a' to test ALL agents.")
    print("  Enter a space-separated list of indices (e.g. '0 3 4') to test specific agents.")
    print("  Enter 'e' to exit.")
    print("==========================================================")

def main():
    while True:
        print_menu()
        
        # Check for non-interactive test mode
        auto_test = os.environ.get("AUTO_TEST")
        if auto_test:
            choice = auto_test.strip().lower()
            print(f"\n[AUTO_TEST Mode] Selected: {choice}")
            # Ensure it only runs once and exits
            if choice == "a":
                os.environ["AUTO_TEST"] = "e"
        else:
            choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'e':
            print("Exiting test suite. Goodbye!")
            break
            
        agents_to_test = []
        if choice == 'a':
            agents_to_test = AGENT_TESTS
        else:
            try:
                indices = [int(x) for x in choice.split()]
                for idx in indices:
                    if 0 <= idx < len(AGENT_TESTS):
                        agents_to_test.append(AGENT_TESTS[idx])
                    else:
                        print(f"Warning: Index {idx} is out of bounds.")
            except ValueError:
                print("Invalid input. Please enter 'a', 'e', or a list of numbers.")
                input("Press Enter to continue...")
                continue
                
        if not agents_to_test:
            print("No agents selected for testing.")
            input("Press Enter to continue...")
            continue
            
        print("\n==========================================================")
        print(f"Starting test run for {len(agents_to_test)} agent(s)...")
        print("==========================================================\n")
        
        total_tests = 0
        passed_tests = 0
        
        for agent in agents_to_test:
            print(f"==== Testing Agent: {agent['name']} ====")
            for test_name, func, kwargs, *rest in agent['tests']:
                expected_fail = rest[0] if rest else False
                total_tests += 1
                success = run_test(test_name, func, kwargs, expected_fail)
                if success:
                    passed_tests += 1
            print("-" * 50)
            
        print("\n==========================================================")
        print("                   FINAL TEST REPORT                      ")
        print("==========================================================")
        print(f"Total Agents Tested : {len(agents_to_test)}")
        print(f"Total Test Cases    : {total_tests}")
        print(f"Passed              : {passed_tests}")
        print(f"Failed              : {total_tests - passed_tests}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! The swarm components are rock solid.")
        else:
            print("\n⚠️ SOME TESTS FAILED! Check the output above for bugs/crashes.")
            
        print("==========================================================\n")
        
        if os.environ.get("AUTO_TEST"):
            post_choice = "e"
        else:
            post_choice = input("Do you want to test more agents? (y/n/e): ").strip().lower()
            
        if post_choice in ['n', 'e']:
            print("Exiting test suite. Goodbye!")
            break

if __name__ == "__main__":
    main()

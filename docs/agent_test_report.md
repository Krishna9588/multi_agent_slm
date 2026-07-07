[agents] WARNING: could not import browser_agent.py: No module named 'playwright'
TERM environment variable not set.
==========================================================
      Autonomous Swarm: Detailed Agent Testing Suite      
==========================================================

Pre-requisites for full functionality:
- Ensure PyPDF2, openai-whisper, and ffmpeg are installed for Phase 3.
- Ensure EMAIL_USER and EMAIL_PASS are set in .env for Email Agent.
- Ensure Git is installed for GitHub Agent.

  [0] sql_db_agent              | System of Record: Database querying and safety rails
  [1] api_discovery_agent       | System of Record: Dynamic REST API fetching
  [2] email_agent               | The Communicator: IMAP/SMTP integration
  [3] calendar_agent            | The Communicator: Local JSON scheduling mock
  [4] social_media_agent        | The Communicator: Mentions and Posting
  [5] pdf_ocr_agent             | The Archivist: PDF parsing and searching
  [6] audio_transcription_agent | The Archivist: Whisper Audio processing
  [7] github_agent              | The Local Admin: Git CLI Sandbox
  [8] file_system_agent         | The Local Admin: Path Jail enforcement
  [9] self_reflection_agent     | The Optimizer: Log analysis and system patching
  [10] link_extractor            | Legacy: Extract links from HTML
  [11] memory_agent              | Vector DB for long term memory
  [12] page_classifier           | Legacy: Classify webpage text
  [13] vision_agent              | Multimodal: Vision capabilities
  [14] search_agent              | Web Search (DuckDuckGo)
  [15] code_executor_agent       | Local Code Execution
  [16] external_service_agent    | Apify / BrightData API integrations
  [17] ner_agent                 | Legacy: Named Entity Recognition
  [18] sentiment_analysis        | Legacy: Sentiment Analysis
  [19] data_exporter_agent       | Exports JSON to CSV/JSON files
  [20] qa_agent                  | Quality Assurance & Evaluation
  [21] auth_agent                | Interactive Authentication
  [22] topic_modeling            | Legacy: Topic Modeling
  [23] meta_agent                | Legacy: Orchestrator Python code generation
  [24] web_scraper               | Legacy: Static BS4 Web Scraper
==========================================================
Options:
  Enter 'a' to test ALL agents.
  Enter a space-separated list of indices (e.g. '0 3 4') to test specific agents.
  Enter 'e' to exit.
==========================================================

[AUTO_TEST Mode] Selected: a

==========================================================
Starting test run for 25 agent(s)...
==========================================================

==== Testing Agent: sql_db_agent ====

[Running Test] Schema Fetch ...
Inputs: {'action': 'get_schema'}
✅ PASSED: Success
Output: {'success': True, 'schema': 'Database is currently empty. No tables found.'}

[Running Test] Safety Check (DROP) ...
Inputs: {'action': 'execute_query', 'query_or_table': 'DROP TABLE users;'}
✅ PASSED (Expected Error Triggered): SECURITY BLOCK: Destructive commands (DROP, TRUNCATE, ALTER) are disabled for safety.
--------------------------------------------------
==== Testing Agent: api_discovery_agent ====

[Running Test] Public API Fetch ...
Inputs: {'action': 'send_request', 'url': 'https://dummyjson.com/test', 'method': 'GET'}
✅ PASSED: Success
Output: {'success': True, 'status_code': 200, 'response': {'status': 'ok', 'method': 'GET'}}
--------------------------------------------------
==== Testing Agent: email_agent ====

[Running Test] Missing Credentials Check ...
Inputs: {'action': 'read_inbox'}
✅ PASSED (Expected Error Triggered): Missing EMAIL_USER or EMAIL_PASS in .env. Cannot access email.
--------------------------------------------------
==== Testing Agent: calendar_agent ====

[Running Test] Check Availability ...
Inputs: {'action': 'check_availability', 'date': '2099-01-01'}
✅ PASSED: Success
Output: {'success': True, 'message': 'Your calendar is completely open on 2099-01-01.'}
--------------------------------------------------
==== Testing Agent: social_media_agent ====

[Running Test] Read Mentions ...
Inputs: {'action': 'read_mentions', 'platform': 'twitter'}
✅ PASSED: Success
Output: {'success': True, 'platform': 'twitter', 'mentions': [{'user': '@tech_fan', 'text': 'This new AI swarm is incredible!', 'sentiment': 'positive'}, {'user': '@angry_dev', 'text': "Why isn't the auth age...
--------------------------------------------------
==== Testing Agent: pdf_ocr_agent ====

[Running Test] Missing File Error ...
Inputs: {'action': 'extract_text', 'file_path': '/fake/path/missing.pdf'}
✅ PASSED (Expected Error Triggered): File not found at /fake/path/missing.pdf
--------------------------------------------------
==== Testing Agent: audio_transcription_agent ====

[Running Test] Missing Audio File ...
Inputs: {'action': 'transcribe_audio', 'file_path': '/fake/audio.mp3'}
✅ PASSED (Expected Error Triggered): Audio file not found at /fake/audio.mp3
--------------------------------------------------
==== Testing Agent: github_agent ====

[Running Test] Clone Repo ...
Inputs: {'action': 'clone_repo', 'repo_url': 'https://github.com/octocat/Hello-World.git'}
✅ PASSED: Success
Output: {'success': True, 'message': "Repository 'Hello-World' is already cloned in the sandbox."}
--------------------------------------------------
==== Testing Agent: file_system_agent ====

[Running Test] Search Safe Files ...
Inputs: {'action': 'search_files', 'pattern_or_source': '*.json'}
✅ PASSED: Success
Output: {'success': True, 'message': "No files found matching '*.json'."}

[Running Test] Path Traversal Attack Block ...
Inputs: {'action': 'move_file', 'pattern_or_source': 'test.txt', 'destination': '../../../../../etc/passwd'}
✅ PASSED (Expected Error Triggered): SECURITY BLOCK: Attempted path traversal outside of sandbox (../../../../../etc/passwd)
--------------------------------------------------
==== Testing Agent: self_reflection_agent ====

[Running Test] Analyze Missing Logs ...
Inputs: {'action': 'analyze_logs', 'agent_name': 'dummy_agent'}
✅ PASSED: Success
Output: {'success': True, 'agent': 'dummy_agent', 'analysis': 'Simulation: Analyzed dummy_agent. Found that it frequently hallucinates parameters when dealing with deeply nested JSON.'}
--------------------------------------------------
==== Testing Agent: link_extractor ====

[Running Test] Extract Links ...
Inputs: {'url': 'https://example.com'}
🚨 CRASHED: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)>
--------------------------------------------------
==== Testing Agent: memory_agent ====

[Running Test] Save Memory ...
Inputs: {'action': 'save', 'query_or_data': 'User likes dark mode', 'tags': 'ui'}
✅ PASSED: Success
Output: {'success': True, 'message': 'Successfully stored in long-term memory.'}

[Running Test] Retrieve Memory ...
Inputs: {'action': 'retrieve', 'query_or_data': 'What does user like?', 'tags': 'ui'}
✅ PASSED: Success
Output: {'success': True, 'results': "Match (Score 0): User likes dark mode\n---\nMatch (Score 0): Based on the search results, it appears that creating a multi-agent system in Python is a feasible task, with...
--------------------------------------------------
==== Testing Agent: page_classifier ====

[Running Test] Classify Text ...
Inputs: {'text': 'This is a blog post about AI.'}
✅ PASSED: Success
Output: {'page_type': 'blog', 'confidence': 'high', 'reasoning': 'The content explicitly describes itself as a blog post.'}
--------------------------------------------------
==== Testing Agent: vision_agent ====

[Running Test] Missing Image Test ...
Inputs: {'image_path': '/fake/image.png', 'prompt': 'Describe this'}
✅ PASSED (Expected Error Triggered): Image file not found at /fake/image.png
--------------------------------------------------
==== Testing Agent: search_agent ====

[Running Test] Search DDG ...
Inputs: {'query': 'Latest AI news', 'backend': 'duckduckgo'}
❌ FAILED (Unexpected Error): All search backends returned no results for: 'Latest AI news'
--------------------------------------------------
==== Testing Agent: code_executor_agent ====

[Running Test] Execute Python ...
Inputs: {'code': "print('hello from sandbox')"}
✅ PASSED: Success
Output: {'stdout': '', 'stderr': 'failed to connect to the docker API at unix:///Users/krishnabirla/.docker/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /Users/krishna...
--------------------------------------------------
==== Testing Agent: external_service_agent ====

[Running Test] Missing Platform Error ...
Inputs: {'action': 'run_actor', 'query': 'scrape', 'platform': 'invalid_platform'}
✅ PASSED (Expected Crash Triggered): external_service_agent() got an unexpected keyword argument 'action'
--------------------------------------------------
==== Testing Agent: ner_agent ====

[Running Test] NER Test ...
Inputs: {'text': 'Apple CEO Tim Cook visited London.'}
✅ PASSED: Success
Output: {'people': [{'name': 'Tim Cook', 'designation': 'CEO'}], 'organizations': [{'name': 'Apple', 'context': 'The company whose CEO is Tim Cook.'}], 'locations': [{'name': 'London', 'context': 'The city vi...
--------------------------------------------------
==== Testing Agent: sentiment_analysis ====

[Running Test] Sentiment Test ...
Inputs: {'text': 'I absolutely love this new framework!'}
✅ PASSED: Success
Output: {'overall_sentiment': 'positive', 'confidence': 'high', 'tone': ['enthusiastic', 'personal', 'informal'], 'intent': 'expressing strong personal satisfaction/praise', 'key_phrases': ['absolutely love t...
--------------------------------------------------
==== Testing Agent: data_exporter_agent ====

[Running Test] Export JSON ...
Inputs: {'data_json': '[{"name": "test"}]', 'filename_prefix': 'test_export', 'format': 'json'}
✅ PASSED: Success
Output: {'status': 'success', 'message': 'Successfully exported JSON file.', 'file_path': '/Users/krishnabirla/PycharmProjects/mulit_model_agent/archive/outputs/test_export_20260704_215940.json'}
--------------------------------------------------
==== Testing Agent: qa_agent ====

[Running Test] QA Validate ...
Inputs: {'original_requirement': 'Extract email address', 'generated_output': 'The email is test@example.com'}
❌ FAILED (Unexpected Error): QA Evaluation failed: Expecting value: line 1 column 1 (char 0)
--------------------------------------------------
==== Testing Agent: auth_agent ====

[Running Test] Auth Mock Error ...
Inputs: {'platform': 'invalid', 'login_url': 'https://example.com/login'}
✅ PASSED (Expected Error Triggered): Interactive authentication failed: 'NoneType' object is not callable
--------------------------------------------------
==== Testing Agent: topic_modeling ====

[Running Test] Topic Test ...
Inputs: {'text': 'The stock market crashed due to high interest rates.'}
✅ PASSED: Success
Output: {'primary_topic': 'Market Crash Causes', 'secondary_topics': ['Stock Market Performance', 'Interest Rate Impact', 'Economic Factors', 'Financial Markets'], 'keywords': ['stock market', 'crashed', 'hig...
--------------------------------------------------
==== Testing Agent: meta_agent ====

[Running Test] Meta Code Gen ...
Inputs: {'tool_name': 'test_tool', 'python_code': 'def func(): pass'}
✅ PASSED: Success
Output: {'success': True, 'message': 'Successfully created test_tool.py in the agents folder.', 'file_path': '/Users/krishnabirla/PycharmProjects/mulit_model_agent/agents/test_tool.py', 'instruction': "The or...
--------------------------------------------------
==== Testing Agent: web_scraper ====

[Running Test] Static Scrape ...
Inputs: {'url': 'https://example.com'}
🚨 CRASHED: No module named 'playwright'
--------------------------------------------------

==========================================================
                   FINAL TEST REPORT                      
==========================================================
Total Agents Tested : 25
Total Test Cases    : 28
Passed              : 24
Failed              : 4

⚠️ SOME TESTS FAILED! Check the output above for bugs/crashes.
==========================================================

Exiting test suite. Goodbye!

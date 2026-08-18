import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.data_structuring_agent import data_structuring_agent

def test_data_structuring_signature():
    """Verify data_structuring_agent accepts input without throwing unhandled exceptions."""
    sample_text = "Job Title: Senior Python Developer at Acme Corp. Location: Remote. Salary: $120,000."
    try:
        res = data_structuring_agent(sample_text, context="Job Posting")
        assert isinstance(res, dict)
    except Exception as e:
        # If Ollama is offline in CI/testing, ensure it catches gracefully
        assert "Ollama" in str(e) or "connect" in str(e) or "model" in str(e).lower()

if __name__ == "__main__":
    sample_text = "Job Title: Senior Python Developer at Acme Corp. Location: Remote. Salary: $120,000."
    print("Running Data Structuring Agent...")
    structured = data_structuring_agent(sample_text, context="Job Posting")
    print("Result:", json.dumps(structured, indent=2))

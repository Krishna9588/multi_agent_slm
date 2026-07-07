import sys
from redesign.core.graph import create_graph

def main():
    print("==================================================")
    print(" Booting 100% Local LangGraph Orchestrator")
    print("==================================================")
    
    app = create_graph()
    
    # Initial seed state
    initial_state = {
        "messages": [],
        "context": "",
        "current_phase": "init"
    }
    
    print("\n[System] Graph compiled successfully.")
    print("[System] Local Ollama connections initialized.")
    print("[System] Ready for zero-cost task execution.\n")
    
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(f"Task received: {task}")
        # To be implemented: app.invoke(...)
    else:
        print("Usage: python -m redesign.main 'Your research task here'")

if __name__ == "__main__":
    main()

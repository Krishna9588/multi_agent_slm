import sys
from redesign.core.graph import create_graph

def main():
    print("==================================================")
    print(" Booting 100% Local LangGraph Orchestrator")
    print("==================================================")
    
    app = create_graph()
    
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(f"Task received: {task}\n")
        
        initial_state = {
            "task_prompt": task,
            "messages": [],
            "raw_data": {},
            "structured_data": {},
            "report_path": "",
            "errors": []
        }
        
        # Stream the graph execution to see logs in real-time
        for output in app.stream(initial_state):
            for key, value in output.items():
                print(f"--- Finished node: {key} ---")
                
        print("\n==================================================")
        print(" Task Completed successfully.")
        print("==================================================")
    else:
        print("Usage: python -m redesign.main 'Your research task here'")

if __name__ == "__main__":
    main()

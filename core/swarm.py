import json
from typing import Callable, Any, Optional

class Agent:
    def __init__(self, name: str, instructions: str, functions: list[Callable] = None, model: str = "gemma4:e2b-mlx"):
        self.name = name
        self.instructions = instructions
        self.functions = functions or []
        self.model = model

class TransferToAgent:
    """Special return type from a function to signal the Swarm router to switch active agents."""
    def __init__(self, agent: Agent):
        self.agent = agent

def run_swarm(starting_agent: Agent, user_query: str, max_turns: int = 10) -> dict:
    """
    Runs a multi-agent swarm loop.
    1. Starts with `starting_agent`.
    2. Sends the query.
    3. If the agent calls a tool that returns a TransferToAgent, it switches the active agent.
    4. Loops until the active agent returns a final string or max_turns is hit.
    """
    from core.models import get_conversation_session
    
    print(f"\n🐝 [Swarm] Starting with agent: {starting_agent.name}")
    
    active_agent = starting_agent
    session = get_conversation_session(model=active_agent.model, system_prompt=active_agent.instructions)
    
    # Simple tool mapping
    def _build_tools_prompt(agent: Agent) -> str:
        if not agent.functions:
            return ""
        tool_desc = "You have the following tools available. To use a tool, output a JSON object: {\"tool\": \"name\", \"args\": {\"arg1\": \"val1\"}}.\n"
        for f in agent.functions:
            tool_desc += f"- {f.__name__}: {f.__doc__}\n"
        return tool_desc

    history = [f"User: {user_query}"]
    
    # Memory Tracking
    last_tool_call = None
    repeated_tool_count = 0
    
    for turn in range(max_turns):
        print(f"🐝 [Swarm] ({active_agent.name}) thinking...")
        
        # Inject tool prompt if tools exist
        tools_prompt = _build_tools_prompt(active_agent)
        prompt = "\n".join(history)
        if tools_prompt:
            prompt = tools_prompt + "\n\n" + prompt
            
        try:
            # We don't stream here to make parsing JSON tools easier, but we could.
            response = session.chat(prompt, format="json" if active_agent.functions else None)
        except Exception as e:
            return {"error": f"Agent {active_agent.name} failed: {e}"}

        # Check if the response is a tool call
        tool_called = False
        try:
            # Basic JSON parser for tool calls
            parsed = json.loads(response.strip().strip("```json").strip("```"))
            if "tool" in parsed:
                tool_called = True
                tool_name = parsed["tool"]
                tool_args = parsed.get("args", {})
                
                # --- MEMORY MODULE: Loop Detection ---
                current_call_signature = f"{tool_name}_{json.dumps(tool_args, sort_keys=True)}"
                if current_call_signature == last_tool_call:
                    repeated_tool_count += 1
                else:
                    last_tool_call = current_call_signature
                    repeated_tool_count = 0
                    
                if repeated_tool_count >= 2:
                    print(f"🐝 [Swarm] ⚠️ Memory Warning Injected (Repeated action detected)")
                    history.append(f"System: [SYSTEM MEMORY WARNING] You have tried calling {tool_name} with these arguments {repeated_tool_count + 1} times and it is failing or not progressing. DO NOT repeat this action. Try a different element_id, or call done_browsing.")
                    continue # Skip execution and force model to read the warning
                # -------------------------------------
                
                print(f"🐝 [Swarm] ({active_agent.name}) called tool: {tool_name}")
                
                # Execute tool
                tool_fn = next((f for f in active_agent.functions if f.__name__ == tool_name), None)
                if tool_fn:
                    try:
                        tool_result = tool_fn(**tool_args)
                        if isinstance(tool_result, TransferToAgent):
                            print(f"🐝 [Swarm] Transferring control to: {tool_result.agent.name}")
                            active_agent = tool_result.agent
                            # Re-initialize session for new agent, but keep history
                            session = get_conversation_session(model=active_agent.model, system_prompt=active_agent.instructions)
                            history.append(f"System: Transferred to {active_agent.name}")
                        else:
                            history.append(f"System Tool Result ({tool_name}): {tool_result}")
                    except Exception as e:
                        history.append(f"System Tool Error ({tool_name}): {e}")
                else:
                    history.append(f"System Error: Tool {tool_name} not found.")
        except json.JSONDecodeError:
            pass # Not a tool call, just a regular text response

        if not tool_called:
            print(f"🐝 [Swarm] ({active_agent.name}) final response: {response}")
            return {"status": "success", "response": response, "history": history}

    return {"status": "error", "error": "Max turns reached without final response."}

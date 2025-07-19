from typing import Dict, Callable
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from agents import build_worker_agent, SUPERVISOR_PROMPT
from memory import ConversationState
from langchain.schema import AIMessage

def build_graph(worker_factories: Dict[str, Callable], supervisor_llm: ChatOpenAI):
    g = StateGraph(dict)
    
    # Add worker nodes dynamically
    for name, factory in worker_factories.items():
        def _make_run(agent_name, agent_factory):
            def run_worker(state: dict):
                print(f"🔧 Executing {agent_name}...")
                print(f"🔧 Calling factory for {agent_name}...")
                agent_exec = agent_factory()
                objective = state['user_objective']
                convo = state['conversation'].render()
                
                # Debug: Check what tools are available
                tools_available = agent_exec.tools if hasattr(agent_exec, 'tools') else []
                print(f"🔧 {agent_name} has {len(tools_available)} tools: {[t.name for t in tools_available]}")
                
                # Add context about what other agents have done
                full_input = f"Objective: {objective}\n\nConversation so far:\n{convo}\n\nYour task: Use your available tools to analyze the data and provide insights. You MUST use your tools to complete this task."
                
                print(f"📝 Input to {agent_name}: {full_input[:200]}...")
                res = agent_exec.invoke({"input": full_input})
                output = res['output'] if 'output' in res else str(res)
                print(f"📤 {agent_name} output: {output[:200]}...")
                state['conversation'].append(agent_name, output)
                return state
            return run_worker
        g.add_node(name, _make_run(name, factory))

    # Supervisor node
    def supervisor_node(state: dict):
        convo = state['conversation'].render()
        msg = SUPERVISOR_PROMPT.format(
            conversation=convo,
            user_objective=state['user_objective'],
            agent_names=", ".join(worker_factories.keys())
        )
        decision = supervisor_llm.invoke(msg)
        text = decision.content.strip()
        state['conversation'].append('SUPERVISOR', text)
        
        # Parse the decision - look for agent names in the response
        for agent_name in worker_factories.keys():
            if agent_name in text.upper():
                state['next'] = agent_name
                return state
        
        # If no agent found, check if it says FINISH
        if 'FINISH' in text.upper():
            state['next'] = 'FINISH'
        else:
            # Default to first agent if unclear
            state['next'] = list(worker_factories.keys())[0]
        
        return state

    g.add_node('supervisor', supervisor_node)

    # Edges: supervisor -> worker(s), worker -> supervisor, supervisor -> END
    for name in worker_factories:
        g.add_edge(name, 'supervisor')
    
    # Add conditional edges from supervisor to workers and END
    g.add_conditional_edges('supervisor',
        lambda s: s['next'],
        {name: name for name in worker_factories} | {'FINISH': END}
    )

    g.set_entry_point('supervisor')
    return g.compile()
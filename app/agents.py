from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate

# Each worker agent has a focused prompt & tool subset.
# Inspired by the separation-of-concerns and specialized agent design. ([blog.langchain.com](https://blog.langchain.com/langgraph-multi-agent-workflows/))

WORKER_PROMPT_TEMPLATE = """You are the {role} agent. 

Instructions: {instructions}

IMPORTANT: You MUST use the available tools to complete your task. Do not respond with 'NO_ACTION' unless you absolutely cannot proceed.

Available tools: {tools}

Use the tools to gather information and provide a detailed response."""

SUPERVISOR_SYSTEM = """You are a supervisor that coordinates specialized agents to complete complex tasks. You must delegate work to agents and only return FINISH when the task is actually complete.

Available agents: {agent_names}.

Your job is to:
1. Analyze the user's objective
2. Delegate appropriate work to agents
3. Only return FINISH when you have sufficient information to provide a complete answer

Return one of: {agent_names}, or FINISH when the task is fully complete.

IMPORTANT: 
- Always start by delegating work to agents
- Only finish when you have comprehensive results from actual tool usage
- If an agent hasn't used their tools yet, keep delegating to them
- Wait for SQL_AGENT to query the database and WEB_AGENT to search the web before finishing"""  # Supervisor routing concept. ([blog.langchain.com](https://blog.langchain.com/langgraph-multi-agent-workflows/))

SUPERVISOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SUPERVISOR_SYSTEM),
    ("human", "Conversation so far:\n{conversation}\nUser Objective: {user_objective}\n\nWorkflow: Start with SQL_AGENT to analyze data, then WEB_AGENT for market research, then SYNTHESIZER for final recommendations.\n\nWho should act next?")
])

def build_worker_agent(role: str, instructions: str, llm: ChatOpenAI, tools: list):
    print(f"🔧 Building {role} agent with {len(tools)} tools: {[t.name for t in tools]}")
    
    # Create tool descriptions for the prompt
    tool_descriptions = []
    for tool in tools:
        tool_descriptions.append(f"- {tool.name}: {tool.description}")
    tools_text = "\n".join(tool_descriptions) if tool_descriptions else "No tools available"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", WORKER_PROMPT_TEMPLATE),
        ("human", "Task: {input}\nScratchpad: {agent_scratchpad}")
    ]).partial(role=role, instructions=instructions, tools=tools_text)
    
    print(f"🔧 Creating tool calling agent for {role}")
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    print(f"🔧 Creating agent executor for {role}")
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    print(f"🔧 {role} agent created with {len(executor.tools)} tools: {[t.name for t in executor.tools]}")
    return executor
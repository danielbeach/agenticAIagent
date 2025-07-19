import os
from langchain_openai import ChatOpenAI
from config import OPENAI_MODEL, DATABASE_URL
from tools import build_sql_tool, search_tool, fetch_tool
from agents import build_worker_agent
from memory import ConversationState
from graph import build_graph

# LLM instances
supervisor_llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
worker_llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.2)

# Build tools
print(f"🔧 Building SQL tool with DATABASE_URL: {DATABASE_URL}")
sql_tool = build_sql_tool(DATABASE_URL)
print(f"🔧 SQL tool created: {sql_tool.name if hasattr(sql_tool, 'name') else 'No name'}")
web_tools = [search_tool, fetch_tool]
print(f"🔧 Web tools created: {[t.name for t in web_tools]}")

# Create agents directly
sql_agent = build_worker_agent(
    role='SQL Analyst',
    instructions='You MUST use the SQL tool to query the transactions table. Start by querying for spending by category, then analyze user spending patterns. Use SQL queries to get actual data - do not provide general advice without querying the database first.',
    llm=worker_llm,
    tools=[sql_tool]
)

web_agent = build_worker_agent(
    role='Web Researcher',
    instructions='You MUST use the web_search tool to find current market trends and financial news. Then use fetch_page to get detailed information from relevant URLs. Do not provide general knowledge - search for current, specific information about market trends and investment opportunities.',
    llm=worker_llm,
    tools=web_tools
)

synthesizer_agent = build_worker_agent(
    role='Synthesizer',
    instructions='Combine spending analysis with market research to provide actionable investment recommendations. Suggest how current market trends relate to the spending patterns. Provide specific, practical advice for personal finance decisions.',
    llm=worker_llm,
    tools=[]
)

# Worker factories (return the pre-built agents)
worker_factories = {
    'SQL_AGENT': lambda: sql_agent,
    'WEB_AGENT': lambda: web_agent,
    'SYNTHESIZER': lambda: synthesizer_agent
}

app = build_graph(worker_factories, supervisor_llm)

if __name__ == '__main__':
    objective = "Analyze spending patterns from the transaction database and provide investment recommendations based on current market trends. Include specific spending insights and suggest how current market conditions might affect personal finance decisions."
    print(f"🎯 Objective: {objective}")
    print("=" * 80)
    
    state = {
        'conversation': ConversationState(),
        'user_objective': objective,
        'next': None
    }
    
    print("🚀 Starting multi-agent workflow...")
    for step in app.stream(state, config={"recursion_limit": 50}):
        for node, node_state in step.items():
            if node != '__end__':
                print(f"📋 [{node}] -> next: {node_state.get('next')}")
                # Print the latest message from each agent
                if 'conversation' in state and state['conversation'].messages:
                    latest_msg = state['conversation'].messages[-1]
                    if latest_msg.startswith(f"{node.upper()}"):
                        print(f"   💬 {latest_msg}")
    
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print(state['conversation'].render())
    print("\n" + "=" * 80)
    print("✅ Multi-agent workflow completed successfully!")
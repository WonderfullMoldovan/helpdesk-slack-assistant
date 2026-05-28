"""
Supervisor agent — top-level orchestrator that classifies incoming queries
and routes them to specialized sub-agents.

Routing decision is LLM-driven, not rule-based, so the system handles
paraphrases and ambiguous phrasings.
"""

from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.action_agent import action_node
from app.agents.escalation_agent import escalation_node
from app.agents.knowledge_agent import generate_node, retrieve_node
from app.llm.azure_client import get_chat_client
from app.rag.retrieval import RetrievedChunk

# ============================================================
# Top-level state
# ============================================================

AgentRoute = Literal["knowledge", "action", "escalation"]

class SupervisorState(TypedDict):
    """
    Top-level state that flows through Supervisor graph.

    Fields populated by Supervisor:
        query: user input
        session: DB session
        user_id: Slack user ID for context
        route: classification result (which agent to invoke)

    Fields populated by sub-agents:
        retrieved_chunks: from Knowledge Agent retrieve_node
        answer: final answer from any agent
    """
    query: str
    session: AsyncSession
    user_id: str
    route: AgentRoute
    retrieved_chunks: list[RetrievedChunk]
    answer: str

CLASSIFICATION_SYSTEM_PROMPT = """You are a query classifier for an IT helpdesk system.

Classify the user's query into EXACTLY ONE of three categories:

1. "knowledge" — informational questions about IT systems, procedures, troubleshooting.
   Examples:
   - "How do I reset my password?"
   - "What does VPN error 433 mean?"
   - "Can I get a second monitor?" (asking about policy/process)

2. "action" — requests to perform an action that changes state.
   Examples:
   - "Reset my password now"
   - "Create a ticket for my broken laptop"
   - "Request a new monitor for me"

3. "escalation" — user explicitly asks for human help, or query is complex/sensitive
   beyond automated handling.
   Examples:
   - "I need to talk to an IT engineer"
   - "This is urgent, please escalate"
   - "I tried everything and nothing works"

Respond with ONLY one word: knowledge, action, or escalation.
No explanation, no punctuation, just the category."""

# ============================================================
# Supervisor classification node
# ============================================================

async def supervisor_node(state: SupervisorState) -> dict:
    """
    Supervisor node that classifies the query and decides which agent to route to.

    Reads from state: query
    Writes to state: route
    """
    query = state["query"]

    print(f"[supervisor] classifying query: {query!r}")

    messages = [
        SystemMessage(content=CLASSIFICATION_SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]
    llm = get_chat_client()
    response = await llm.ainvoke(messages)
    # Normalize the response — LLM should return one word, but be defensive
    raw = response.content.strip().lower()
    if "action" in raw:
        route: AgentRoute = "action"
    elif "escalation" in raw or "escalate" in raw:
        route = "escalation"
    else:
        route = "knowledge"
    print(f"[supervisor] route={route} (raw LLM output: {raw!r})")

    return {"route": route}

# ============================================================
# Conditional edge function
# ============================================================

def route_to_agent(state: SupervisorState) -> str:
    """
    Conditional edge: read state.route, return name of next node.

    LangGraph uses the return value to determine which node executes next.
    """
    return state["route"]
# ============================================================
# Build top-level graph
# ============================================================

def build_supervisor_graph():
    """
    Build the top-level Supervisor graph.

    Topology:
        START → supervisor → (route to one of:)
                        → knowledge: retrieve → generate → END
                        → action: action_node → END
                        → escalation: escalation_node → END
    """
    builder = StateGraph(SupervisorState)

    # Register all nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_node("action", action_node)
    builder.add_node("escalation", escalation_node)

    # Entry: always go to supervisor first
    builder.add_edge(START, "supervisor")

    # Conditional edge: supervisor decides where to go next
    builder.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "knowledge": "retrieve",
            "action": "action",
            "escalation": "escalation",
        },
    )

    # Knowledge path: retrieve → generate → END
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    # Action and Escalation are single-node paths to END
    builder.add_edge("action", END)
    builder.add_edge("escalation", END)

    return builder.compile()


# ============================================================
# Public API
# ============================================================

async def handle_user_query(
    session: AsyncSession,
    query: str,
    user_id: str,
) -> str:
    """
    Top-level entry point for the multi-agent system.

    Routes query through Supervisor to appropriate agent, returns answer.

    Args:
        session: active DB session
        query: user's natural language input
        user_id: Slack user ID (for escalation context)

    Returns:
        Generated answer (Markdown-formatted, ready for Slack)
    """
    from app.observability.langfuse_client import get_langfuse_handler

    graph = build_supervisor_graph()

    initial_state: SupervisorState = {
        "query": query,
        "session": session,
        "user_id": user_id,
        "route": "knowledge",  # placeholder, supervisor will overwrite
        "retrieved_chunks": [],
        "answer": "",
    }

    handler = get_langfuse_handler()

    final_state = await graph.ainvoke(
        initial_state,
        config={
            "callbacks":[handler],
            "metadata":{
                "slack_user_id": user_id,
                "query_preview": query[:100]
            },
            "run_name":"Helpdes_slack_request"
        }
    )

    return final_state["answer"]

"""
Knowledge Agent — answers user questions using RAG.

Graph topology:
    START → retrieve → generate → END

State flows through:
- User query (input)
- Retrieved chunks from KB (added by retrieve node)
- Final answer (added by generate node)

This is the minimal viable agent. Future enhancements:
- Reflection / re-retrieval if answer is poor
- Citation extraction in structured form
- Confidence scoring
- Fallback to escalation
"""
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.azure_client import get_chat_client
from app.rag.retrieval import RetrievedChunk, hybrid_search, search_kb

# ============================================================
# State schema
# ============================================================

class KnowledgeAgentState(TypedDict):
    """
    State that flows through the Knowledge Agent graph.

    Fields:
        query: original user question
        session: database session (passed in, not modified by graph)
        retrieved_chunks: chunks fetched by retrieve node
        answer: final generated answer
    """
    query: str
    session: AsyncSession
    retrieved_chunks: list[RetrievedChunk]
    answer: str
# ============================================================
# Node: retrieve
# ============================================================

async def retrieve_node(state: KnowledgeAgentState) -> dict:
    """
    Search KB for chunks relevant to the user query.

    Reads from state: query, session
    Writes to state: retrieved_chunks
    """
    query = state["query"]
    session = state["session"]

    print(f"[knowledge_agent] retrieve: query={query!r}")

    chunks = await hybrid_search(session, query, top_k=3)

    print(f"[knowledge_agent] retrieve: found {len(chunks)} chunks")
    for chunk in chunks:
        print(f"  - doc={chunk.document_title!r} distance={chunk.distance:.4f}")

    # Return only the fields we're updating
    return {"retrieved_chunks": chunks}

# ============================================================
# Node: generate
# ============================================================

SYSTEM_PROMPT = """You are an IT helpdesk assistant for an internal company support system.

Your job:
- Answer the user's question using ONLY the provided KB context below
- Be concise and direct — IT helpdesk users want quick answers
- Use Markdown formatting (Slack renders **bold**, lists, code blocks)
- If the KB context doesn't contain enough info to answer, say so clearly — DO NOT make up information
- Reference document titles when relevant (e.g., "See: VPN Connection Issues")

Do NOT:
- Invent information not in the KB
- Pretend to know about systems not mentioned
- Provide generic IT advice if no specific KB context applies
"""


async def generate_node(state: KnowledgeAgentState) -> dict:
    """
    Generate final answer using LLM, grounded in retrieved chunks.

    Reads from state: query, retrieved_chunks
    Writes to state: answer
    """
    query = state["query"]
    chunks = state["retrieved_chunks"]

    print(f"[knowledge_agent] generate: query={query!r} chunks={len(chunks)}")

    # Build context from chunks
    if chunks:
        context_parts = []
        for chunk in chunks:
            context_parts.append(
                f"### From: {chunk.document_title}\n\n{chunk.content}"
            )
        context = "\n\n---\n\n".join(context_parts)
    else:
        context = "(No relevant KB articles found.)"

    # Build messages
    user_message = f"""User question:
{query}

KB context:
{context}

Answer the user's question based on the KB context above. Be concise."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    # Call LLM
    llm = get_chat_client()
    response = await llm.ainvoke(messages)

    answer = response.content
    print(f"[knowledge_agent] generate: answer length={len(answer)} chars")

    return {"answer": answer}
# ============================================================
# Graph definition
# ============================================================

def build_knowledge_graph():
    """
    Build and compile the Knowledge Agent graph.

    Returns a compiled graph ready to be invoked with initial state.

    Topology:
        START -> retrieve -> generate -> END
    """
    builder = StateGraph(KnowledgeAgentState)

    # Register nodes
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)

    # Define edges
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    # Compile — produces an executable Pregel-style runtime
    return builder.compile()


# ============================================================
# Public API
# ============================================================

async def answer_question(session: AsyncSession, query: str) -> str:
    """
    Public entry point for the Knowledge Agent.

    Builds (or reuses) the graph, runs it with the given query,
    returns the generated answer.

    Args:
        session: active DB session for retrieval
        query: user's natural language question

    Returns:
        Generated answer string (Markdown-formatted, suitable for Slack).
    """
    graph = build_knowledge_graph()

    initial_state: KnowledgeAgentState = {
        "query": query,
        "session": session,
        "retrieved_chunks": [],
        "answer": "",
    }

    final_state = await graph.ainvoke(initial_state)

    return final_state["answer"]

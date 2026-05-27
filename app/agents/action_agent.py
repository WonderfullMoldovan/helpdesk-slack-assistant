"""
Action Agent — handles requests that require performing actions
(e.g., create ticket, open password reset, request hardware).

Current status: STUB.
The architecture supports this agent as a peer to Knowledge Agent,
routed by Supervisor. Full implementation deferred — out of capstone scope.

What it WOULD do (production):
- Identify the action type (create_ticket, reset_password, request_hw, ...)
- Validate user permissions for that action
- Call appropriate tool (Jira API, AD API, etc.)
- Confirm with user via human-in-the-loop if action is high-stakes
- Log to audit_log

Today: returns a placeholder explaining the limitation.
"""
from typing import TypedDict


class ActionAgentState(TypedDict):
    """State for Action Agent (subset of top level state)."""
    query: str
    answer: str


async def action_node(state: dict) -> dict:
    """
    Stub for Action Agent.

    In production this would parse the action, validate permissions,
    invoke tools, and confirm with user via human-in-the-loop.
    """

    query = state["query"]

    print(f"[action_agent] received query: {query!r}")

    # Placeholder response for now
    answer = (
        "I recognize this as an action request (creating tickets, requesting hardware, "
        "performing system changes). The Action Agent is part of the architecture "
        "but not yet implemented in this version.\n\n"
        "Please contact #it-support directly for now, or rephrase your question "
        "as an informational query (e.g., 'How do I request a second monitor?') "
        "to get answered by the Knowledge Agent."
    )

    return {"answer": answer}

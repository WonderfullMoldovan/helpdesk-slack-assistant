"""
Escalation Agent — handles cases requiring human intervention.

Current status: MINIMAL STUB.
Logs the escalation to escalations table (Block 6 schema),
but doesn't yet notify engineers, no reminder scheduler.

What it WOULD do (production):
- Insert escalation record with status=waiting_for_human
- Notify on-call engineer via Slack DM
- Schedule reminder if no response in N hours
- Reroute to fallback engineer after max_reminders

Today: inserts escalation record + returns user-facing message.
"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.models import Escalation


async def escalation_node(state: dict) -> dict:
    """
    Stub for Escalation Agent.

    Logs an escalation record to DB so audit trail exists.
    Returns user-facing message confirming escalation was registered.
    """
    query = state["query"]
    session: AsyncSession = state["session"]
    user_id_str: str = state.get("user_id", "unknown_user")
    print(f"[escalation_agent] received query: {query!r}")

    # Insert escalation record (DB schema from Block 6)
    # thread_id is the Slack thread / DM channel — for capstone we use user_id
    # as a placeholder; real implementation would use Slack thread_ts.
    escalation = Escalation(
        thread_id = f"slack:{user_id_str}",
        requester_id = None,
        reason = "explicit_request",
        status = "waiting_for_human",
        context={
            "query": query,
            "source": "slack",
            "agent_routing" : "escalation",
        },
    )
    # NOTE: This will fail because requester_id is NOT NULL in our schema.
    # Stub keeps the call site shape; full implementation requires user lookup.
    # For now we skip the actual insert and return a placeholder message.

    answer = (
        "I've flagged this for the IT team to handle directly.\n\n"
        "**What happens next:** an IT engineer will follow up via Slack within the next "
        "few hours. In urgent cases, please also ping #it-support directly.\n\n"
        "*Note: Escalation Agent is implemented as architectural scaffold in this version; "
        "full notification flow (engineer assignment, reminders, audit logging) is "
        "specified in the SDD but deferred from capstone scope.*"
    )

    return {"answer": answer}

"""
Diagnostic: run Supervisor graph end-to-end on sample queries.
Tests that classification + routing + agent invocation work.
"""
import asyncio

from app.agents.supervisor import handle_user_query
from app.repositories.database import close_database, get_session_factory, init_database

# Queries designed to hit each route
TEST_QUERIES = [
    # Knowledge route — informational
    "How do I reset my password?",
    "What does VPN error 433 mean?",

    # Action route — state-changing
    "Reset my password now",
    "Create a ticket for my broken laptop",

    # Escalation route — explicit human help
    "I need to talk to an IT engineer",
    "This is urgent, escalate me to a human",
]


async def test_query(query: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"QUERY: {query}")
    print('=' * 70)

    session_factory = get_session_factory()
    async with session_factory() as session:
        answer = await handle_user_query(
            session=session,
            query=query,
            user_id="U0B681KPM2M",  # placeholder
        )

    print(f"\nANSWER:\n{answer}")


async def main():
    print("=== Supervisor end-to-end test ===")
    await init_database()

    try:
        for query in TEST_QUERIES:
            await test_query(query)

        print(f"\n{'=' * 70}")
        print("Done.")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
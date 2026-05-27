"""
Slack webhook endpoint — entry point for all incoming Slack events.

Flow:
1. Verify HMAC signature (via dependency)
2. Parse event payload
3. Handle URL verification challenge (one-time during Slack App setup)
4. Deduplicate via Redis (event_id with TTL)
5. ACK Slack within 3 seconds (200 OK)
6. (Future: trigger background processing)
"""

import json
from typing import Any

import redis.asyncio as redis_async
from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.slack_verify import verify_slack_signature
from app.repositories.database import get_db_session
from app.repositories.redis_client import get_redis
from app.repositories.user_repository import UserRepository

router = APIRouter(
    prefix="/slack",
    tags=["slack"],
)
# Slack expects an ACK within 3 seconds.
# Dedup keys live for 10 minutes (longer than Slack's own retry window).
DEDUP_TTL_SECONDS = 60 * 60 * 24
# Note: the actual processing of the event (e.g., posting a response) happens
# in a background task, so we can return the ACK immediately without waiting.
async def process_user_message(
    channel: str,
    user_id: str,
    text: str,
) -> None:
    """
    Background task: identify user, route to Knowledge Agent, reply.

    Flow:
    1. Create DB session (background task is outside FastAPI request scope)
    2. Identify or create user (Block 9)
    3. Route query to Knowledge Agent (Block 10)
    4. Post agent's answer back to Slack

    Note: any exception is logged + best-effort error notification to user.
    """
    from app.agents.supervisor import handle_user_query
    from app.api.slack_client import get_user_info, post_message
    from app.repositories.database import get_session_factory


    try:
        session_factory = get_session_factory()
    except RuntimeError:
        print("[slack] DB session factory not initialized")
        return

    try:
        async with session_factory() as session:
            user_repo = UserRepository(session)

            existing = await user_repo.get_by_slack_id(user_id)

            if existing is None:
                #new user - fetch profile from Slack
                print(f"[slack] New user {user_id}, fetching profile")
                profile = await get_user_info(user_id)

                user, _ = await user_repo.get_or_create_by_slack_id(
                    slack_user_id = user_id,
                    email = profile.get("email"),
                    display_name = profile.get("display_name"),
                    )
                await session.commit() # commit new user to DB
                print(
                    f"[slack] Created user {user.id} "
                    f"(slack={user_id}, name={user.display_name!r})"
                )
            else:
                user = existing
                print(f"[slack] Found existing user {user.id} for Slack ID {user_id}")

                #Route to Supervisor - multi-agent dispatch
                print(f"[slack] Routing to Supervisor Agent: {text!r}")
                answer = await handle_user_query(
                    session=session,
                    query=text,
                    user_id=user_id,
                )
                print(f"[slack] Agent returned {len(answer)} chars")

                # Post answer back to Slack
                await post_message(
                    channel=channel,
                    text=answer,
                )
                print(f"[slack] Posted response to {channel} for user {user.id}")
    except Exception as e:
        print(f"[slack] process_user_message failed: {type(e).__name__}: {e}")
        try:
            await post_message(
                channel=channel,
                text="Sorry, something went wrong processing your message.",
            )
        except Exception as inner:
            print(f"[slack] Failed to send error message: {inner}")

@router.post("/events")
async def handle_slack_event(
    background_tasks: BackgroundTasks,
    body: bytes = Depends(verify_slack_signature),
    redis: redis_async.Redis = Depends(get_redis),
) -> JSONResponse:
    """
    Handle incoming Slack events.

    Flow:
    1. Verify HMAC signature (dependency)
    2. Handle URL verification challenge
    3. Deduplicate via Redis
    4. Schedule background task for actual processing
    5. ACK Slack within 3 seconds
    """
    payload: dict [str, Any] = json.loads(body)
    event_type = payload.get("type")
            # ----------------------------------------------------------
    # Category 1: URL Verification Challenge
    # ----------------------------------------------------------
    # When you add a Request URL in Slack App settings, Slack sends
    # a one-time verification request with type="url_verification".
    # We must echo back the 'challenge' value to prove we own the endpoint.
    if event_type == "url_verification":
        challenge = payload.get("challenge", "")
        return JSONResponse(
            content={"challenge": challenge},
            status_code=status.HTTP_200_OK,
        )

    # ----------------------------------------------------------
    # Category 2: Real Events
    # ----------------------------------------------------------
    # For "event_callback" type, Slack wraps the actual event in payload["event"]
    if event_type != "event_callback":
        # Unknown event type — log and ACK
        print(f"[slack] Unknown event type :{event_type}")
        return JSONResponse(
            content={"ok": True},
            status_code=status.HTTP_200_OK,
        )
    # ----------------------------------------------------------
    # Deduplication via Redis
    # ----------------------------------------------------------
    # Slack retries events on missed ACK; without dedup we'd process
    # the same message multiple times.
    event_id = payload.get("event_id")
    if event_id:
        dedup_key = f"slack:event:{event_id}"
        # SET NX (only if not exists) returns True if key was set,
        # False if it already existed = duplicate.
        was_set = await redis.set(dedup_key, "1", ex=DEDUP_TTL_SECONDS, nx=True)
        if not was_set:
            print(f"[slack] Duplicate event: {event_id}, skipping")
            return JSONResponse(
                content={"ok": True, "duplicate": True},
                status_code=status.HTTP_200_OK,
            )
    # ----------------------------------------------------------
    # Process the event (echo for now)
    # ----------------------------------------------------------
    event = payload.get("event", {})
    inner_type = event.get("type")
    user_id = event.get("user")
    text = event.get("text", "")
    channel = event.get("channel")

    #ignore messages from bots (including itself) to avoid loops
    if event.get("bot_id"):
        print(f"[slack] Ignoring bot message: {channel}")
        return JSONResponse(
            content={"ok": True},
            status_code=status.HTTP_200_OK,
        )

    print(
        f"[slack] Received event: type={inner_type} "
        f"user={user_id} text={text!r}"
    )

    #Schedule Backgound processing
    # FastAPI will invoke this AFTER returning the 200 OK below
    if inner_type in {"message", "app_mention"}:
        background_tasks.add_task(
            process_user_message,
            channel=channel,
            user_id=user_id,
            text=text,
        )
    # ACK Slack immediately — actual processing happens in background
    return JSONResponse(content={"ok": True}, status_code=status.HTTP_200_OK)

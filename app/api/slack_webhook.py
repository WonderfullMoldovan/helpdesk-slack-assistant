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

from app.api.slack_verify import verify_slack_signature
from app.repositories.redis_client import get_redis

router = APIRouter(
    prefix="/slack",
    tags=["slack"],
)
# Slack expects an ACK within 3 seconds.
# Dedup keys live for 10 minutes (longer than Slack's own retry window).
DEDUP_TTL_SECONDS = 60 * 10
async def process_user_message(
    channel: str,
    user_id: str,
    text: str,
) -> None:
    """
    Background task: process a user message and reply.

    For now: echo. Future blocks will route to LangGraph agent.

    Note: any exception here is logged but doesn't fail the user-facing request
    (the webhook already ACK'd with 200 OK).
    """
    from app.api.slack_client import post_message

    try:
        # Echo response - for now, just confirm receipt
        await post_message(
            channel=channel,
            text=f"Echo: {text}",
        )
        print(f"[slack] Replied to {user_id} in {channel}")
    except Exception as e:
        # Background tasks can't propagate errors to the user via the webhook
        # (already 200 OK'd). Log for debugging and try to notify user about failure.
        print(f"[slack] process_user_message failed: {type(e).__name__}: {e}")
        try:
            await post_message(
                channel=channel,
                text="Sorry, I hit an error processing your request. Please try again.",
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

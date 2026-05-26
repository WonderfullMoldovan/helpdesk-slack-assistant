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
from fastapi import APIRouter, Depends, status
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

@router.post("/events")
async def handle_slack_event(
    body: bytes = Depends(verify_slack_signature),
    redis: redis_async.Redis = Depends(get_redis),
) -> JSONResponse:
    """
    Handle incoming Slack events.

    Two categories of incoming requests:
    1. URL verification challenge (during Slack App setup)
    2. Real events (message.im, app_mention, etc.)
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
    if event_id :
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

    print(
        f"[slack] Received event: type={inner_type} "
        f"user={user_id} text={text!r}"
    )

    # TODO: in next blocks, trigger agent graph here
    # For now, just ACK — we'll add response posting in Block 8

    return JSONResponse(content={"ok": True}, status_code=status.HTTP_200_OK)
"""
Slack webhook signature verification.

Implements HMAC-SHA256 verification as documented at:
https://api.slack.com/authentication/verifying-requests-from-slack

Every incoming webhook is verified BEFORE any business logic.
Failure to verify is a 401 response with no further processing.
"""
import hashlib
import hmac
import time

from fastapi import Header, HTTPException, Request, status

from app.config.settings import settings

# Slack signature version, always "v0"
SIGNATURE_VERSION = "v0"
# Maximum age of a request, in seconds. Older requests rejected as potential replay.
MAX_REQUEST_AGE_SECONDS = 60*5 # 5 min

async def verify_slack_signature(
        request: Request,
        x_slack_signature :str = Header(...),
        x_slack_request_timestamp:str = Header(...),
) -> bytes:
        """
    FastAPI dependency that verifies the incoming request is from Slack.

    Returns the raw request body if verification succeeds.
    Raises HTTPException(401) if verification fails.

    The raw body is returned because:
    1. Verification consumes it (request.body() can only be called once)
    2. Handler needs the body anyway to parse the event

    Usage:
        @router.post("/slack/events")
        async def handler(body: bytes = Depends(verify_slack_signature)):
            data = json.loads(body)
    """
    # Check timestamp freshness (anti-replay)
        try:
            timestamp = int(x_slack_request_timestamp)
        except ValueError:
            raise HTTPException(  # noqa: B904
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail= "Invalid timestamp header",
            )

        now = int(time.time())
        if abs(now - timestamp) > MAX_REQUEST_AGE_SECONDS:
            raise HTTPException(
                status_code= status.HTTP_401_UNAUTHORIZED,
                detail="Request timestamp too old (possible replay)"
            )
        # Read raw body (must be raw bytes, not parsed JSON)
        body = await request.body()
        # Compute expected signature
        # Slack's formula: HMAC-SHA256 of "{version}:{timestamp}:{body}"
        sig_basestring = f"{SIGNATURE_VERSION}:{timestamp}:{body.decode('utf-8')}"
        signing_secret = settings.slack_signing_secret.get_secret_value().encode("utf-8")

        computed_signature = (
            SIGNATURE_VERSION
            + "="
            +hmac.new(
                key=signing_secret,
                msg=sig_basestring.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
        )
            # Constant-time comparison (defense against timing attacks)
        if not hmac.compare_digest(computed_signature, x_slack_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature verification failed",
        )

        # Verification passed — return body for handler use
        return body


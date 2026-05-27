"""
Slack Web API client — for outgoing calls to Slack.

While slack_webhook.py handles incoming events (Slack -> us),
this module handles outgoing API calls (us -> Slack):
- Posting messages to channels/DMs
- Sending DMs to specific users
- (Future) Posting interactive blocks for HITL escalations
"""
from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from app.config.settings import settings

# Module-level singleton — one client for entire app lifecycle
_slack_client: AsyncWebClient | None = None

def get_slack_client() -> AsyncWebClient:
    """
    Returns the Slack Web API client (singleton).

    The client is stateless — safe to reuse across requests.
    Internally it manages an aiohttp session, which is created on first use.
    """
    global _slack_client
    if _slack_client is None:
        _slack_client = AsyncWebClient(token=settings.slack_bot_token.get_secret_value())
    return _slack_client

async def post_message(
        channel: str,
        text: str,
        thread_ts: str | None = None,
) -> dict[str, Any]:
    """
    Post a message to a Slack channel or DM.

    Args:
        channel: Channel ID (e.g., "D0123ABCD") or user ID for DM.
        text: Message body. Slack will render basic Markdown.
        thread_ts: If set, post as a reply in this thread.

    Returns:
        Slack API response dict.

    Raises:
        SlackApiError: If Slack returns an error response.
    """

    client = get_slack_client()

    try:
        response = await client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
        )
        return response.data
    except SlackApiError as e:
        # Log and re-raise — caller decides how to handle
        print(f"[slack] chat_postMessage failed: {e.response['error']}")
        raise

async def get_user_info(slack_user_id: str) -> dict[str, Any]:
    """
    Get user info from Slack by user ID.

    Returns relevant fields: email, display_name, real_name.

    If Slack API errors or user not found, returns empty dict
    (caller handles missing fields gracefully).
    """
    client = get_slack_client()

    try:
        response = await client.users_info(user=slack_user_id)
        user_data = response.data.get("user", {})
        profile = user_data.get("profile", {})
        return {
            "email": profile.get("email"),
            "display_name": profile.get("display_name"),
            "real_name": profile.get("real_name"),
        }
    except SlackApiError as e:
        print(f"[slack] users_info failed for {slack_user_id}: {e.response['error']}")
        return {}

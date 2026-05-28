"""
Langfuse client — observability for LLM workflows.

Uses Langfuse v3 API:
- Initialize global Langfuse client once (reads credentials)
- CallbackHandler() picks up credentials from global client

When CallbackHandler is passed to LangChain invocations, every LLM call,
chain step, and graph node is automatically traced in Langfuse.

Usage:
    handler = get_langfuse_handler()
    response = await llm.ainvoke(messages, config={"callbacks": [handler]})
"""
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.config.settings import settings


# Module-level singletons — created lazily on first access
_langfuse_client: Langfuse | None = None
_callback_handler: CallbackHandler | None = None


def _init_langfuse() -> Langfuse:
    """Initialize the global Langfuse client (reads credentials)."""
    global _langfuse_client

    if _langfuse_client is None:
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key.get_secret_value(),
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            host=settings.langfuse_host,
        )

    return _langfuse_client


def get_langfuse_handler() -> CallbackHandler:
    """
    Returns the singleton Langfuse CallbackHandler for LangChain integration.

    The handler reads credentials from the global Langfuse client,
    which we initialize once on first call.
    """
    global _callback_handler

    if _callback_handler is None:
        # Initialize global Langfuse client first (v3 API requirement)
        _init_langfuse()
        # Handler picks up credentials from global client
        _callback_handler = CallbackHandler()

    return _callback_handler

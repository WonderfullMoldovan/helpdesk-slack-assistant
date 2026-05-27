"""
Azure OpenAI client factories.

Provides LangChain-compatible chat and embedding clients configured for Azure OpenAI.
Singletons: one client per role (chat / embedding), reused across the app.

Why LangChain wrappers (AzureChatOpenAI, AzureOpenAIEmbeddings) instead of raw openai SDK:
- LangGraph and other LangChain components expect LangChain BaseChatModel interface
- Standardized message types (HumanMessage, AIMessage, SystemMessage)
- Built-in retry, streaming, callbacks integration

The clients are stateless and safe for concurrent use across async requests.
"""

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.config.settings import settings


# Module-level singeltons -created lazily on first access
_chat_client: AzureChatOpenAI | None = None
_embedding_client: AzureOpenAIEmbeddings | None = None

def get_chat_client() -> AzureChatOpenAI:
    """
    Returns the singleton AzureChatOpenAI client for chat completions.

    Configured for gpt-5.4 reasoning model with:
    - max_completion_tokens (NOT max_tokens — reasoning models reject the latter)
    - reasoning_effort controls latency / quality trade-off
    """
    global _chat_client

    if _chat_client is None:
        _chat_client = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment_chat,
            api_version=settings.azure_openai_api_version_chat,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            # reasoning_effort is first-class in recent langchain-openai
            reasoning_effort=settings.azure_openai_reasoning_effort,
            max_completion_tokens=2000,
            timeout=60.0,
            max_retries=2,
        )
    return _chat_client

def get_embedding_client() -> AzureOpenAIEmbeddings:
    """
    Returns the singleton AzureOpenAIEmbeddings client for text embeddings.

    Configured for text-embedding-3-large with:
    - dimensions truncated to 1536 to match pgvector column and reduce costs
    """
    global _embedding_client

    if _embedding_client is None:
        _embedding_client = AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment_embedding,
            api_version=settings.azure_openai_api_version_embedding,
            api_key=settings.azure_openai_embedding_api_key.get_secret_value(),
            # Truncate native 3072 dims down to 1536 to match our pgvector column
            dimensions=settings.azure_openai_embedding_dimensions,
            timeout=30.0,
            max_retries=2,
        )
    return _embedding_client

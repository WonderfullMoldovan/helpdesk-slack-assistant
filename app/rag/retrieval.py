"""
RAG retrieval — search the knowledge base for relevant chunks.

Strategy: vector similarity search using pgvector.
Future enhancement: hybrid search combining vector + BM25 (full-text).
"""
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.azure_client import get_embedding_client


@dataclass
class RetrievedChunk:
    """A chunk returned from the knowledge base, with retrieval metadata."""
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    distance: float  # cosine distance, lower = more similar

    @property
    def similarity_score(self) -> float:
        """Cosine similarity, higher = more similar. Convenience for display."""
        return 1.0 - self.distance


async def search_kb(
    session: AsyncSession,
    query: str,
    top_k: int = 3,
) -> list[RetrievedChunk]:
    """
    Search the knowledge base for chunks most relevant to `query`.

    Process:
    1. Embed the query via Azure OpenAI
    2. Cosine distance search against kb_chunks.embedding (pgvector)
    3. Return top_k chunks, joined with kb_documents for title

    Args:
        session: active database session
        query: natural language search query
        top_k: maximum number of chunks to return

    Returns:
        List of RetrievedChunk, ordered by relevance (most similar first).
        Empty list if no chunks in KB.
    """
    if not query.strip():
        return []

    # Step 1: embed the query
    embedding_client = get_embedding_client()
    query_vector = await embedding_client.aembed_query(query)

    # Step 2: vector similarity search
    # The <=> operator is pgvector's cosine distance (NOT similarity).
    # Lower distance = more similar.
    sql = text("""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.title AS document_title,
            c.content,
            c.embedding <=> CAST(:query_vector AS vector) AS distance
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE c.deleted_at IS NULL
          AND d.deleted_at IS NULL
        ORDER BY distance ASC
        LIMIT :top_k
    """)

    result = await session.execute(
        sql,
        {
            "query_vector": str(query_vector),  # pgvector accepts text repr
            "top_k": top_k,
        },
    )

    chunks = [
        RetrievedChunk(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            content=row.content,
            distance=float(row.distance),
        )
        for row in result
    ]

    return chunks

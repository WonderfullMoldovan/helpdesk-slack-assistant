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

async def hybrid_search(
        session: AsyncSession,
        query: str,
        top_k: int = 3,
        candidates_per_system: int = 10,
        rrf_k: int = 60,
) -> list[RetrievedChunk]:
    """
    Hybrid search: combine vector similarity and BM25-style keyword search.

    Algorithm:
    1. Run vector search → top `candidates_per_system` chunks
    2. Run full-text search (PostgreSQL tsvector) → top `candidates_per_system` chunks
    3. Combine via Reciprocal Rank Fusion (RRF)
    4. Return top `top_k` after fusion

    Args:
        session: active DB session
        query: natural language search query
        top_k: final number of chunks to return
        candidates_per_system: how many candidates to fetch from each system
            (must be >= top_k, larger gives more recall but slower fusion)
        rrf_k: RRF constant, standard default 60 per Cormack et al. 2009

    Returns:
        List of RetrievedChunk ordered by RRF score (best first).
        The `distance` field on each chunk holds the original vector distance
        (or 1.0 if chunk was found only by BM25).
    """
    if not query.strip():
        return []

    # ----------------------------------------------------------------
    # Step 1: Vector search
    # ----------------------------------------------------------------
    embedding_client = get_embedding_client()
    query_vector = await embedding_client.aembed_query(query)

    vector_sql = text("""
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
        LIMIT :limit
    """)

    vector_result = await session.execute(
        vector_sql,
        {"query_vector": str(query_vector), "limit": candidates_per_system},
    )
    vector_rows = list(vector_result)

    # ----------------------------------------------------------------
    # Step 2: BM25 / full-text search
    # ----------------------------------------------------------------
    # plainto_tsquery handles tokenization and stemming.
    # ts_rank_cd uses cover density (term proximity) for ranking.
    fts_sql = text("""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.title AS document_title,
            c.content,
            ts_rank_cd(c.content_tsv, plainto_tsquery('english', :query)) AS rank
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE c.deleted_at IS NULL
        AND d.deleted_at IS NULL
        AND c.content_tsv @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :limit
    """)

    fts_result = await session.execute(
        fts_sql,
        {"query": query, "limit": candidates_per_system},
    )
    fts_rows = list(fts_result)

    # ----------------------------------------------------------------
    # Step 3: RRF fusion
    # ----------------------------------------------------------------
    # For each chunk, accumulate 1/(k + rank) from each system it appears in.
    # Chunks present in both systems get combined boost.

    rrf_scores: dict[int, float] = {}  # chunk_id -> accumulated RRF score
    chunk_data: dict[int, dict] = {}   # chunk_id -> row data (first occurrence wins)

    for rank, row in enumerate(vector_rows, start=1):
        chunk_id = row.chunk_id
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": row.document_id,
                "document_title": row.document_title,
                "content": row.content,
                "distance": float(row.distance),  # vector distance
            }

    for rank, row in enumerate(fts_rows, start=1):
        chunk_id = row.chunk_id
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        if chunk_id not in chunk_data:
            # Chunk found only by BM25 — no vector distance available
            chunk_data[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": row.document_id,
                "document_title": row.document_title,
                "content": row.content,
                "distance": 1.0,  # sentinel: "no vector distance"
            }

    # ----------------------------------------------------------------
    # Step 4: Sort by RRF score (descending), take top_k
    # ----------------------------------------------------------------
    sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    results = [
        RetrievedChunk(**chunk_data[cid])
        for cid in sorted_ids[:top_k]
    ]

    return results

"""
KB ingestion script — loads Markdown files from kb_docs/ into the database.

For each document:
1. Read raw content
2. Create kb_documents row
3. Chunk content (simple: ~500 chars per chunk)
4. Generate embedding for each chunk via Azure OpenAI
5. Insert kb_chunks rows with embeddings

Run with: python scripts/ingest_kb.py

This is a one-time setup script — not part of the running application.
Re-running will create duplicates; clear tables first if re-ingesting.
"""
import asyncio
from pathlib import Path
from pdb import main
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.llm.azure_client import get_embedding_client
from app.repositories.database import get_session_factory, close_database, init_database
from app.repositories.models import KBChunk, KBDocument

# Configuration
KB_DOCS_DIR = Path("kb_docs")
CHUNK_SIZE_CHARS = 800  # ~200 tokens, good for retrieval granularity
CHUNK_OVERLAP_CHARS = 100 # overlap between chunks to preserve context across boundaries

def chunk_text(text:str, chunk_size: int, overlap: int) -> list[str]:
    """Splits text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        # Move forward, but step back by 'overlap' for the next chunk
        start = end - overlap
        if start > len(text):
            break
    return chunks

async def ingest_document(session: AsyncSession, file_path: Path) -> None:
    """
    Process a single Markdown file: create document + chunks + embeddings.
    """
    print(f"\n--- Processing: {file_path.name} ---")
    # 1. Read raw content
    content = file_path.read_text(encoding="utf-8")
    print(f"Read {len(content)} characters")

    # 2.Extract title from first H1 heading or use filename
    first_line = content.split("\n", 1)[0]
    if first_line.startswith("# "):
        title = first_line[2:].strip()
    else:
        title = file_path.stem.replace("_", " ").title()


    # 3. Check if already ingested (idempotency)
    existing = await session.execute(
        select(KBDocument).where(KBDocument.source_path == str(file_path))
    )
    if existing.scalars().first():
        print(f"Document already ingested, skipping: {file_path.name}")
        return

    # 4. Create kb_documents row
    doc = KBDocument(
        title=title,
        content=content,
        source_path=str(file_path),
        doc_metadata={"filename": file_path.name}
    )
    session.add(doc)
    await session.flush()  # get doc.id for chunks
    print(f"  Created KBDocument id={doc.id} title={title!r}")


    # 5. Chunk content
    chunks = chunk_text(content, CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS)
    print(f"  Split into {len(chunks)} chunks")

    # Generate embeddings (batch all chunks in one API call for efficiency)
    embedding_client = get_embedding_client()
    embeddings = await embedding_client.aembed_documents(chunks)
    print(f"  Generated {len(embeddings)} embeddings ({len(embeddings[0])} dims each)")

    # 6. Create chink row
    for idx, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = KBChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=chunk_content,
            embedding=embedding,
            token_count=len(chunk_content) // 4 # rough estimate: 1 token ≈ 4 chars
        )
        session.add(chunk)
    print(f"  Added {len(chunks)} KBChunks")


async def main() -> None:
    print("=== KB Ingestion ===")
    print(f"Source directory: {KB_DOCS_DIR.absolute()}")
    print(f"Chunk size: {CHUNK_SIZE_CHARS} chars, overlap: {CHUNK_OVERLAP_CHARS} chars")
    print(f"Embedding model: {settings.azure_openai_deployment_embedding}")
    print(f"Embedding dimensions: {settings.azure_openai_embedding_dimensions}")


    # initialize db connection
    await init_database()

    try:
        session_factory=get_session_factory()
        #Find all .md files
        md_files = list(KB_DOCS_DIR.glob("*.md"))
        print(f"\nFound {len(md_files)} Markdown files")

        if not md_files:
            print("No Markdown files found in kb_docs/. Please add some .md files to ingest.")
            return
            # Process each in its own transaction
        for file_path in md_files:
            async with session_factory() as session:
                try:
                    await ingest_document(session, file_path)
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    print(f"Error processing {file_path.name}: {e}")
                    raise
        print("\n=== Ingestion complete ===")
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(main())

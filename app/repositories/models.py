"""
SQLAlchemy ORM models — the Python representation of database tables.

These models define both:
- The runtime API for database access (queries, inserts, updates)
- The schema source-of-truth from which Alembic generates migrations

Naming convention:
- Class names: PascalCase singular (User, Escalation)
- Table names: snake_case plural (users, escalations)
"""
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ============================================================
# Base class — all models inherit from this
# ============================================================

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ============================================================
# users
# ============================================================

class User(Base):
    """
    Maps a Slack identity to an internal employee record.

    Soft-deleted: 'deleted_at' marks departed employees while preserving
    historical references from escalations.
    """
    __tablename__ = "users"

    # Primary key: UUID because it appears in Slack payloads
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Natural key from Slack — globally unique within a workspace
    slack_user_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Role: validated in application layer (Python Enum / Pydantic)
    # DB-level CHECK omitted for evolution flexibility (per schema design)
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="employee",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships — for ORM-level navigation
    requested_escalations: Mapped[list["Escalation"]] = relationship(
        "Escalation",
        foreign_keys="Escalation.requester_id",
        back_populates="requester",
    )


# ============================================================
# escalations
# ============================================================

class Escalation(Base):
    """
    Records every human-in-the-loop escalation.

    Never deleted (indefinite audit retention). Status tracks lifecycle:
    waiting_for_human -> approved | denied | cancelled.

    Idempotency: partial unique index on thread_id WHERE status='waiting_for_human'
    prevents double-escalation at DB level.
    """
    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Soft reference to LangGraph checkpoint (not FK — different ownership)
    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Three separate user references
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    assigned_engineer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    resolver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Reason: low_confidence | high_stakes | explicit_request
    reason: Mapped[str] = mapped_column(String(32), nullable=False)

    # Status: waiting_for_human | approved | denied | cancelled
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="waiting_for_human",
        index=True,
    )

    # Packaged context for the engineer (original request, classification, etc.)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Reminder tracking
    reminder_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    last_reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requester_id],
        back_populates="requested_escalations",
    )

    # Table-level constraints
    __table_args__ = (
        # Partial unique index: at most one open escalation per thread
        # Enforces idempotency at DB level (per ADR / SDD §8.7)
        Index(
            "uq_escalations_open_per_thread",
            "thread_id",
            unique=True,
            postgresql_where="status = 'waiting_for_human'",
        ),
        # Engineer's pending queue
        Index(
            "idx_escalations_assigned_engineer",
            "assigned_engineer_id",
            postgresql_where="status = 'waiting_for_human'",
        ),
    )


# ============================================================
# kb_documents
# ============================================================

class KBDocument(Base):
    """
    Source knowledge base documents — full text and metadata.
    Chunks (KBChunk) are derived from these.
    """
    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship to chunks
    chunks: Mapped[list["KBChunk"]] = relationship(
        "KBChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


# ============================================================
# kb_chunks
# ============================================================

class KBChunk(Base):
    """
    Chunked, embedded representation of KB documents — the unit of RAG retrieval.

    Has both vector embedding (dense) and tsvector (sparse/keyword) for hybrid search.
    """
    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("kb_documents.id"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector embedding for semantic search (1536 dims = text-embedding-3-small)
    # Nullable to allow two-phase insert (chunk text first, embed async)
    embedding: Mapped[Any | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )

    # Generated column for full-text search (BM25-style keyword matching)
    # Maintained automatically by PostgreSQL from content column
    content_tsv: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
    )

    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship back to document
    document: Mapped["KBDocument"] = relationship(
        "KBDocument",
        back_populates="chunks",
    )

    # Table-level constraints and indexes
    __table_args__ = (
        # Chunk positions within a document are unique
        UniqueConstraint("document_id", "chunk_index", name="uq_kb_chunks_doc_idx"),
        # HNSW index for vector similarity search
        # Note: Created via raw SQL in migration (SQLAlchemy doesn't natively support HNSW yet)
        # See migration for: CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)
        # GIN index for full-text search
        Index(
            "idx_kb_chunks_content_tsv",
            "content_tsv",
            postgresql_using="gin",
        ),
    )


# ============================================================
# audit_log
# ============================================================

class AuditLog(Base):
    """
    Append-only record of system actions.

    By design: no updated_at, no deleted_at. Rows are inserted, never modified.
    This immutability is what makes it trustworthy as an audit trail.
    """
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Who/what performed the action: 'system', 'agent:supervisor', 'user_id', etc.
    actor: Mapped[str] = mapped_column(String(64), nullable=False)

    # Controlled vocabulary, validated in application layer
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Event-specific details
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Only created_at — no updated_at (append-only)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
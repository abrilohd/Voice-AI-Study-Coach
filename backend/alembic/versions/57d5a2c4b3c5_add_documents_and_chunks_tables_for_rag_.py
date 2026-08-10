"""add documents and chunks tables for RAG pipeline

Revision ID: 57d5a2c4b3c5
Revises: 51080b6750d5
Create Date: 2026-08-06 09:58:26.531614

"""
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision = '57d5a2c4b3c5'
down_revision = '51080b6750d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension for vector similarity search
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('chunk_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_document_chunks_document_id'),
        'document_chunks',
        ['document_id'],
        unique=False
    )
    
    # Create ivfflat index for approximate nearest-neighbor search on embeddings
    # Note: ivfflat index requires some data to exist before it's efficient.
    # The 'lists' parameter (100) is appropriate for <1M vectors.
    # For larger datasets (>1M vectors), consider switching to hnsw index.
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    # Drop tables (indexes are dropped automatically via CASCADE)
    op.drop_table('document_chunks')
    op.drop_table('documents')
    
    # Drop pgvector extension
    # Note: Only drop if no other tables are using vector types.
    # In production, manually verify before dropping the extension.
    op.execute("DROP EXTENSION IF EXISTS vector")

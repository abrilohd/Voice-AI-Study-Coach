"""replace_ivfflat_with_hnsw_index

Revision ID: 786ac8f492c5
Revises: 57d5a2c4b3c5
Create Date: 2026-11-07 06:11:33.599009

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '786ac8f492c5'
down_revision = '57d5a2c4b3c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace ivfflat index with HNSW for better recall and performance.
    
    HNSW (Hierarchical Navigable Small World) provides:
    - Better recall than IVFFlat (fewer false negatives)
    - No "lists" tuning required
    - Works well with small datasets (< 10k vectors)
    - Slightly higher build time, but faster queries
    
    Parameters:
    - m=16: Number of bidirectional links (balance between speed and recall)
    - ef_construction=64: Build-time quality (higher = better index, slower build)
    """
    # Drop existing ivfflat index
    op.drop_index("ix_chunks_embedding", table_name="document_chunks")
    
    # Create HNSW index with cosine distance
    op.execute("""
        CREATE INDEX ix_chunks_embedding 
        ON document_chunks 
        USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Rollback to ivfflat index."""
    # Drop HNSW index
    op.drop_index("ix_chunks_embedding", table_name="document_chunks")
    
    # Recreate ivfflat index
    op.execute("""
        CREATE INDEX ix_chunks_embedding 
        ON document_chunks 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    """)

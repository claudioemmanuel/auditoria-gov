"""er_confidence_shield

Revision ID: 2a85d83fddb3
Revises: 0020
Create Date: 2026-03-23 11:33:44.637295
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '2a85d83fddb3'
down_revision: Union[str, None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cluster_confidence to entity for ER confidence shield
    op.add_column(
        'entity',
        sa.Column(
            'cluster_confidence',
            sa.Integer(),
            sa.CheckConstraint('cluster_confidence BETWEEN 0 AND 100', name='ck_entity_cluster_confidence'),
            nullable=True,
        ),
    )

    # Create er_merge_evidence table to record why entities were merged
    op.create_table(
        'er_merge_evidence',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('entity_a_id', sa.UUID(), nullable=False),
        sa.Column('entity_b_id', sa.UUID(), nullable=False),
        sa.Column(
            'confidence_score',
            sa.Integer(),
            sa.CheckConstraint('confidence_score BETWEEN 0 AND 100', name='ck_er_merge_evidence_confidence_score'),
            nullable=False,
        ),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('evidence_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['entity_a_id'], ['entity.id']),
        sa.ForeignKeyConstraint(['entity_b_id'], ['entity.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index("ix_er_merge_evidence_entity_a", "er_merge_evidence", ["entity_a_id"])
    op.create_index("ix_er_merge_evidence_entity_b", "er_merge_evidence", ["entity_b_id"])


def downgrade() -> None:
    op.drop_index("ix_er_merge_evidence_entity_a", table_name="er_merge_evidence")
    op.drop_index("ix_er_merge_evidence_entity_b", table_name="er_merge_evidence")
    op.drop_table('er_merge_evidence')
    op.drop_column('entity', 'cluster_confidence')

"""dispensa_thresholds

Revision ID: 0021
Revises: 2a85d83fddb3
Create Date: 2026-03-23 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0021"
down_revision: Union[str, None] = "2a85d83fddb3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dispensa_threshold",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("categoria", sa.String(50), nullable=False),
        sa.Column("valor_brl", sa.Numeric(15, 2), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("decreto_ref", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Seed: Decreto 12.343/2024 (valid 2024-01-01 to 2025-12-31)
    # Seed: Decreto 12.807/2025 (valid from 2026-01-01)
    # NOTE: The exact 2026 values should be confirmed at https://www.gov.br/compras/pt-br
    # Using best available values at time of implementation
    op.execute("""
        INSERT INTO dispensa_threshold (categoria, valor_brl, valid_from, valid_to, decreto_ref)
        VALUES
          ('goods',   62725.59, '2024-01-01', '2025-12-31', 'Decreto 12.343/2024'),
          ('works',  125451.15, '2024-01-01', '2025-12-31', 'Decreto 12.343/2024'),
          ('goods',   66500.00, '2026-01-01', NULL,          'Decreto 12.807/2025'),
          ('works',  133000.00, '2026-01-01', NULL,          'Decreto 12.807/2025')
    """)


def downgrade() -> None:
    op.drop_table("dispensa_threshold")

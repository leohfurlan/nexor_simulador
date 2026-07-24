"""adiciona margem_lucro_estimada em sim_empresas

Revision ID: 0002_empresa_margem
Revises: 0001_initial_sim
Create Date: 2026-07-24

Campo opcional de margem de lucro líquida estimada (fração), usado para refinar
a sugestão de repasse de preço no Dashboard.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_empresa_margem"
down_revision: Union[str, None] = "0001_initial_sim"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sim_empresas",
        sa.Column("margem_lucro_estimada", sa.Numeric(6, 5), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sim_empresas", "margem_lucro_estimada")

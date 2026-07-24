"""adiciona parâmetros do Lucro Real em sim_parametros

Revision ID: 0003_lucro_real_params
Revises: 0002_empresa_margem
Create Date: 2026-07-24

Novo regime Lucro Real (5º cenário): alíquota de IRPJ+CSLL sobre o lucro e
honorário mensal do regime. Ambos configuráveis (nada hardcoded no motor).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_lucro_real_params"
down_revision: Union[str, None] = "0002_empresa_margem"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sim_parametros",
        sa.Column(
            "aliquota_lucro_real_irpj_csll",
            sa.Numeric(6, 5),
            nullable=False,
            server_default="0.34000",
        ),
    )
    op.add_column(
        "sim_parametros",
        sa.Column(
            "honorario_lucro_real",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="900.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("sim_parametros", "honorario_lucro_real")
    op.drop_column("sim_parametros", "aliquota_lucro_real_irpj_csll")

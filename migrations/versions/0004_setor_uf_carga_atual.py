"""setor/UF na empresa + parâmetros da carga atual (pré-reforma)

Revision ID: 0004_setor_uf_carga_atual
Revises: 0003_lucro_real_params
Create Date: 2026-07-24

Adiciona setor e UF em sim_empresas (para estimar ISS×ICMS) e as alíquotas
PIS/COFINS/ISS/ICMS em sim_parametros, usadas na estimativa da carga atual.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_setor_uf_carga_atual"
down_revision: Union[str, None] = "0003_lucro_real_params"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALIQ = sa.Numeric(6, 5)
_PARAM_COLS = (
    ("aliquota_pis", "0.00650"),
    ("aliquota_cofins", "0.03000"),
    ("aliquota_iss", "0.05000"),
    ("aliquota_icms", "0.18000"),
)


def upgrade() -> None:
    op.add_column("sim_empresas", sa.Column("setor", sa.String(length=20), nullable=True))
    op.add_column("sim_empresas", sa.Column("uf", sa.String(length=2), nullable=True))
    for nome, default in _PARAM_COLS:
        op.add_column(
            "sim_parametros",
            sa.Column(nome, _ALIQ, nullable=False, server_default=default),
        )


def downgrade() -> None:
    for nome, _ in reversed(_PARAM_COLS):
        op.drop_column("sim_parametros", nome)
    op.drop_column("sim_empresas", "uf")
    op.drop_column("sim_empresas", "setor")

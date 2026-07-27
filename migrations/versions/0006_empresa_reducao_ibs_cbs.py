"""adiciona reducao_ibs_cbs em sim_empresas

Revision ID: 0006_empresa_reducao_ibs_cbs
Revises: 0005_lucro_presumido_ibs_cbs
Create Date: 2026-07-27

A LC 214/2025 reduz a alíquota de IBS/CBS em 30% para as profissões
regulamentadas (art. 127) e em 60% para saúde e educação (arts. 128/129).
A redução só existe no regime regular de IBS/CBS — ou seja, vale para o SN
Híbrido, o Lucro Presumido c/ crédito e o Lucro Real, e NÃO para o SN Padrão,
que recolhe tudo no DAS. Sem esse campo o comparador subestima o Híbrido para
contadores, advogados, engenheiros, médicos etc., podendo inverter a
recomendação.

Campo opt-in por empresa: NULL = sem redução (comportamento anterior).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_empresa_reducao_ibs_cbs"
down_revision: Union[str, None] = "0005_lucro_presumido_ibs_cbs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sim_empresas",
        sa.Column("reducao_ibs_cbs", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sim_empresas", "reducao_ibs_cbs")

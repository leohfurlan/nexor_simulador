"""separa IBS/CBS do Lucro Presumido em campo próprio

Revision ID: 0005_lucro_presumido_ibs_cbs
Revises: 0004_setor_uf_carga_atual
Create Date: 2026-07-24

`aliquota_lucro_presumido` deixa de ser o combinado "IRPJ+CSLL+IBS/CBS"
(16,55%) e passa a representar só IRPJ+CSLL do Lucro Presumido puro
(13,33%, valor de mercado atual). O IBS/CBS do Lucro Presumido c/ crédito
ganha campo próprio (`aliquota_lucro_presumido_ibs_cbs`, 27%), antes
hardcoded junto no mesmo número — por isso os dois cards do simulador
mudavam juntos quando só um deveria mudar.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_lucro_presumido_ibs_cbs"
down_revision: Union[str, None] = "0004_setor_uf_carga_atual"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALIQ = sa.Numeric(6, 5)


def upgrade() -> None:
    op.add_column(
        "sim_parametros",
        sa.Column(
            "aliquota_lucro_presumido_ibs_cbs",
            _ALIQ,
            nullable=False,
            server_default="0.27000",
        ),
    )
    op.alter_column(
        "sim_parametros",
        "aliquota_lucro_presumido",
        server_default="0.13330",
    )
    # Só realinha quem ainda está no valor combinado padrão antigo — não mexe
    # em tenants que já customizaram a alíquota em Configurações.
    op.execute(
        "UPDATE sim_parametros SET aliquota_lucro_presumido = 0.13330 "
        "WHERE aliquota_lucro_presumido = 0.16550"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE sim_parametros SET aliquota_lucro_presumido = 0.16550 "
        "WHERE aliquota_lucro_presumido = 0.13330"
    )
    op.alter_column(
        "sim_parametros",
        "aliquota_lucro_presumido",
        server_default="0.16550",
    )
    op.drop_column("sim_parametros", "aliquota_lucro_presumido_ibs_cbs")

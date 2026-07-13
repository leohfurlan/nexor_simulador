"""schema inicial do módulo simulador (tabelas sim_*) + seed de categorias

Revision ID: 0001_initial_sim
Revises:
Create Date: 2026-07-13

Cria as tabelas do módulo com prefixo `sim_` (para conviver no Postgres
compartilhado do Nexor Fiscal) e popula a tabela de referência de créditos.
Ao integrar, revise o tipo de `tenant_id` (aqui `sa.Uuid`) e adicione a
ForeignKey para `tenants.id` conforme a convenção do host.
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_sim"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALIQ = sa.Numeric(6, 5)
_MOEDA = sa.Numeric(10, 2)

# (nome, elegibilidade, gera_credito, observacao) — igual a app/seeds.py
_CATEGORIAS = [
    ("Matérias-Primas e Insumos", "Permitido", True, None),
    ("Bens de Capital", "Permitido", True, "Crédito parcelado"),
    ("Energia/Telecom", "Permitido", True, None),
    ("Vale-Transporte/Alimentação", "Permitido", True, None),
    ("Planos de Saúde", "Condicionado", True, "Crédito condicionado a requisitos"),
    ("Uso/Consumo Pessoal", "Não permitido", False, None),
    ("Operações Isentas/Imunes", "Não permitido", False, None),
    ("Ativo Imobilizado", "Permitido", True, "Crédito parcelado"),
    ("Insumos de Escritório", "Permitido", True, None),
    ("Aluguéis de Imóveis PJ", "Permitido", True, None),
    ("Softwares/Licenças", "Permitido", True, None),
    ("Serviços de Terceiros", "Permitido", True, None),
    ("Folha de Pagamento", "Não permitido", False, None),
]


def upgrade() -> None:
    op.create_table(
        "sim_categorias_despesa",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("elegibilidade_credito", sa.String(length=20), nullable=False),
        sa.Column("gera_credito", sa.Boolean(), nullable=False),
        sa.Column("observacao", sa.String(length=200), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )

    op.create_table(
        "sim_empresas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("cnpj", sa.String(length=18), nullable=True),
        sa.Column("atividade", sa.String(length=200), nullable=True),
        sa.Column("exige_credito_cliente", sa.Boolean(), nullable=False),
        sa.Column("regime_atual", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sim_empresas_tenant_id", "sim_empresas", ["tenant_id"])

    op.create_table(
        "sim_lancamentos_mensais",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=False),
        sa.Column("competencia", sa.String(length=7), nullable=False),
        sa.Column("faturamento", sa.Numeric(14, 2), nullable=False),
        sa.Column("despesas_com_credito", sa.Numeric(14, 2), nullable=False),
        sa.Column("das_padrao_apurado", sa.Numeric(14, 2), nullable=True),
        sa.Column("rbt12", sa.Numeric(16, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["sim_empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "competencia", name="uq_sim_lancamento_competencia"),
    )
    op.create_index("ix_sim_lancamentos_mensais_tenant_id", "sim_lancamentos_mensais", ["tenant_id"])
    op.create_index("ix_sim_lancamentos_mensais_empresa_id", "sim_lancamentos_mensais", ["empresa_id"])

    op.create_table(
        "sim_parametros",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=True),
        sa.Column("aliquota_cbs", _ALIQ, nullable=False),
        sa.Column("aliquota_ibs", _ALIQ, nullable=False),
        sa.Column("aliquota_hibrido_total", _ALIQ, nullable=False),
        sa.Column("aliquota_credito_despesa", _ALIQ, nullable=False),
        sa.Column("aliquota_lucro_presumido", _ALIQ, nullable=False),
        sa.Column("honorario_hibrido", _MOEDA, nullable=False),
        sa.Column("honorario_padrao", _MOEDA, nullable=False),
        sa.Column("honorario_lucro_presumido", _MOEDA, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["sim_empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sim_parametros_tenant_id", "sim_parametros", ["tenant_id"])
    op.create_index("ix_sim_parametros_empresa_id", "sim_parametros", ["empresa_id"])

    # Seed da tabela de referência (13 categorias).
    categorias = sa.table(
        "sim_categorias_despesa",
        sa.column("id", sa.Uuid()),
        sa.column("nome", sa.String()),
        sa.column("elegibilidade_credito", sa.String()),
        sa.column("gera_credito", sa.Boolean()),
        sa.column("observacao", sa.String()),
        sa.column("ordem", sa.Integer()),
    )
    op.bulk_insert(
        categorias,
        [
            {
                "id": uuid.uuid4(),
                "nome": nome,
                "elegibilidade_credito": elegib,
                "gera_credito": gera,
                "observacao": obs,
                "ordem": i,
            }
            for i, (nome, elegib, gera, obs) in enumerate(_CATEGORIAS, start=1)
        ],
    )


def downgrade() -> None:
    op.drop_table("sim_parametros")
    op.drop_table("sim_lancamentos_mensais")
    op.drop_table("sim_empresas")
    op.drop_table("sim_categorias_despesa")

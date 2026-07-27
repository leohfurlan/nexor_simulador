"""Bootstrap de banco (dev) + seed dos dados de referência (PRD seção 5).

Standalone: `python -m app.seeds` cria as tabelas (create_all) e popula as 13
categorias de despesa + os parâmetros padrão do tenant de dev. Idempotente.

Na integração ao Nexor Fiscal, o schema vem de uma migration Alembic e o seed
das categorias roda como data migration; os parâmetros são criados por tenant.
"""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import func, select

from app.config import settings
from app.database import Base, async_session_maker, engine
from app.models import (
    CONDICIONADO,
    NAO_PERMITIDO,
    PERMITIDO,
    CategoriaDespesa,
    Parametros,
)

# (nome, elegibilidade, gera_credito, observacao)
_CATEGORIAS: list[tuple[str, str, bool, str | None]] = [
    ("Matérias-Primas e Insumos", PERMITIDO, True, None),
    ("Bens de Capital", PERMITIDO, True, "Crédito parcelado"),
    ("Energia/Telecom", PERMITIDO, True, None),
    ("Vale-Transporte/Alimentação", PERMITIDO, True, None),
    ("Planos de Saúde", CONDICIONADO, True, "Crédito condicionado a requisitos"),
    ("Uso/Consumo Pessoal", NAO_PERMITIDO, False, None),
    ("Operações Isentas/Imunes", NAO_PERMITIDO, False, None),
    ("Ativo Imobilizado", PERMITIDO, True, "Crédito parcelado"),
    ("Insumos de Escritório", PERMITIDO, True, None),
    ("Aluguéis de Imóveis PJ", PERMITIDO, True, None),
    ("Softwares/Licenças", PERMITIDO, True, None),
    ("Serviços de Terceiros", PERMITIDO, True, None),
    ("Folha de Pagamento", NAO_PERMITIDO, False, None),
]


def _scalar_default_sql(column: sa.Column) -> str | None:
    """SQL literal do default Python da coluna, se for um valor escalar simples."""
    default = column.default
    if default is None or not getattr(default, "is_scalar", False):
        return None
    value = default.arg
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return None


def _sync_missing_columns(sync_conn) -> None:
    """Adiciona em bases já existentes as colunas que os models ganharam depois.

    `create_all` só cria tabelas ausentes — nunca altera uma tabela que já
    existe. Bases instaladas em máquinas de cliente (fora do fluxo Alembic)
    ficam presas no schema de quando foram criadas; sem isso, uma alíquota
    nova (ex.: `aliquota_lucro_presumido_ibs_cbs`) quebra com "no such column"
    até alguém apagar e recriar o banco manualmente — perdendo os dados.
    Só faz ADD COLUMN; nunca remove/renomeia nem toca em linhas existentes
    além de aplicar o default na coluna nova.
    """
    inspector = sa.inspect(sync_conn)
    tabelas_existentes = set(inspector.get_table_names())
    for tabela in Base.metadata.sorted_tables:
        if tabela.name not in tabelas_existentes:
            continue  # tabela nova inteira: create_all já resolve
        colunas_existentes = {c["name"] for c in inspector.get_columns(tabela.name)}
        for coluna in tabela.columns:
            if coluna.name in colunas_existentes:
                continue
            tipo_sql = coluna.type.compile(dialect=sync_conn.dialect)
            ddl = f"ALTER TABLE {tabela.name} ADD COLUMN {coluna.name} {tipo_sql}"
            if not coluna.nullable:
                default_sql = _scalar_default_sql(coluna)
                if default_sql is None:
                    # Sem default conhecido para preencher as linhas existentes:
                    # melhor pular e deixar visível nos logs do que travar o boot.
                    continue
                ddl += f" NOT NULL DEFAULT {default_sql}"
            sync_conn.execute(sa.text(ddl))


async def init_models() -> None:
    """Cria as tabelas (dev) e adiciona colunas novas em tabelas já existentes."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sync_missing_columns)


async def seed_categorias(session) -> int:
    """Insere as categorias ainda ausentes (idempotente por nome)."""
    existentes = set(
        (await session.execute(select(CategoriaDespesa.nome))).scalars().all()
    )
    novas = 0
    for ordem, (nome, elegib, gera, obs) in enumerate(_CATEGORIAS, start=1):
        if nome in existentes:
            continue
        session.add(
            CategoriaDespesa(
                nome=nome,
                elegibilidade_credito=elegib,
                gera_credito=gera,
                observacao=obs,
                ordem=ordem,
            )
        )
        novas += 1
    return novas


async def seed_parametros(session, tenant_id: uuid.UUID) -> bool:
    """Cria a linha global de parâmetros do tenant, se ainda não existir."""
    exists = await session.scalar(
        select(func.count())
        .select_from(Parametros)
        .where(Parametros.tenant_id == tenant_id, Parametros.empresa_id.is_(None))
    )
    if exists:
        return False
    session.add(Parametros(tenant_id=tenant_id))  # defaults = PRD seção 4
    return True


async def seed_all(tenant_id: uuid.UUID | None = None) -> None:
    tenant_id = tenant_id or settings.dev_tenant_id
    async with async_session_maker() as session:
        await seed_categorias(session)
        await seed_parametros(session, tenant_id)
        await session.commit()


async def _main() -> None:
    await init_models()
    await seed_all()
    print("Banco inicializado e seed aplicado (categorias + parâmetros padrão).")


if __name__ == "__main__":
    asyncio.run(_main())

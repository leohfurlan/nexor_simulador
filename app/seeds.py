"""Bootstrap de banco (dev) + seed dos dados de referência (PRD seção 5).

Standalone: `python -m app.seeds` cria as tabelas (create_all) e popula as 13
categorias de despesa + os parâmetros padrão do tenant de dev. Idempotente.

Na integração ao Nexor Fiscal, o schema vem de uma migration Alembic e o seed
das categorias roda como data migration; os parâmetros são criados por tenant.
"""
from __future__ import annotations

import asyncio
import uuid

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


async def init_models() -> None:
    """Cria as tabelas (dev). Em produção o schema vem do Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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

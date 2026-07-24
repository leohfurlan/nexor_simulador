"""Serviço de Empresa — CRUD tenant-scoped (padrão nfse_hub)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Empresa, LancamentoMensal, Parametros
from app.utils.numbers import parse_optional_decimal_br


def _margem_para_fracao(valor: object) -> Decimal | None:
    """Margem em PERCENTUAL ('20' ou '20,5') → fração (0.205). Vazio → None."""
    pct = parse_optional_decimal_br(valor)
    return None if pct is None else pct / Decimal("100")


async def list_empresas(session: AsyncSession, tenant_id: uuid.UUID, query: str = ""):
    stmt = select(Empresa).where(Empresa.tenant_id == tenant_id)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(or_(Empresa.nome.ilike(like), Empresa.cnpj.ilike(like)))
    stmt = stmt.order_by(Empresa.nome)
    return (await session.execute(stmt)).scalars().all()


async def get_empresa(
    session: AsyncSession, tenant_id: uuid.UUID, empresa_id: uuid.UUID
) -> Empresa | None:
    return await session.scalar(
        select(Empresa).where(Empresa.id == empresa_id, Empresa.tenant_id == tenant_id)
    )


async def create_empresa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    nome: str,
    cnpj: str | None = None,
    atividade: str | None = None,
    exige_credito_cliente: bool = False,
    regime_atual: str | None = None,
    margem_lucro_estimada: object = None,
    setor: str | None = None,
    uf: str | None = None,
) -> Empresa:
    empresa = Empresa(
        tenant_id=tenant_id,
        nome=nome.strip(),
        cnpj=(cnpj or "").strip() or None,
        atividade=(atividade or "").strip() or None,
        exige_credito_cliente=exige_credito_cliente,
        regime_atual=(regime_atual or "").strip() or None,
        margem_lucro_estimada=_margem_para_fracao(margem_lucro_estimada),
        setor=(setor or "").strip() or None,
        uf=((uf or "").strip().upper() or None),
    )
    session.add(empresa)
    await session.commit()
    await session.refresh(empresa)
    return empresa


async def update_empresa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    empresa_id: uuid.UUID,
    *,
    nome: str,
    cnpj: str | None,
    atividade: str | None,
    exige_credito_cliente: bool,
    regime_atual: str | None,
    margem_lucro_estimada: object = None,
    setor: str | None = None,
    uf: str | None = None,
) -> Empresa | None:
    empresa = await get_empresa(session, tenant_id, empresa_id)
    if empresa is None:
        return None
    empresa.nome = nome.strip()
    empresa.cnpj = (cnpj or "").strip() or None
    empresa.atividade = (atividade or "").strip() or None
    empresa.exige_credito_cliente = exige_credito_cliente
    empresa.regime_atual = (regime_atual or "").strip() or None
    empresa.margem_lucro_estimada = _margem_para_fracao(margem_lucro_estimada)
    empresa.setor = (setor or "").strip() or None
    empresa.uf = (uf or "").strip().upper() or None
    await session.commit()
    await session.refresh(empresa)
    return empresa


async def delete_empresa(
    session: AsyncSession, tenant_id: uuid.UUID, empresa_id: uuid.UUID
) -> bool:
    empresa = await get_empresa(session, tenant_id, empresa_id)
    if empresa is None:
        return False
    # Remoção explícita dos dependentes (SQLite não força ON DELETE por padrão).
    await session.execute(
        delete(LancamentoMensal).where(LancamentoMensal.empresa_id == empresa_id)
    )
    await session.execute(delete(Parametros).where(Parametros.empresa_id == empresa_id))
    await session.delete(empresa)
    await session.commit()
    return True

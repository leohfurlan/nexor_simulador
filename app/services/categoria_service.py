"""Serviço da tabela de referência de créditos (CategoriaDespesa)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CategoriaDespesa


async def list_categorias(session: AsyncSession) -> list[CategoriaDespesa]:
    stmt = select(CategoriaDespesa).order_by(CategoriaDespesa.ordem, CategoriaDespesa.nome)
    return list((await session.execute(stmt)).scalars().all())

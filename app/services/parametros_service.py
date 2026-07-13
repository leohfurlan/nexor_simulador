"""Serviço de Parametros — leitura/escrita da linha global do tenant.

Segue o padrão do Nexor Fiscal: funções async recebendo (session, tenant_id).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Parametros
from app.utils.numbers import parse_decimal_br

# Campos editáveis na tela de Configurações (PRD seção 4).
ALIQUOTA_FIELDS = (
    "aliquota_cbs",
    "aliquota_ibs",
    "aliquota_hibrido_total",
    "aliquota_credito_despesa",
    "aliquota_lucro_presumido",
)
HONORARIO_FIELDS = (
    "honorario_hibrido",
    "honorario_padrao",
    "honorario_lucro_presumido",
)
CAMPOS_EDITAVEIS = ALIQUOTA_FIELDS + HONORARIO_FIELDS


async def get_or_create_parametros(session: AsyncSession, tenant_id: uuid.UUID) -> Parametros:
    """Retorna os parâmetros globais do tenant, criando com defaults se faltar."""
    params = await session.scalar(
        select(Parametros).where(
            Parametros.tenant_id == tenant_id, Parametros.empresa_id.is_(None)
        )
    )
    if params is None:
        params = Parametros(tenant_id=tenant_id)
        session.add(params)
        await session.commit()
        await session.refresh(params)
    return params


async def update_parametros(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    aliquotas_pct: dict[str, str],
    honorarios: dict[str, str],
) -> Parametros:
    """Atualiza a linha global.

    `aliquotas_pct` chegam em PERCENTUAL (ex.: '16,30' = 16,30%) e são
    convertidas para fração (0.16300). `honorarios` chegam em R$.
    """
    params = await get_or_create_parametros(session, tenant_id)

    for campo in ALIQUOTA_FIELDS:
        if campo in aliquotas_pct:
            pct = parse_decimal_br(aliquotas_pct[campo])
            setattr(params, campo, pct / Decimal("100"))

    for campo in HONORARIO_FIELDS:
        if campo in honorarios:
            setattr(params, campo, parse_decimal_br(honorarios[campo]))

    await session.commit()
    await session.refresh(params)
    return params

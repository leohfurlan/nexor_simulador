"""Importa um cliente do Nexor Fiscal para o simulador (Empresa + lançamentos).

O faturamento mensal (emitidas autorizadas) vira `faturamento` de cada
LancamentoMensal. Despesas com crédito e DAS Padrão ficam em branco para o
usuário preencher — não há origem fiscal direta para eles.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc.engine import LP_PURO, SN_PADRAO
from app.models import Empresa
from app.services import lancamento_service

# regime_tributario (nfse_hub) → regime_atual (simulador)
_REGIME_MAP = {
    "simples_nacional": SN_PADRAO,
    "lucro_presumido": LP_PURO,
}


def _map_regime(regime_tributario: str | None) -> str | None:
    return _REGIME_MAP.get((regime_tributario or "").lower())


async def importar_cliente(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    cnpj: str,
    razao_social: str,
    regime_tributario: str | None,
    faturamento_mensal: list[dict],
) -> Empresa:
    """Cria/atualiza a Empresa (casada por CNPJ) e faz upsert dos lançamentos."""
    empresa = None
    if cnpj:
        empresa = await session.scalar(
            select(Empresa).where(Empresa.tenant_id == tenant_id, Empresa.cnpj == cnpj)
        )
    if empresa is None:
        empresa = Empresa(
            tenant_id=tenant_id,
            nome=razao_social.strip() or "(sem razão social)",
            cnpj=cnpj or None,
            regime_atual=_map_regime(regime_tributario),
        )
        session.add(empresa)
        await session.commit()
        await session.refresh(empresa)

    for item in faturamento_mensal:
        ano = int(item["competencia_ano"])
        mes = int(item["competencia_mes"])
        valor = item["faturamento"]
        await lancamento_service.upsert_lancamento(
            session,
            tenant_id,
            empresa.id,
            competencia=f"{ano:04d}-{mes:02d}",
            faturamento=str(valor),
            despesas_com_credito="",
            das_padrao_apurado="",
        )
    return empresa

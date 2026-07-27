"""Simulação rápida (item #10) — painel dividido com cálculo em tempo real.

Coluna esquerda: inputs. Coluna direita: resultado recalculado via HTMX a cada
alteração, sem recarregar a página e sem gravar nada no banco.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc.carga_atual import SETORES
from app.calc.engine import NOMES_REDUCAO, NOMES_REGIME
from app.calc.tributos_uf import UFS
from app.database import get_async_session
from app.deps import get_tenant_id
from app.services import simulacao_service
from app.services.parametros_service import get_or_create_parametros
from app.utils.templates import templates

router = APIRouter(prefix="/simular", tags=["simulador"])

REGIMES = list(NOMES_REGIME.items())
SETOR_OPCOES = list(SETORES.items())
UF_OPCOES = list(UFS)
REDUCAO_OPCOES = list(NOMES_REDUCAO.items())


def _form_ctx() -> dict:
    return {"regimes": REGIMES, "setores": SETOR_OPCOES, "ufs": UF_OPCOES,
            "reducoes": REDUCAO_OPCOES}


@router.get("", response_class=HTMLResponse)
async def pagina(request: Request):
    return templates.TemplateResponse(
        request, "simulador/index.html", {"active": "simular", **_form_ctx()}
    )


@router.post("", response_class=HTMLResponse)
async def calcular(
    request: Request,
    faturamento: str = Form(""),
    despesas_com_credito: str = Form(""),
    das_padrao_apurado: str = Form(""),
    margem_pct: str = Form(""),
    setor: str = Form(""),
    uf: str = Form(""),
    regime_atual: str = Form(""),
    reducao_ibs_cbs: str = Form(""),
    exige_credito_cliente: str | None = Form(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    params = await get_or_create_parametros(session, tenant_id)
    try:
        ctx = simulacao_service.simular_rapida(
            params.to_calc(),
            faturamento=faturamento,
            despesas_com_credito=despesas_com_credito,
            das_padrao_apurado=das_padrao_apurado,
            margem_pct=margem_pct,
            setor=setor or None,
            uf=uf or None,
            regime_atual=regime_atual or None,
            reducao_ibs_cbs=reducao_ibs_cbs or None,
            exige_credito_cliente=exige_credito_cliente is not None,
        )
    except ValueError:
        return templates.TemplateResponse(
            request, "simulador/partials/erro.html", {}
        )
    return templates.TemplateResponse(request, "simulador/partials/resultado.html", ctx)

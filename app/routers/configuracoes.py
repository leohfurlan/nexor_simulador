"""Tela 4 — Configurações (PRD seções 4 e 8).

Edita as alíquotas (em %) e honorários (em R$) globais do tenant. Espelha o
padrão do Nexor Fiscal: APIRouter + HTMX + templates.TemplateResponse.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.deps import get_tenant_id
from app.services.parametros_service import get_or_create_parametros, update_parametros
from app.utils.templates import templates

router = APIRouter(prefix="/configuracoes", tags=["configuracoes"])


def _display(params) -> dict:
    """Valores para o formulário: alíquotas em % (fração×100), honorários em R$."""
    return {
        "aliquota_cbs": float(params.aliquota_cbs) * 100,
        "aliquota_ibs": float(params.aliquota_ibs) * 100,
        "aliquota_hibrido_total": float(params.aliquota_hibrido_total) * 100,
        "aliquota_credito_despesa": float(params.aliquota_credito_despesa) * 100,
        "aliquota_lucro_presumido": float(params.aliquota_lucro_presumido) * 100,
        "honorario_hibrido": float(params.honorario_hibrido),
        "honorario_padrao": float(params.honorario_padrao),
        "honorario_lucro_presumido": float(params.honorario_lucro_presumido),
    }


@router.get("", response_class=HTMLResponse)
async def configuracoes_page(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    params = await get_or_create_parametros(session, tenant_id)
    return templates.TemplateResponse(
        request,
        "configuracoes/index.html",
        {"valores": _display(params), "active": "configuracoes"},
    )


@router.post("", response_class=HTMLResponse)
async def salvar_configuracoes(
    request: Request,
    aliquota_cbs: str = Form(...),
    aliquota_ibs: str = Form(...),
    aliquota_hibrido_total: str = Form(...),
    aliquota_credito_despesa: str = Form(...),
    aliquota_lucro_presumido: str = Form(...),
    honorario_hibrido: str = Form(...),
    honorario_padrao: str = Form(...),
    honorario_lucro_presumido: str = Form(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        params = await update_parametros(
            session,
            tenant_id,
            aliquotas_pct={
                "aliquota_cbs": aliquota_cbs,
                "aliquota_ibs": aliquota_ibs,
                "aliquota_hibrido_total": aliquota_hibrido_total,
                "aliquota_credito_despesa": aliquota_credito_despesa,
                "aliquota_lucro_presumido": aliquota_lucro_presumido,
            },
            honorarios={
                "honorario_hibrido": honorario_hibrido,
                "honorario_padrao": honorario_padrao,
                "honorario_lucro_presumido": honorario_lucro_presumido,
            },
        )
    except ValueError as exc:
        return HTMLResponse(
            f'<p class="rounded-md bg-rose-50 px-4 py-3 text-sm text-rose-700">'
            f"Não foi possível salvar: {exc}.</p>",
            status_code=400,
        )

    return templates.TemplateResponse(
        request,
        "configuracoes/partials/salvo.html",
        {"valores": _display(params)},
    )

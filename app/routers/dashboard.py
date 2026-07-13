"""Tela 2 — Dashboard (PRD seção 8). Seletor de empresa + painel por empresa."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.deps import get_tenant_id
from app.services import dashboard_service, empresa_service
from app.utils.templates import templates

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_class=HTMLResponse)
async def escolher(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    empresas = await empresa_service.list_empresas(session, tenant_id)
    return templates.TemplateResponse(
        request, "dashboard/index.html", {"empresas": empresas, "active": "dashboard"}
    )


@router.get("/{empresa_id}", response_class=HTMLResponse)
async def painel(
    empresa_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    empresa = await empresa_service.get_empresa(session, tenant_id, empresa_id)
    if empresa is None:
        return RedirectResponse(url="/dashboard", status_code=303)
    dados = await dashboard_service.build_dashboard(session, tenant_id, empresa)
    dados["active"] = "dashboard"
    return templates.TemplateResponse(request, "dashboard/detail.html", dados)

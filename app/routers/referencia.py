"""Tela 3 — Referência de créditos (PRD seção 8). Tabela informativa (read-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.categoria_despesa import CONDICIONADO, NAO_PERMITIDO, PERMITIDO
from app.services import categoria_service
from app.utils.templates import templates

router = APIRouter(prefix="/referencia", tags=["referencia"])

# Ícone por elegibilidade (rótulo textual acompanha — nunca só cor/ícone).
_ICONE = {PERMITIDO: "✅", CONDICIONADO: "⚠️", NAO_PERMITIDO: "❌"}


@router.get("", response_class=HTMLResponse)
async def referencia_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    categorias = await categoria_service.list_categorias(session)
    return templates.TemplateResponse(
        request,
        "referencia/index.html",
        {"categorias": categorias, "icone": _ICONE, "active": "referencia"},
    )

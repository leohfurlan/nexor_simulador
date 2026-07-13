"""Tela — Clientes do escritório (Nexor Fiscal): histórico + alimentar simulação.

Read-only sobre a base do nfse_hub; a única escrita é no simulador (ao importar
um cliente, cria Empresa + lançamentos). Falhas de conexão são exibidas de forma
amigável (o Postgres do nfse_hub pode estar fora do ar).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.deps import get_tenant_id
from app.integrations import nexor_fiscal
from app.services import importacao_cliente_service
from app.utils.templates import templates

router = APIRouter(prefix="/clientes", tags=["clientes"])

_ERRO_CONEXAO = (
    "Não foi possível conectar à base do Nexor Fiscal. "
    "Verifique se o Postgres do nfse_hub está no ar e se NEXOR_FISCAL_DATABASE_URL "
    "está configurada no .env."
)


def _resumo(clientes: list[dict]) -> dict:
    """Totais do escritório no período (sobre todos os clientes)."""
    return {
        "n_clientes": len(clientes),
        "com_nota": sum(1 for c in clientes if int(c["n_emitidas"]) + int(c["n_recebidas"]) > 0),
        "n_emitidas": sum(int(c["n_emitidas"]) for c in clientes),
        "v_emitidas": sum(float(c["v_emitidas"]) for c in clientes),
        "n_recebidas": sum(int(c["n_recebidas"]) for c in clientes),
        "v_recebidas": sum(float(c["v_recebidas"]) for c in clientes),
    }


# (chave de ordenação, reverse)
_SORTS = {
    "nome": (lambda c: (c["razao_social"] or "").lower(), False),
    "emitidas_valor": (lambda c: float(c["v_emitidas"]), True),
    "recebidas_valor": (lambda c: float(c["v_recebidas"]), True),
}


def _filtrar_ordenar(clientes: list[dict], q: str, sort: str) -> list[dict]:
    termo = (q or "").strip().lower()
    if termo:
        clientes = [
            c for c in clientes
            if termo in (c["razao_social"] or "").lower() or termo in (c["cnpj"] or "").lower()
        ]
    key, reverse = _SORTS.get(sort, _SORTS["nome"])
    return sorted(clientes, key=key, reverse=reverse)


@router.get("", response_class=HTMLResponse)
async def listar(
    request: Request,
    q: str = "",
    sort: str = "nome",
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    ctx = {"active": "clientes", "desde": settings.nexor_fiscal_desde_ano,
           "configurado": nexor_fiscal.is_configured(), "q": q, "sort": sort}
    if not nexor_fiscal.is_configured():
        return templates.TemplateResponse(request, "clientes/index.html", ctx)
    try:
        ctx["tenant_nome"] = await nexor_fiscal.get_tenant_nome(tenant_id)
        clientes = await nexor_fiscal.list_clientes(tenant_id, settings.nexor_fiscal_desde_ano)
        ctx["resumo"] = _resumo(clientes)
        ctx["clientes"] = _filtrar_ordenar(clientes, q, sort)
    except Exception:
        ctx["erro"] = _ERRO_CONEXAO
        return templates.TemplateResponse(request, "clientes/index.html", ctx)

    # Busca/ordenação ao vivo trocam só a lista; navegação normal traz a página.
    if request.headers.get("HX-Request") and not request.headers.get("HX-Boosted"):
        return templates.TemplateResponse(request, "clientes/partials/list.html", ctx)
    return templates.TemplateResponse(request, "clientes/index.html", ctx)


@router.get("/{cnpj_id}", response_class=HTMLResponse)
async def detalhe(
    cnpj_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    ctx = {"active": "clientes", "desde": settings.nexor_fiscal_desde_ano,
           "configurado": nexor_fiscal.is_configured(), "cnpj_id": str(cnpj_id)}
    if not nexor_fiscal.is_configured():
        return templates.TemplateResponse(request, "clientes/detail.html", ctx)
    try:
        cliente = await nexor_fiscal.get_cliente(tenant_id, cnpj_id)
        if cliente is None:
            return RedirectResponse(url="/clientes", status_code=303)
        ctx["cliente"] = cliente
        ctx["faturamento"] = await nexor_fiscal.faturamento_mensal(
            tenant_id, cnpj_id, settings.nexor_fiscal_desde_ano
        )
        ctx["notas"] = await nexor_fiscal.list_notas(
            tenant_id, cnpj_id, settings.nexor_fiscal_desde_ano
        )
    except Exception:
        ctx["erro"] = _ERRO_CONEXAO
    return templates.TemplateResponse(request, "clientes/detail.html", ctx)


@router.post("/{cnpj_id}/importar", response_class=HTMLResponse)
async def importar(
    cnpj_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    if not nexor_fiscal.is_configured():
        return RedirectResponse(url="/clientes", status_code=303)
    cliente = await nexor_fiscal.get_cliente(tenant_id, cnpj_id)
    if cliente is None:
        return RedirectResponse(url="/clientes", status_code=303)
    faturamento = await nexor_fiscal.faturamento_mensal(
        tenant_id, cnpj_id, settings.nexor_fiscal_desde_ano
    )
    empresa = await importacao_cliente_service.importar_cliente(
        session,
        tenant_id,
        cnpj=cliente["cnpj"],
        razao_social=cliente["razao_social"],
        regime_tributario=cliente.get("regime_tributario"),
        faturamento_mensal=faturamento,
    )
    # Leva direto ao dashboard da empresa importada.
    return RedirectResponse(url=f"/dashboard/{empresa.id}", status_code=303)

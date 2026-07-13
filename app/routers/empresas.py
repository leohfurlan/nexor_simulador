"""Tela 1 — Empresas: cadastro + tabela mensal editável + import CSV (PRD seção 8).

CRUD da empresa via POST/redirect (navegação normal); a tabela mensal é
interativa via HTMX (salvar linha → recalcula os 4 regimes → devolve a seção).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc.engine import NOMES_REGIME
from app.database import get_async_session
from app.deps import get_tenant_id
from app.services import empresa_service, lancamento_service
from app.utils.templates import templates

router = APIRouter(prefix="/empresas", tags=["empresas"])

# Regimes selecionáveis como "regime atual" da empresa.
REGIMES = list(NOMES_REGIME.items())


@router.get("", response_class=HTMLResponse)
async def listar(
    request: Request,
    q: str = "",
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    empresas = await empresa_service.list_empresas(session, tenant_id, q)
    ctx = {"empresas": empresas, "q": q, "active": "empresas", "regimes": REGIMES}
    if request.headers.get("HX-Request") and not request.headers.get("HX-Boosted"):
        return templates.TemplateResponse(request, "empresas/partials/list_items.html", ctx)
    return templates.TemplateResponse(request, "empresas/list.html", ctx)


@router.post("", response_class=HTMLResponse)
async def criar(
    request: Request,
    nome: str = Form(...),
    cnpj: str = Form(""),
    atividade: str = Form(""),
    exige_credito_cliente: str | None = Form(None),
    regime_atual: str = Form(""),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    if not nome.strip():
        empresas = await empresa_service.list_empresas(session, tenant_id)
        return templates.TemplateResponse(
            request,
            "empresas/list.html",
            {"empresas": empresas, "q": "", "active": "empresas", "regimes": REGIMES,
             "erro": "Informe o nome da empresa."},
            status_code=400,
        )
    empresa = await empresa_service.create_empresa(
        session, tenant_id,
        nome=nome, cnpj=cnpj, atividade=atividade,
        exige_credito_cliente=exige_credito_cliente is not None,
        regime_atual=regime_atual,
    )
    return RedirectResponse(url=f"/empresas/{empresa.id}", status_code=303)


@router.get("/{empresa_id}", response_class=HTMLResponse)
async def detalhe(
    empresa_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    empresa = await empresa_service.get_empresa(session, tenant_id, empresa_id)
    if empresa is None:
        return RedirectResponse(url="/empresas", status_code=303)
    rows = await lancamento_service.compute_rows(session, tenant_id, empresa)
    return templates.TemplateResponse(
        request,
        "empresas/detail.html",
        {"empresa": empresa, "rows": rows, "active": "empresas", "regimes": REGIMES},
    )


@router.post("/{empresa_id}/editar", response_class=HTMLResponse)
async def editar(
    empresa_id: uuid.UUID,
    nome: str = Form(...),
    cnpj: str = Form(""),
    atividade: str = Form(""),
    exige_credito_cliente: str | None = Form(None),
    regime_atual: str = Form(""),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    await empresa_service.update_empresa(
        session, tenant_id, empresa_id,
        nome=nome, cnpj=cnpj, atividade=atividade,
        exige_credito_cliente=exige_credito_cliente is not None,
        regime_atual=regime_atual,
    )
    return RedirectResponse(url=f"/empresas/{empresa_id}", status_code=303)


@router.post("/{empresa_id}/excluir", response_class=HTMLResponse)
async def excluir(
    empresa_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    await empresa_service.delete_empresa(session, tenant_id, empresa_id)
    return RedirectResponse(url="/empresas", status_code=303)


# --- Tabela mensal (HTMX) ----------------------------------------------------

async def _render_secao(request, session, tenant_id, empresa, *, mensagem=None, erros=None):
    rows = await lancamento_service.compute_rows(session, tenant_id, empresa)
    return templates.TemplateResponse(
        request,
        "empresas/partials/lancamentos_section.html",
        {"empresa": empresa, "rows": rows, "mensagem": mensagem, "erros": erros or []},
    )


@router.post("/{empresa_id}/lancamentos", response_class=HTMLResponse)
async def salvar_lancamento(
    empresa_id: uuid.UUID,
    request: Request,
    competencia: str = Form(...),
    faturamento: str = Form(""),
    despesas_com_credito: str = Form(""),
    das_padrao_apurado: str = Form(""),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    empresa = await empresa_service.get_empresa(session, tenant_id, empresa_id)
    if empresa is None:
        return HTMLResponse("Empresa não encontrada.", status_code=404)
    try:
        await lancamento_service.upsert_lancamento(
            session, tenant_id, empresa_id,
            competencia=competencia, faturamento=faturamento,
            despesas_com_credito=despesas_com_credito,
            das_padrao_apurado=das_padrao_apurado,
        )
    except ValueError as exc:
        return await _render_secao(
            request, session, tenant_id, empresa, erros=[str(exc)]
        )
    return await _render_secao(request, session, tenant_id, empresa)


@router.post("/{empresa_id}/lancamentos/{competencia}/excluir", response_class=HTMLResponse)
async def excluir_lancamento(
    empresa_id: uuid.UUID,
    competencia: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    empresa = await empresa_service.get_empresa(session, tenant_id, empresa_id)
    if empresa is None:
        return HTMLResponse("Empresa não encontrada.", status_code=404)
    await lancamento_service.delete_lancamento(session, tenant_id, empresa_id, competencia)
    return await _render_secao(request, session, tenant_id, empresa)


@router.post("/{empresa_id}/importar", response_class=HTMLResponse)
async def importar_csv(
    empresa_id: uuid.UUID,
    request: Request,
    arquivo: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
):
    empresa = await empresa_service.get_empresa(session, tenant_id, empresa_id)
    if empresa is None:
        return HTMLResponse("Empresa não encontrada.", status_code=404)
    content = await arquivo.read()
    importadas, erros, nota = await lancamento_service.import_file(
        session, tenant_id, empresa_id, arquivo.filename, content
    )
    mensagem = f"{importadas} competência(s) importada(s)"
    mensagem += f" da {nota}." if nota else "."
    return await _render_secao(request, session, tenant_id, empresa, mensagem=mensagem, erros=erros)

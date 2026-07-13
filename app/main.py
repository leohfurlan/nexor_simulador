"""Aplicação FastAPI standalone do Simulador Tributário (módulo do Nexor Fiscal).

Espelha o padrão do nfse_hub (app/main.py): monta /static, inclui routers.
No modo debug, o lifespan cria as tabelas e aplica o seed — assim o app
"sobe e funciona" sem passos manuais durante o desenvolvimento.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.integrations import nexor_fiscal
from app.routers import clientes, configuracoes, dashboard, empresas, referencia
from app.seeds import init_models, seed_all
from app.utils.templates import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.debug:
        await init_models()
        await seed_all()
    yield


app = FastAPI(
    title="Nexor · Simulador Tributário",
    description="Comparador de regimes tributários (Reforma Tributária / IBS-CBS)",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(clientes.router)
app.include_router(empresas.router)
app.include_router(dashboard.router)
app.include_router(referencia.router)
app.include_router(configuracoes.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    # Página inicial: introdução ao sistema e como começar a usar.
    return templates.TemplateResponse(
        request,
        "inicio/index.html",
        {"active": "inicio", "configurado": nexor_fiscal.is_configured()},
    )

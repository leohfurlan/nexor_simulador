"""Testes da Simulação rápida (item #10) — cálculo single-shot via HTMX."""
import asyncio
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_DB_PATH = _tmp.name
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + _DB_PATH.replace("\\", "/")
os.environ["DEBUG"] = "true"
os.environ["SQL_ECHO"] = "false"

from starlette.testclient import TestClient  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


def teardown_module(module):
    asyncio.run(engine.dispose())
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


def test_pagina_simulador_carrega():
    with TestClient(app) as client:
        r = client.get("/simular")
        assert r.status_code == 200
        assert "Simulação rápida" in r.text
        assert 'hx-post="/simular"' in r.text  # painel reativo


def test_simulacao_calcula_regimes_e_carga_atual():
    with TestClient(app) as client:
        r = client.post("/simular", data={
            "faturamento": "98000,00",
            "setor": "servico",
            "regime_atual": "lp_puro",
            "margem_pct": "20",
            "das_padrao_apurado": "8000,00",
        })
        assert r.status_code == 200
        assert "Regime recomendado" in r.text
        # Serviço → ISS na carga atual; painel antes × depois presente.
        assert "Carga atual (pré-reforma) estimada" in r.text
        assert "Serviços" in r.text and "ISS" in r.text
        # Com margem e DAS, os 5 regimes ficam disponíveis (Lucro Real incluso).
        assert "Lucro Real" in r.text


def test_simulacao_sem_faturamento_pede_dados():
    with TestClient(app) as client:
        r = client.post("/simular", data={"faturamento": ""})
        assert r.status_code == 200
        assert "Preencha o" in r.text  # estado vazio


def test_simulacao_valor_invalido_mostra_erro():
    with TestClient(app) as client:
        r = client.post("/simular", data={"faturamento": "abc"})
        assert r.status_code == 200
        assert "Não consegui interpretar" in r.text

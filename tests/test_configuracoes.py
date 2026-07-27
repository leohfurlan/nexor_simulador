"""Teste da tela de Configurações (Fase 2) via TestClient, com banco temporário.

Define DATABASE_URL antes de importar o app (o engine é criado no import).
"""
import asyncio
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_DB_PATH = _tmp.name
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + _DB_PATH.replace("\\", "/")
os.environ["DEBUG"] = "true"       # lifespan cria tabelas + seed
os.environ["SQL_ECHO"] = "false"   # sem poluir a saída dos testes

from starlette.testclient import TestClient  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402

_FORM = {
    "aliquota_cbs": "2.70",
    "aliquota_ibs": "8.80",
    "aliquota_hibrido_total": "16.30",
    "aliquota_credito_despesa": "27.00",
    "aliquota_lucro_presumido": "13.33",
    "aliquota_lucro_presumido_ibs_cbs": "27.00",
    "aliquota_lucro_real_irpj_csll": "34.00",
    "aliquota_pis": "0.65",
    "aliquota_cofins": "3.00",
    "aliquota_iss": "5.00",
    "aliquota_icms": "18.00",
    "honorario_hibrido": "550.00",
    "honorario_padrao": "350.00",
    "honorario_lucro_presumido": "750.00",
    "honorario_lucro_real": "900.00",
}


def teardown_module(module):
    asyncio.run(engine.dispose())
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


def test_configuracoes_crud():
    with TestClient(app) as client:
        # GET renderiza os defaults (PRD seção 4)
        r = client.get("/configuracoes")
        assert r.status_code == 200
        assert "16.30" in r.text and "550.00" in r.text

        # POST salva um honorário alterado
        r = client.post("/configuracoes", data=dict(_FORM, honorario_hibrido="999.99"))
        assert r.status_code == 200
        assert "salvas" in r.text

        # GET reflete a alteração persistida
        r = client.get("/configuracoes")
        assert "999.99" in r.text


def test_configuracoes_valor_invalido_retorna_400():
    with TestClient(app) as client:
        r = client.post("/configuracoes", data=dict(_FORM, aliquota_cbs="abc"))
        assert r.status_code == 400

"""Testes do Dashboard (Fase 4) e da Referência de créditos (Fase 5)."""
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


def _empresa_com_lancamentos(client):
    r = client.post(
        "/empresas",
        data={"nome": "Dash Co", "regime_atual": "lp_puro"},
        follow_redirects=False,
    )
    url = r.headers["location"]
    for comp, fat, desp, das in [
        ("2026-01", "25716,90", "3000,00", "2110,71"),
        ("2026-02", "25000,00", "3000,00", "2050,00"),
    ]:
        client.post(
            f"{url}/lancamentos",
            data={"competencia": comp, "faturamento": fat,
                  "despesas_com_credito": desp, "das_padrao_apurado": das},
        )
    return url  # /empresas/{id}


def test_dashboard_renderiza_com_recomendacao_e_grafico():
    with TestClient(app) as client:
        empresa_url = _empresa_com_lancamentos(client)
        empresa_id = empresa_url.rsplit("/", 1)[1]

        # Seletor lista a empresa
        r = client.get("/dashboard")
        assert r.status_code == 200
        assert "Dash Co" in r.text

        # Painel da empresa
        r = client.get(f"/dashboard/{empresa_id}")
        assert r.status_code == 200
        assert "Regime recomendado" in r.text
        assert "Simples Nacional Padrão" in r.text     # menor custo (honorário 350)
        assert "economia" in r.text.lower()            # regime_atual=LP → economia > 0
        assert "chartPct" in r.text and "chartCusto" in r.text  # gráficos presentes


def test_referencia_lista_categorias():
    with TestClient(app) as client:
        r = client.get("/referencia")
        assert r.status_code == 200
        assert "Matérias-Primas e Insumos" in r.text
        assert "Folha de Pagamento" in r.text
        assert "Permitido" in r.text and "Não permitido" in r.text

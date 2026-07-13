"""Fluxo da Tela 1 (Fase 3): empresa CRUD + tabela mensal HTMX + import CSV."""
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


def _criar_empresa(client, nome="Empresa Teste", exige=True):
    data = {"nome": nome, "cnpj": "12.345.678/0001-90", "atividade": "Serviços"}
    if exige:
        data["exige_credito_cliente"] = "1"
    r = client.post("/empresas", data=data, follow_redirects=False)
    assert r.status_code == 303
    location = r.headers["location"]
    assert location.startswith("/empresas/")
    return location  # /empresas/{id}


def test_fluxo_empresa_e_lancamentos():
    with TestClient(app) as client:
        url = _criar_empresa(client)

        # Detalhe abre com a seção de lançamentos
        r = client.get(url)
        assert r.status_code == 200
        assert "Lançamentos mensais" in r.text

        # Adiciona o caso de referência do PRD → recalcula os 4 regimes
        r = client.post(
            f"{url}/lancamentos",
            data={
                "competencia": "2026-01",
                "faturamento": "25716,90",
                "despesas_com_credito": "3000,00",
                "das_padrao_apurado": "2110,71",
            },
        )
        assert r.status_code == 200
        assert "2.110,71" in r.text   # SN Padrão
        assert "3.381,85" in r.text   # SN Híbrido
        assert "4.256,15" in r.text   # LP puro

        # Sem DAS → SN Padrão indisponível ("—") para aquele mês
        r = client.post(
            f"{url}/lancamentos",
            data={"competencia": "02/2026", "faturamento": "10000", "despesas_com_credito": "0", "das_padrao_apurado": ""},
        )
        assert r.status_code == 200

        # Competência inválida → mensagem de erro na seção
        r = client.post(
            f"{url}/lancamentos",
            data={"competencia": "13-2026", "faturamento": "1", "despesas_com_credito": "0", "das_padrao_apurado": ""},
        )
        assert r.status_code == 200
        assert "inválida" in r.text

        # Import CSV (delimitador ; e decimais pt-BR; ISO e MM/YYYY)
        csv = (
            "competencia;faturamento;despesas_com_credito;das_padrao_apurado\n"
            "2026-03;10000,00;1000,00;800,00\n"
            "04/2026;5000,00;500,00;\n"
        ).encode("utf-8")
        r = client.post(f"{url}/importar", files={"arquivo": ("dados.csv", csv, "text/csv")})
        assert r.status_code == 200
        assert "2 competência" in r.text

        # Excluir um lançamento
        r = client.post(f"{url}/lancamentos/2026-01/excluir")
        assert r.status_code == 200

        # Excluir a empresa
        r = client.post(f"{url}/excluir", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/empresas"


def test_criar_empresa_sem_nome_retorna_400():
    with TestClient(app) as client:
        r = client.post("/empresas", data={"nome": "  "}, follow_redirects=False)
        assert r.status_code == 400


def test_import_xlsx_com_cabecalhos_reais():
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lançamentos"
    ws.append(["Mês", "Faturamento Mensal ($)", "Despesas com Crédito ($)", "DAS Padrão"])
    ws.append(["jan/2026", 20000, 2500, 1600])
    ws.append(["fev/2026", 22000, 2500, 1750])
    ws.append(["jun/2026", 0, 0, 0])  # mês sem movimento → ignorado
    buf = io.BytesIO()
    wb.save(buf)

    with TestClient(app) as client:
        url = _criar_empresa(client, nome="Import XLSX", exige=False)
        r = client.post(
            f"{url}/importar",
            files={
                "arquivo": (
                    "planilha.xlsx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert r.status_code == 200
        assert "2 competência" in r.text   # jun (zerado) foi ignorado
        assert "da aba" in r.text
        assert "3.310,00" in r.text         # LP calculado (20000×16,55%), pt-BR

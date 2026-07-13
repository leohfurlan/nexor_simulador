"""Integração com a base do Nexor Fiscal (read-only) + importar cliente.

Usa um Postgres-substituto em SQLite (mesmos nomes de tabela/coluna do nfse_hub)
com dados FICTÍCIOS, para exercitar o conector e o fluxo sem o banco real.
"""
import asyncio
import os
import sqlite3
import tempfile

_sim = tempfile.NamedTemporaryFile(suffix="_sim.db", delete=False); _sim.close()
_src = tempfile.NamedTemporaryFile(suffix="_src.db", delete=False); _src.close()

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + _sim.name.replace("\\", "/")
os.environ["NEXOR_FISCAL_DATABASE_URL"] = "sqlite+aiosqlite:///" + _src.name.replace("\\", "/")
os.environ["DEBUG"] = "true"
os.environ["SQL_ECHO"] = "false"

OFFICE = "8b5dbf59-dd85-4c63-9e94-0f792309b10b"
CID_A = "11111111-1111-1111-1111-111111111111"
CID_B = "22222222-2222-2222-2222-222222222222"


def _build_source():
    con = sqlite3.connect(_src.name)
    c = con.cursor()
    c.execute("create table tenants(id text, name text)")
    c.execute("create table cnpjs(id text, tenant_id text, cnpj text, razao_social text, "
              "nome_fantasia text, regime_tributario text, status text)")
    c.execute("create table nfse_documents(id text, tenant_id text, cnpj_id text, direcao text, "
              "status text, numero_nota text, competencia_ano int, competencia_mes int, "
              "issued_at text, valor_servicos real, tomador_razao_social text, prestador_razao_social text)")
    c.execute("insert into tenants values(?,?)", (OFFICE, "JS APOIO CONTABIL"))
    c.executemany("insert into cnpjs values(?,?,?,?,?,?,?)", [
        (CID_A, OFFICE, "11111111000191", "Cliente Alfa Ltda", None, "simples_nacional", "active"),
        (CID_B, OFFICE, "22222222000191", "Cliente Beta ME", None, "lucro_presumido", "active"),
    ])
    n = 0
    def nota(cid, direcao, status, ano, mes, valor, tom=None, pres=None):
        nonlocal n; n += 1
        c.execute("insert into nfse_documents values(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (f"n{n}", OFFICE, cid, direcao, status, str(n), ano, mes, None, valor, tom, pres))
    nota(CID_A, "emitida", "autorizada", 2025, 1, 10000, tom="Tomador X")
    nota(CID_A, "emitida", "autorizada", 2025, 2, 12000, tom="Tomador Y")
    nota(CID_A, "emitida", "rascunho",  2025, 3, 5000,  tom="Tomador Z")   # não entra no faturamento
    nota(CID_A, "recebida", "autorizada", 2025, 1, 3000, pres="Prestador W")
    nota(CID_A, "emitida", "autorizada", 2024, 12, 9999, tom="Antigo")     # fora do período (2025+)
    nota(CID_B, "emitida", "autorizada", 2025, 1, 20000, tom="Tomador K")
    con.commit(); con.close()


_build_source()

from starlette.testclient import TestClient  # noqa: E402

from app.database import engine  # noqa: E402
from app.integrations import nexor_fiscal  # noqa: E402
from app.main import app  # noqa: E402


def teardown_module(module):
    asyncio.run(engine.dispose())
    if nexor_fiscal._engine is not None:
        asyncio.run(nexor_fiscal._engine.dispose())
    for f in (_sim.name, _src.name):
        try:
            os.unlink(f)
        except OSError:
            pass


def test_lista_clientes_com_resumo():
    with TestClient(app) as client:
        r = client.get("/clientes")
        assert r.status_code == 200
        assert "JS APOIO CONTABIL" in r.text
        assert "Cliente Alfa Ltda" in r.text and "Cliente Beta ME" in r.text
        assert "3.000,00" in r.text     # recebidas de Alfa (2025)
        assert "9.999" not in r.text    # nota de 2024 fora do período
        assert "47.000,00" in r.text    # resumo: total emitidas (27k Alfa + 20k Beta)


def test_busca_filtra_clientes():
    with TestClient(app) as client:
        r = client.get("/clientes", params={"q": "Beta"})
        assert r.status_code == 200
        assert "Cliente Beta ME" in r.text
        assert "Cliente Alfa Ltda" not in r.text


def test_detalhe_faturamento_mensal():
    with TestClient(app) as client:
        r = client.get(f"/clientes/{CID_A}")
        assert r.status_code == 200
        # faturamento = emitidas autorizadas de 2025 (jan 10k, fev 12k; mar é rascunho)
        assert "10.000,00" in r.text and "12.000,00" in r.text


def test_importar_cliente_alimenta_simulacao():
    with TestClient(app) as client:
        r = client.post(f"/clientes/{CID_A}/importar", follow_redirects=False)
        assert r.status_code == 303
        dash = r.headers["location"]
        assert dash.startswith("/dashboard/")
        # Dashboard da empresa importada: faturamento total = 10k + 12k = 22k
        r = client.get(dash)
        assert r.status_code == 200
        assert "22.000,00" in r.text

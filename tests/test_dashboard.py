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


def test_dashboard_tem_repasse_pdf_e_copiar_resumo():
    """Regime atual (LP) mais caro que o recomendado (SN Padrão) → sugestão de
    repasse de preço com folga; botões de exportação presentes."""
    with TestClient(app) as client:
        empresa_url = _empresa_com_lancamentos(client)
        empresa_id = empresa_url.rsplit("/", 1)[1]

        r = client.get(f"/dashboard/{empresa_id}")
        assert r.status_code == 200
        assert "Sugestão de repasse de preço" in r.text
        assert "folga" in r.text.lower()          # recomendado é mais barato
        # Sem margem cadastrada: convite a informá-la.
        assert "para ver o impacto na margem" in r.text
        assert "Gerar PDF" in r.text
        assert "Copiar resumo" in r.text
        assert "const RESUMO" in r.text            # resumo embutido p/ clipboard
        # Banner de alíquotas provisórias presente no dashboard e em configurações.
        assert "Alíquotas provisórias" in r.text
        assert "Alíquotas provisórias" in client.get("/configuracoes").text
        # Linha do tempo da transição (2026–2033).
        assert "Linha do tempo da Reforma" in r.text
        assert "2033" in r.text and "Reforma plena" in r.text


def test_repasse_usa_margem_de_lucro_estimada():
    """Com margem cadastrada, o repasse projeta a margem sem repasse. Regime
    recomendado (SN Padrão) reduz a carga → margem projetada sobe."""
    with TestClient(app) as client:
        r = client.post(
            "/empresas",
            data={"nome": "Margem Co", "regime_atual": "lp_puro",
                  "margem_lucro_estimada": "20"},
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
        eid = url.rsplit("/", 1)[1]

        # Badge da margem no cadastro.
        assert "margem 20,00%" in client.get(f"/empresas/{eid}").text

        r = client.get(f"/dashboard/{eid}")
        assert r.status_code == 200
        assert "Margem estimada" in r.text
        # 20% + queda de carga (~5,13pp) → ~25,13% sem repasse.
        assert "20,00%" in r.text and "25,13%" in r.text
        assert "para ver o impacto na margem" not in r.text
        # Com margem, o Lucro Real passa a ser comparável (card presente).
        assert "Lucro Real" in r.text


def test_lucro_real_indisponivel_sem_margem():
    """Sem margem cadastrada, o Lucro Real aparece como indisponível (—),
    não distorcendo a recomendação."""
    with TestClient(app) as client:
        eid = _empresa(client, "Sem Margem Co", [
            ("2026-01", "25716,90", "3000,00", "2110,71"),
        ])
        r = client.get(f"/dashboard/{eid}")
        assert r.status_code == 200
        assert "Lucro Real" in r.text  # card existe
        # marcado como indisponível por falta de margem
        assert "informe" in r.text.lower()


def test_dashboard_mostra_carga_atual_por_setor():
    """Com setor informado, o Dashboard exibe a estimativa da carga atual e o
    comparativo antes × depois."""
    with TestClient(app) as client:
        r = client.post(
            "/empresas",
            data={"nome": "Setor Co", "regime_atual": "lp_puro",
                  "setor": "comercio", "uf": "SP"},
            follow_redirects=False,
        )
        url = r.headers["location"]
        client.post(
            f"{url}/lancamentos",
            data={"competencia": "2026-01", "faturamento": "10000,00",
                  "despesas_com_credito": "0,00", "das_padrao_apurado": "800,00"},
        )
        eid = url.rsplit("/", 1)[1]
        r = client.get(f"/dashboard/{eid}")
        assert r.status_code == 200
        assert "Carga atual (pré-reforma) estimada" in r.text
        assert "Comércio" in r.text and "ICMS" in r.text
        assert "Antes × depois" in r.text
        assert "1.800,00" in r.text  # ICMS SP 18% de 10.000


def test_linha_tempo_marca_ano_atual():
    import datetime as dt

    from app.services.reforma import linha_tempo

    marcos = linha_tempo(hoje=dt.date(2026, 7, 18))
    assert [m["ano"] for m in marcos] == [
        "2026", "2027", "2028", "2029", "2030", "2031", "2032", "2033"
    ]
    atuais = [m["ano"] for m in marcos if m["atual"]]
    assert atuais == ["2026"]
    # Fora do intervalo: nenhum ano marcado como atual.
    assert not any(m["atual"] for m in linha_tempo(hoje=dt.date(2040, 1, 1)))


def _empresa(client, nome, lancamentos):
    r = client.post(
        "/empresas",
        data={"nome": nome, "regime_atual": "lp_puro"},
        follow_redirects=False,
    )
    url = r.headers["location"]
    for comp, fat, desp, das in lancamentos:
        client.post(
            f"{url}/lancamentos",
            data={"competencia": comp, "faturamento": fat,
                  "despesas_com_credito": desp, "das_padrao_apurado": das},
        )
    return url.rsplit("/", 1)[1]


def test_sn_padrao_entra_na_simulacao_com_mes_sem_movimento_sem_das():
    """DAS informado em todos os meses com faturamento inclui o SN Padrão no
    acumulado, mesmo que haja mês sem movimento sem DAS (bug reportado pelo
    contador: "salvamos o DAS e não inclui na Simulação")."""
    with TestClient(app) as client:
        eid = _empresa(client, "SN Movimento Co", [
            ("2026-01", "25716,90", "3000,00", "2110,71"),
            ("2026-02", "25000,00", "3000,00", "2050,00"),
            ("2026-03", "0,00", "0,00", ""),  # mês sem movimento, DAS em branco
        ])
        r = client.get(f"/dashboard/{eid}")
        assert r.status_code == 200
        # SN Padrão comparável → não mostra o aviso de dado faltante.
        assert "informe o DAS Padrão dos meses com faturamento" not in r.text


def test_sn_padrao_fica_de_fora_quando_mes_com_faturamento_sem_das():
    """Se um mês COM faturamento não tem DAS, o SN Padrão continua fora do
    acumulado (o total seria subestimado — comparação injusta)."""
    with TestClient(app) as client:
        eid = _empresa(client, "SN Faltante Co", [
            ("2026-01", "25716,90", "3000,00", "2110,71"),
            ("2026-02", "25000,00", "3000,00", ""),  # tem faturamento, sem DAS
        ])
        r = client.get(f"/dashboard/{eid}")
        assert r.status_code == 200
        assert "informe o DAS Padrão dos meses com faturamento" in r.text


def test_dashboard_filtra_por_mes():
    """Simulação pode constar apenas o mês solicitado, em vez do período todo
    (pedido do contador)."""
    with TestClient(app) as client:
        eid = _empresa(client, "Filtro Mês Co", [
            ("2026-01", "25716,90", "3000,00", "2110,71"),
            ("2026-02", "25000,00", "3000,00", "2050,00"),
        ])
        # Período todo: 2 meses e faturamento somado.
        r = client.get(f"/dashboard/{eid}")
        assert r.status_code == 200
        assert "2 meses" in r.text
        assert "Simular" in r.text  # seletor de mês presente

        # Mês único: só a competência escolhida entra na simulação.
        r = client.get(f"/dashboard/{eid}?mes=2026-01")
        assert r.status_code == 200
        assert "jan/2026 · faturamento" in r.text
        assert "25.716,90" in r.text and "50.716,90" not in r.text

        # Competência inexistente é ignorada → volta ao período todo.
        r = client.get(f"/dashboard/{eid}?mes=2099-12")
        assert "2 meses" in r.text


def test_simular_mes_unico_com_das_so_daquele_mes():
    """Fluxo do contador: DAS lançado manualmente em um único mês. No período
    todo o SN Padrão fica parcial (com aviso guiando ao seletor); ao simular só
    aquele mês, o SN Padrão passa a ser comparável."""
    with TestClient(app) as client:
        eid = _empresa(client, "Mês Único Co", [
            ("2026-05", "114271,25", "0,00", ""),
            ("2026-06", "95571,25", "0,00", ""),
            ("2026-07", "65571,25", "0,00", "10688,11"),  # DAS só de julho
        ])
        # Período todo: SN Padrão parcial → aviso para escolher um mês.
        r = client.get(f"/dashboard/{eid}")
        assert r.status_code == 200
        assert "fica de fora da comparação do período todo" in r.text
        assert f"/dashboard/{eid}?mes=2026-07" in r.text

        # Simulando só julho: SN Padrão comparável (sem aviso de dado faltante).
        r = client.get(f"/dashboard/{eid}?mes=2026-07")
        assert r.status_code == 200
        assert "informe o DAS Padrão dos meses com faturamento" not in r.text

        # A tabela de lançamentos oferece o atalho "Simular mês".
        r = client.get(f"/empresas/{eid}")
        assert "Simular mês" in r.text


def test_referencia_lista_categorias():
    with TestClient(app) as client:
        r = client.get("/referencia")
        assert r.status_code == 200
        assert "Matérias-Primas e Insumos" in r.text
        assert "Folha de Pagamento" in r.text
        assert "Permitido" in r.text and "Não permitido" in r.text

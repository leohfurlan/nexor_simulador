"""Testes do motor de cálculo e da recomendação (PRD seção 10).

Inclui o caso de referência obrigatório, as bordas (F=0/vazio) e a prova de
que os parâmetros são injetados (nenhum número mágico no motor).
"""
from decimal import Decimal

from app.calc.engine import (
    LP_CREDITO,
    LP_PURO,
    LP_REAL,
    SN_HIBRIDO,
    SN_PADRAO,
    calcular_lancamento,
)
from app.calc.params import Parametros
from app.calc.recommend import recomendar

# Caso de referência do PRD (seção 10).
F_REF = "25716.90"
D_REF = "3000.00"
DAS_REF = "2110.71"


def _resultado_ref():
    return calcular_lancamento(F_REF, D_REF, DAS_REF)


# --- Caso de referência: impostos (tolerância exata de centavo) ---------------

def test_caso_referencia_credito_e_bruto():
    r = _resultado_ref()
    assert r.credito_despesa == Decimal("810.00")   # 3.000 * 27%
    assert r.hibrido_bruto == Decimal("4191.85")     # 25.716,90 * 16,3%


def test_caso_referencia_impostos():
    r = _resultado_ref()
    assert r.regimes[SN_PADRAO].imposto == Decimal("2110.71")
    assert r.regimes[SN_HIBRIDO].imposto == Decimal("3381.85")
    assert r.regimes[LP_CREDITO].imposto == Decimal("9561.62")
    assert r.regimes[LP_PURO].imposto == Decimal("3428.06")


def test_caso_referencia_percentuais():
    r = _resultado_ref()

    def pct(chave):
        return r.regimes[chave].pct_efetivo.quantize(Decimal("0.0001"))

    assert pct(SN_PADRAO) == Decimal("0.0821")   # 8,21%
    assert pct(SN_HIBRIDO) == Decimal("0.1315")  # 13,15%
    assert pct(LP_CREDITO) == Decimal("0.3718")  # 37,18%
    assert pct(LP_PURO) == Decimal("0.1333")     # 13,33%


# --- Lucro Real (5º cenário, depende da margem) ------------------------------

def test_lucro_real_usa_margem_e_ibs_cbs():
    # F=1000, margem=20% -> lucro=200; IRPJ/CSLL 34% -> 68,00
    # IBS/CBS = 1000 * (2,7% + 8,8%) = 115,00; sem crédito (D=0)
    r = calcular_lancamento("1000", "0", "0", margem="0.20")
    assert r.lucro_real_base == Decimal("200.00")
    assert r.regimes[LP_REAL].imposto == Decimal("183.00")  # 68 + 115 - 0


def test_lucro_real_desconta_credito_das_despesas():
    # D=100 -> crédito 27,00 abate o IBS/CBS do Lucro Real
    r = calcular_lancamento("1000", "100", "0", margem="0.20")
    assert r.regimes[LP_REAL].imposto == Decimal("156.00")  # 68 + 115 - 27


# --- Bordas: faturamento zero/vazio -> nunca #DIV/0! --------------------------

def test_faturamento_zero_nao_calcula_percentual():
    r = calcular_lancamento(0, 1000, 0)
    for regime in r.regimes.values():
        assert regime.pct_efetivo is None
    # o imposto ainda é calculado, sem estourar divisão por zero
    assert r.regimes[LP_PURO].imposto == Decimal("0.00")


def test_faturamento_vazio_tratado_como_zero():
    r = calcular_lancamento("", "", "")
    assert r.regimes[SN_HIBRIDO].pct_efetivo is None
    assert r.faturamento == Decimal("0")


# --- Parâmetros injetados: prova de "nenhum número mágico" --------------------

def test_parametros_sao_injetados():
    base = calcular_lancamento("1000", "0", "0")
    custom = calcular_lancamento(
        "1000", "0", "0", Parametros(aliquota_lucro_presumido=Decimal("0.20"))
    )
    assert base.regimes[LP_PURO].imposto == Decimal("133.30")   # 1000 * 13,33%
    assert custom.regimes[LP_PURO].imposto == Decimal("200.00")  # 1000 * 20%


# --- Redução de IBS/CBS (LC 214/2025) ----------------------------------------

def test_reducao_regulamentada_nao_altera_sn_padrao():
    # O SN Padrão recolhe o IBS/CBS dentro do DAS: nada muda para ele.
    base = _resultado_ref()
    red = calcular_lancamento(F_REF, D_REF, DAS_REF, reducao_ibs_cbs="regulamentada")
    assert red.reducao_ibs_cbs == Decimal("0.30")
    assert red.regimes[SN_PADRAO].imposto == base.regimes[SN_PADRAO].imposto
    # Lucro Presumido puro não tem IBS/CBS — também intocado.
    assert red.regimes[LP_PURO].imposto == base.regimes[LP_PURO].imposto


def test_reducao_incide_so_sobre_a_parcela_ibs_cbs_do_hibrido():
    # F=1000: parcela IBS/CBS = 11,5% -> 80,50 com -30%; resíduo Simples = 4,8% -> 48,00
    r = calcular_lancamento("1000", "0", "0", reducao_ibs_cbs="regulamentada")
    assert r.hibrido_bruto == Decimal("128.50")
    assert r.cbs == Decimal("18.90")   # 1000 * 2,7% * 0,70
    assert r.ibs == Decimal("61.60")   # 1000 * 8,8% * 0,70


def test_reducao_nao_reduz_credito_das_despesas():
    # O crédito vem do que o fornecedor cobrou: continua integral (27% de 100).
    r = calcular_lancamento("1000", "100", "0", reducao_ibs_cbs="saude_educacao")
    assert r.credito_despesa == Decimal("27.00")
    # LP c/ crédito: 133,30 (LP puro) + 108,00 (27% * 0,40) - 27,00
    assert r.regimes[LP_CREDITO].imposto == Decimal("214.30")


def test_sem_reducao_mantem_o_calculo_anterior():
    base = _resultado_ref()
    assert base.reducao_ibs_cbs == Decimal("0")
    assert base.hibrido_bruto == Decimal("4191.85")
    # Chave desconhecida é ignorada (não vira redução silenciosa).
    desconhecida = calcular_lancamento(F_REF, D_REF, DAS_REF, reducao_ibs_cbs="xpto")
    assert desconhecida.hibrido_bruto == base.hibrido_bruto


# --- Recomendação (PRD seção 7) ----------------------------------------------

def test_recomendacao_menor_custo_total():
    # custo total: padrão 2.460,71 | híbrido 3.931,85 | lp 4.178,06 | lp_cred 10.311,62
    # Lucro Real fora: o caso de referência não informa margem.
    rec = recomendar(_resultado_ref(), exige_credito_cliente=False, excluir={LP_REAL})
    assert rec.regime.chave == SN_PADRAO


def test_recomendacao_desqualifica_sn_padrao_quando_exige_credito():
    # Sem margem, o Lucro Real não é candidato (excluído como no app).
    rec = recomendar(_resultado_ref(), exige_credito_cliente=True, excluir={LP_REAL})
    assert SN_PADRAO in rec.desqualificados
    assert rec.regime.chave != SN_PADRAO
    # entre os que repassam crédito, o menor custo total é o SN Híbrido
    assert rec.regime.chave == SN_HIBRIDO
    assert "competitivo" in rec.justificativa

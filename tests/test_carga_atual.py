"""Testes da estimativa de carga atual (pré-reforma) e da tabela de ICMS por UF."""
from decimal import Decimal

from app.calc.carga_atual import (
    SETOR_COMERCIO,
    SETOR_SERVICO,
    calcular_carga_atual,
)
from app.calc.tributos_uf import icms_da_uf


def test_servico_usa_iss_e_nao_icms():
    # F=10.000: PIS 0,65% =65; COFINS 3% =300; ISS 5% =500; total 865
    c = calcular_carga_atual("10000", SETOR_SERVICO)
    assert c.pis == Decimal("65.00")
    assert c.cofins == Decimal("300.00")
    assert c.iss == Decimal("500.00")
    assert c.icms == Decimal("0.00")
    assert c.total == Decimal("865.00")
    assert c.pct_efetivo == Decimal("0.0865")


def test_comercio_usa_icms_da_uf():
    # SP: ICMS 18% -> 1.800; PIS 65 + COFINS 300; total 2.165
    c = calcular_carga_atual("10000", SETOR_COMERCIO, uf="SP")
    assert c.icms == Decimal("1800.00")
    assert c.iss == Decimal("0.00")
    assert c.total == Decimal("2165.00")
    assert c.aliquota_estadual_municipal == Decimal("0.18")


def test_icms_da_uf_desconhecida_cai_no_padrao():
    assert icms_da_uf(None, Decimal("0.18")) == Decimal("0.18")
    assert icms_da_uf("ZZ", Decimal("0.18")) == Decimal("0.18")
    assert icms_da_uf("mg", Decimal("0.18")) == Decimal("0.18")  # normaliza p/ maiúscula


def test_faturamento_zero_nao_estoura_percentual():
    c = calcular_carga_atual("0", SETOR_SERVICO)
    assert c.pct_efetivo is None
    assert c.total == Decimal("0.00")

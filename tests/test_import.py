"""Testes puros do parsing de import (competência + cabeçalhos), sem banco."""
import datetime

import pytest

from app.services.lancamento_service import (
    _build_colmap,
    normalize_competencia,
)


def test_normalize_competencia_formatos():
    assert normalize_competencia("2026-01") == "2026-01"
    assert normalize_competencia("03/2026") == "2026-03"
    assert normalize_competencia("jan/2026") == "2026-01"
    assert normalize_competencia("jan./26") == "2026-01"       # formato da planilha real
    assert normalize_competencia("janeiro/2026") == "2026-01"
    assert normalize_competencia("mai./26") == "2026-05"
    assert normalize_competencia("dez/26") == "2026-12"
    assert normalize_competencia(datetime.datetime(2026, 7, 1)) == "2026-07"
    assert normalize_competencia(datetime.date(2026, 12, 1)) == "2026-12"


@pytest.mark.parametrize("bad", ["", "13/2026", "abc", "2026/01/01", None])
def test_normalize_competencia_invalida(bad):
    with pytest.raises(ValueError):
        normalize_competencia(bad)


def test_headers_reais_da_planilha_mapeiam():
    header = [
        "Mês",
        "Faturamento Mensal ($)",
        "Despesas com Crédito ($)",
        "DAS Padrão",
        "Fat. Acumulado 12 meses ($)",
    ]
    assert _build_colmap(header) == {
        "competencia": 0,
        "faturamento": 1,
        "despesas_com_credito": 2,
        "das_padrao_apurado": 3,
        "rbt12": 4,
    }

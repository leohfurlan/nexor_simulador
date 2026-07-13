"""Núcleo de cálculo (puro) do comparador de regimes tributários."""
from .engine import (
    LP_CREDITO,
    LP_PURO,
    NOMES_REGIME,
    SN_HIBRIDO,
    SN_PADRAO,
    ResultadoCalculo,
    ResultadoRegime,
    calcular_lancamento,
)
from .params import Parametros
from .recommend import Recomendacao, recomendar

__all__ = [
    "calcular_lancamento",
    "recomendar",
    "Parametros",
    "ResultadoCalculo",
    "ResultadoRegime",
    "Recomendacao",
    "NOMES_REGIME",
    "SN_PADRAO",
    "SN_HIBRIDO",
    "LP_PURO",
    "LP_CREDITO",
]

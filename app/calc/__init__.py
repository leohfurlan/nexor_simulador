"""Núcleo de cálculo (puro) do comparador de regimes tributários."""
from .engine import (
    LP_CREDITO,
    LP_PURO,
    NOMES_REDUCAO,
    NOMES_REGIME,
    REDUCOES_IBS_CBS,
    SN_HIBRIDO,
    SN_PADRAO,
    ResultadoCalculo,
    ResultadoRegime,
    calcular_lancamento,
    fracao_reducao,
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
    "NOMES_REDUCAO",
    "REDUCOES_IBS_CBS",
    "fracao_reducao",
    "SN_PADRAO",
    "SN_HIBRIDO",
    "LP_PURO",
    "LP_CREDITO",
]

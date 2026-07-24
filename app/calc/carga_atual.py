"""Estimativa da carga tributária ATUAL (pré-reforma) sobre a receita.

Referência para o comparativo "antes × depois" da reforma. É uma ESTIMATIVA
simplificada, típica do Lucro Presumido: PIS + COFINS (cumulativos) + ICMS
(comércio/indústria) ou ISS (serviços). Não cobre IPI, ST, créditos de
não-cumulatividade nem o Simples Nacional (DAS unificado).

Motor puro (Decimal), no mesmo padrão de engine.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Union

from .params import Parametros
from .tributos_uf import icms_da_uf

Number = Union[int, float, str, Decimal, None]
CENTAVO = Decimal("0.01")

SETOR_COMERCIO = "comercio"
SETOR_INDUSTRIA = "industria"
SETOR_SERVICO = "servico"
SETORES = {
    SETOR_COMERCIO: "Comércio",
    SETOR_INDUSTRIA: "Indústria",
    SETOR_SERVICO: "Serviços",
}


def _to_decimal(value: Number) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _centavos(value: Decimal) -> Decimal:
    return value.quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CargaAtual:
    setor: str
    pis: Decimal
    cofins: Decimal
    icms: Decimal              # comércio/indústria (0 em serviços)
    iss: Decimal              # serviços (0 em comércio/indústria)
    total: Decimal
    pct_efetivo: Optional[Decimal]  # total / faturamento; None quando F == 0
    aliquota_estadual_municipal: Decimal  # ICMS ou ISS aplicado (fração)


def calcular_carga_atual(
    faturamento: Number,
    setor: str,
    params: Optional[Parametros] = None,
    uf: str | None = None,
) -> CargaAtual:
    """Estima a carga atual (pré-reforma) sobre a receita, por setor."""
    params = params or Parametros()
    F = _to_decimal(faturamento)

    pis = _centavos(F * params.aliquota_pis)
    cofins = _centavos(F * params.aliquota_cofins)

    if setor == SETOR_SERVICO:
        aliq_est_mun = params.aliquota_iss
        iss = _centavos(F * aliq_est_mun)
        icms = Decimal("0.00")
    else:  # comércio ou indústria → ICMS
        aliq_est_mun = icms_da_uf(uf, params.aliquota_icms)
        icms = _centavos(F * aliq_est_mun)
        iss = Decimal("0.00")

    total = _centavos(pis + cofins + icms + iss)
    pct = (total / F) if F != 0 else None
    return CargaAtual(
        setor=setor,
        pis=pis,
        cofins=cofins,
        icms=icms,
        iss=iss,
        total=total,
        pct_efetivo=pct,
        aliquota_estadual_municipal=aliq_est_mun,
    )

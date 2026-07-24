"""Alíquotas internas de ICMS por UF — ESTIMATIVAS de referência.

Valores aproximados da alíquota interna padrão (mercadorias em geral). Servem
apenas para estimar a carga atual (pré-reforma) no comparativo; NÃO substituem
a legislação estadual (que tem exceções, ST, benefícios e alíquotas por
produto). O contador pode ajustar a alíquota padrão em Configurações.
"""
from __future__ import annotations

from decimal import Decimal

# UF -> alíquota interna padrão (fração). Estimativas de referência (2026).
ICMS_INTERNO_UF: dict[str, Decimal] = {
    "AC": Decimal("0.19"), "AL": Decimal("0.19"), "AP": Decimal("0.18"),
    "AM": Decimal("0.20"), "BA": Decimal("0.205"), "CE": Decimal("0.20"),
    "DF": Decimal("0.20"), "ES": Decimal("0.17"), "GO": Decimal("0.19"),
    "MA": Decimal("0.22"), "MT": Decimal("0.17"), "MS": Decimal("0.17"),
    "MG": Decimal("0.18"), "PA": Decimal("0.19"), "PB": Decimal("0.20"),
    "PR": Decimal("0.195"), "PE": Decimal("0.205"), "PI": Decimal("0.21"),
    "RJ": Decimal("0.20"), "RN": Decimal("0.18"), "RS": Decimal("0.17"),
    "RO": Decimal("0.195"), "RR": Decimal("0.20"), "SC": Decimal("0.17"),
    "SP": Decimal("0.18"), "SE": Decimal("0.19"), "TO": Decimal("0.20"),
}

UFS = tuple(sorted(ICMS_INTERNO_UF))


def icms_da_uf(uf: str | None, padrao: Decimal) -> Decimal:
    """Alíquota de ICMS da UF; cai no `padrao` (config) se a UF for desconhecida."""
    if not uf:
        return padrao
    return ICMS_INTERNO_UF.get(uf.strip().upper(), padrao)

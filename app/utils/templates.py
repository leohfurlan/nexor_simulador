"""Instância central de Jinja2Templates do módulo.

Reaproveita os filtros `brl` e `month_year_pt` do Nexor Fiscal (mesmos nomes,
para os templates ficarem idênticos ao integrar) e adiciona `pct` para os
percentuais efetivos do simulador.
"""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

_MONTHS_PT: dict[int, str] = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}


def _brl(value: object) -> str:
    """Número no padrão brasileiro: 1234.56 → '1.234,56' (sem prefixo R$).

    Idêntico ao filtro `brl` do Nexor Fiscal. Uso: {{ valor | brl }}.
    """
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    formatted = f"{f:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(value: object, casas: int = 2) -> str:
    """Razão → percentual pt-BR: 0.1315 → '13,15'. None/inválido → '—'.

    O motor devolve o % efetivo como razão; aqui multiplicamos por 100.
    Uso: {{ resultado.pct_efetivo | pct }}%.
    """
    if value is None:
        return "—"
    try:
        f = float(value) * 100  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    formatted = f"{f:,.{casas}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _month_year_pt(value: object) -> str:
    """Competência 'YYYY-MM' ou date → 'mai/2026'. Inválido → '—'."""
    if isinstance(value, str) and len(value) == 7 and value[4] == "-":
        try:
            year, month = int(value[:4]), int(value[5:7])
        except ValueError:
            return "—"
    else:
        month = getattr(value, "month", None)
        year = getattr(value, "year", None)
        if not isinstance(month, int) or not isinstance(year, int):
            return "—"
    return f"{_MONTHS_PT.get(month, str(month).zfill(2))}/{year}"


templates.env.filters["brl"] = _brl
templates.env.filters["pct"] = _pct
templates.env.filters["month_year_pt"] = _month_year_pt

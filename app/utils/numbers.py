"""Parsing numérico tolerante a pt-BR (vírgula decimal) e en (ponto decimal)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation


def parse_decimal_br(value: object) -> Decimal:
    """'2,70' ou '2.70' → Decimal. Vazio/None/inválido → ValueError.

    Se houver vírgula, assume pt-BR: '.' é separador de milhar e ',' decimal.
    """
    s = "" if value is None else str(value).strip()
    if s == "":
        raise ValueError("valor vazio")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"valor inválido: {value!r}") from exc


def parse_optional_decimal_br(value: object) -> Decimal | None:
    """Igual a parse_decimal_br, mas vazio/None → None (campo não informado)."""
    s = "" if value is None else str(value).strip()
    if s == "":
        return None
    return parse_decimal_br(s)


def parse_money_default_zero(value: object) -> Decimal:
    """Igual a parse_decimal_br, mas vazio/None → 0 (faturamento/despesas)."""
    s = "" if value is None else str(value).strip()
    if s == "":
        return Decimal("0")
    return parse_decimal_br(s)

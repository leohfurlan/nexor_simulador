"""Lógica de recomendação do regime ótimo (PRD seção 7).

Só concorrem à recomendação os regimes que apuram IBS/CBS no regime regular
(SN Híbrido, LP c/ crédito e Lucro Real) — os regimes de referência entram no
comparativo apenas para mostrar "quanto era". Entre os candidatos, vence o
menor custo total (imposto + honorário), com a regra de competitividade: se o
cliente da empresa exige crédito de IBS/CBS (B2B), quem não repassa crédito é
desqualificado.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .engine import REGIMES_RECOMENDAVEIS, ResultadoCalculo, ResultadoRegime


@dataclass(frozen=True)
class Recomendacao:
    regime: ResultadoRegime       # regime sugerido
    desqualificados: list[str]    # chaves descartadas pela regra de competitividade
    justificativa: str            # texto em linguagem simples para leigos


def recomendar(
    resultado: ResultadoCalculo,
    exige_credito_cliente: bool = False,
    excluir: set[str] | None = None,
) -> Recomendacao:
    # Só os regimes pós-Reforma disputam a recomendação; SN Padrão e LP puro
    # ficam de fora por construção (são referência de "quanto era").
    candidatos = {
        chave: regime
        for chave, regime in resultado.regimes.items()
        if chave in REGIMES_RECOMENDAVEIS
    }
    desqualificados: list[str] = []

    # Regimes indisponíveis (ex.: Lucro Real sem margem informada).
    for chave in excluir or ():
        if chave in candidatos:
            del candidatos[chave]
            desqualificados.append(chave)

    escolhido = min(candidatos.values(), key=lambda r: r.custo_total)
    justificativa = _justificar(escolhido, exige_credito_cliente)
    return Recomendacao(
        regime=escolhido,
        desqualificados=desqualificados,
        justificativa=justificativa,
    )


def _fmt_brl(valor: Decimal) -> str:
    """Formatação R$ pt-BR mínima (R$ 1.234,56). A versão definitiva usa Babel."""
    inteiro, _, dec = f"{valor:.2f}".partition(".")
    negativo = inteiro.startswith("-")
    inteiro = inteiro.lstrip("-")
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return f"R$ {'-' if negativo else ''}{'.'.join(grupos)},{dec}"


def _justificar(escolhido: ResultadoRegime, exige_credito_cliente: bool) -> str:
    texto = (
        f"{escolhido.nome}: {_fmt_brl(escolhido.imposto)} em impostos e "
        f"{_fmt_brl(escolhido.custo_total)} de custo total (imposto + honorário) "
        f"no período."
    )
    if exige_credito_cliente:
        texto += (
            " Como seu cliente exige crédito de IBS/CBS, o regime sugerido "
            "mantém você competitivo: ele apura IBS/CBS no regime regular e "
            "repassa o crédito integral ao cliente."
        )
    return texto

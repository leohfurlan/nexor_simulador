"""Lógica de recomendação do regime ótimo (PRD seção 7).

Combina menor custo total (imposto + honorário) com a regra de competitividade:
se o cliente da empresa exige crédito de IBS/CBS (B2B), o SN Padrão é
desqualificado porque não permite o repasse do crédito.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .engine import ResultadoCalculo, ResultadoRegime, SN_PADRAO


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
    candidatos = dict(resultado.regimes)
    desqualificados: list[str] = []

    # Regimes indisponíveis (ex.: SN Padrão sem DAS informado no mês).
    for chave in excluir or ():
        if chave in candidatos:
            del candidatos[chave]
            desqualificados.append(chave)

    # Regra de competitividade (PRD 7.2): sem repasse de crédito, o SN Padrão
    # não serve para clientes B2B que exigem crédito.
    if exige_credito_cliente and SN_PADRAO in candidatos:
        del candidatos[SN_PADRAO]
        desqualificados.append(SN_PADRAO)

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
            " Como seu cliente exige crédito de IBS/CBS, o Simples Nacional Padrão "
            "foi descartado por não permitir esse repasse — o regime sugerido "
            "mantém você competitivo."
        )
    return texto

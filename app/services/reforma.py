"""Linha do tempo da transição da Reforma Tributária (IBS/CBS).

Marcos conforme a EC 132/2023 e a LC 214/2025. São datas legislativas (não
parâmetros de cálculo), por isso ficam aqui e não na tela de Configurações.
Componente reutilizável: alimenta a seção didática do Dashboard (e, por tabela,
o PDF, que é a impressão do Dashboard).
"""
from __future__ import annotations

import datetime as dt

LINHA_TEMPO: list[dict[str, str]] = [
    {
        "ano": "2026",
        "titulo": "Início — fase de teste",
        "descricao": "CBS a 0,9% e IBS a 0,1%, compensáveis com PIS/COFINS. "
        "Sem impacto financeiro efetivo neste ano.",
    },
    {
        "ano": "2027",
        "titulo": "CBS cheia",
        "descricao": "PIS e COFINS são extintos e a CBS passa a valer "
        "integralmente. IPI zerado (exceto Zona Franca de Manaus) e início do "
        "Imposto Seletivo.",
    },
    {
        "ano": "2028",
        "titulo": "Manutenção",
        "descricao": "Sistema segue sem alteração de alíquotas em relação a 2027.",
    },
    {
        "ano": "2029",
        "titulo": "IBS começa a substituir ICMS/ISS",
        "descricao": "IBS assume 10% da carga e o ICMS/ISS cai para 90%.",
    },
    {
        "ano": "2030",
        "titulo": "Transição do IBS",
        "descricao": "IBS a 20%; ICMS/ISS a 80%.",
    },
    {
        "ano": "2031",
        "titulo": "Transição do IBS",
        "descricao": "IBS a 30%; ICMS/ISS a 70%.",
    },
    {
        "ano": "2032",
        "titulo": "Transição do IBS",
        "descricao": "IBS a 40%; ICMS/ISS a 60%.",
    },
    {
        "ano": "2033",
        "titulo": "Reforma plena",
        "descricao": "ICMS, ISS, PIS, COFINS e IPI extintos. Passam a valer "
        "apenas o IBS e a CBS.",
    },
]


def linha_tempo(hoje: dt.date | None = None) -> list[dict]:
    """Retorna a linha do tempo marcando o ano corrente com `atual=True`."""
    ano_atual = (hoje or dt.date.today()).year
    marcos = []
    for marco in LINHA_TEMPO:
        item = dict(marco)
        item["atual"] = int(marco["ano"]) == ano_atual
        marcos.append(item)
    return marcos

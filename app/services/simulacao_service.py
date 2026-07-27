"""Simulação rápida (single-shot, sem persistência) — item #10 do backlog.

Reaproveita o motor puro para uma simulação avulsa: um faturamento, um setor e
o regime atual, com resultado recalculado em tempo real (HTMX). Não grava nada
no banco — é o modo "estimar na hora", espelhando a UX de painel dividido.
"""
from __future__ import annotations

from decimal import Decimal

from app.calc.carga_atual import SETORES, calcular_carga_atual
from app.calc.engine import (
    LP_REAL,
    NOMES_REGIME,
    REGIMES_RECOMENDAVEIS,
    SN_PADRAO,
    calcular_lancamento,
)
from app.calc.recommend import recomendar
from app.services.dashboard_service import REGIME_CORES, REGIME_ORDER
from app.utils.numbers import parse_money_default_zero, parse_optional_decimal_br

_HONORARIO_ATTR = {
    "sn_padrao": "honorario_padrao",
    "sn_hibrido": "honorario_hibrido",
    "lp_puro": "honorario_lucro_presumido",
    "lp_credito": "honorario_lucro_presumido",
    "lp_real": "honorario_lucro_real",
}


def _margem_fracao(margem_pct: object) -> Decimal | None:
    pct = parse_optional_decimal_br(margem_pct)
    return None if pct is None else pct / Decimal("100")


def simular_rapida(
    calc_params,
    *,
    faturamento: object,
    despesas_com_credito: object = "",
    das_padrao_apurado: object = "",
    margem_pct: object = "",
    setor: str | None = None,
    uf: str | None = None,
    regime_atual: str | None = None,
    exige_credito_cliente: bool = False,
    reducao_ibs_cbs: str | None = None,
) -> dict:
    """Calcula os regimes para uma simulação avulsa e monta o contexto do painel."""
    F = parse_money_default_zero(faturamento)
    D = parse_money_default_zero(despesas_com_credito)
    das = parse_optional_decimal_br(das_padrao_apurado)
    margem = _margem_fracao(margem_pct)

    calc = calcular_lancamento(
        F, D, das, calc_params, margem=margem, reducao_ibs_cbs=reducao_ibs_cbs
    )

    # Regimes indisponíveis por falta de dado (mesma regra do dashboard).
    excluir = set()
    if das is None:
        excluir.add(SN_PADRAO)
    if margem is None:
        excluir.add(LP_REAL)

    def _disponivel(chave: str) -> bool:
        return chave not in excluir

    cards = []
    for chave in REGIME_ORDER:
        r = calc.regimes[chave]
        honorario = getattr(calc_params, _HONORARIO_ATTR[chave])
        cards.append({
            "chave": chave,
            "nome": NOMES_REGIME[chave],
            "cor": REGIME_CORES[chave],
            "imposto": r.imposto,
            "honorario": honorario,
            "custo_total": r.imposto + honorario,
            "pct": r.pct_efetivo,
            "disponivel": _disponivel(chave),
            "recomendavel": chave in REGIMES_RECOMENDAVEIS,
        })
    por_chave = {c["chave"]: c for c in cards}

    recomendado = None
    if F > 0:
        rec = recomendar(calc, exige_credito_cliente, excluir=excluir or None)
        recomendado = por_chave[rec.regime.chave]
        recomendado = dict(recomendado, justificativa=rec.justificativa)

    # Repasse de preço (regime atual → recomendado), com gross-up e margem.
    repasse = None
    if (
        recomendado and regime_atual in por_chave
        and por_chave[regime_atual]["disponivel"]
        and regime_atual != recomendado["chave"] and F > 0
    ):
        imposto_rec = recomendado["imposto"]
        imposto_atual = por_chave[regime_atual]["imposto"]
        delta = imposto_rec - imposto_atual
        delta_t = delta / F
        t_rec = imposto_rec / F
        pct = delta_t / (1 - t_rec) if t_rec != 1 else None
        margem_sem_repasse = (margem - delta_t) if margem is not None else None
        repasse = {
            "atual_nome": NOMES_REGIME[regime_atual],
            "delta_mensal": delta,
            "pct": pct,
            "sentido": "aumento" if delta > 0 else ("reducao" if delta < 0 else "neutro"),
            "margem": margem,
            "margem_sem_repasse": margem_sem_repasse,
        }

    carga_atual = None
    if setor in SETORES and F > 0:
        c = calcular_carga_atual(F, setor, calc_params, uf=uf)
        reforma = (calc.total_ibs_cbs - calc.credito_despesa)
        carga_atual = {
            "setor_nome": SETORES[setor],
            "uf": uf,
            "aliquota_est_mun": c.aliquota_estadual_municipal,
            "usa_iss": setor == "servico",
            "pis": c.pis, "cofins": c.cofins, "icms": c.icms, "iss": c.iss,
            "total": c.total,
            "pct": c.pct_efetivo,
            "reforma": reforma,
            "reforma_pct": (reforma / F) if F > 0 else None,
            "delta": reforma - c.total,
        }

    return {
        "cards": cards,
        "recomendado": recomendado,
        "repasse": repasse,
        "carga_atual": carga_atual,
        "faturamento": F,
        "regime_atual": regime_atual,
        "reducao_ibs_cbs": reducao_ibs_cbs or "",
        "reducao_pct": calc.reducao_ibs_cbs,
        "tem_dados": F > 0,
    }

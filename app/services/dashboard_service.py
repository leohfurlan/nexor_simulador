"""Agregação para o Dashboard (Tela 2) — totais por regime, recomendação,
economia anual e séries para os gráficos.

Cores por regime validadas com o script da skill de dataviz (paleta categórica
acessível; pior par adjacente ΔE 19,6, contraste ≥3:1 na superfície branca).
Identidade nunca fica só na cor: cards, legenda e tabela repetem o nome.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from app.calc.engine import (
    LP_CREDITO,
    LP_PURO,
    NOMES_REGIME,
    SN_HIBRIDO,
    SN_PADRAO,
)
from app.models import Empresa
from app.services.lancamento_service import compute_rows
from app.services.parametros_service import get_or_create_parametros

REGIME_ORDER = (SN_PADRAO, SN_HIBRIDO, LP_PURO, LP_CREDITO)
REGIME_CORES = {
    SN_PADRAO: "#008300",   # verde
    SN_HIBRIDO: "#2a78d6",  # azul
    LP_PURO: "#eb6834",     # laranja
    LP_CREDITO: "#4a3aa7",  # violeta
}

_MESES_ABREV = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}


def _label(competencia: str) -> str:
    ano, mes = competencia.split("-")
    return f"{_MESES_ABREV[int(mes)]}/{ano[2:]}"


def _reg(row: dict, chave: str) -> dict:
    return next(r for r in row["regimes"] if r["chave"] == chave)


async def build_dashboard(
    session, tenant_id: uuid.UUID, empresa: Empresa
) -> dict:
    params = await get_or_create_parametros(session, tenant_id)
    rows = await compute_rows(session, tenant_id, empresa)
    n = len(rows)

    honorarios = {
        SN_PADRAO: params.honorario_padrao,
        SN_HIBRIDO: params.honorario_hibrido,
        LP_PURO: params.honorario_lucro_presumido,
        LP_CREDITO: params.honorario_lucro_presumido,
    }
    faturamento_total = sum((r["faturamento"] for r in rows), Decimal("0"))
    # SN Padrão entra no acumulado quando o DAS foi informado em todos os meses
    # COM movimento (faturamento > 0). Meses sem movimento não exigem DAS: tanto
    # o SN Padrão quanto os demais regimes contribuem ~0, então não distorcem a
    # comparação. Basta o DAS ter sido informado em ao menos um mês.
    meses_com_movimento = [r for r in rows if r["faturamento"] > 0]
    tem_das = any(r["das"] is not None for r in rows)
    sn_padrao_ok = (
        n > 0
        and tem_das
        and all(r["das"] is not None for r in meses_com_movimento)
    )

    agg: dict[str, dict] = {}
    for chave in REGIME_ORDER:
        imposto_total = sum((_reg(r, chave)["imposto"] for r in rows), Decimal("0"))
        honorario_total = honorarios[chave] * n
        disponivel = sn_padrao_ok if chave == SN_PADRAO else True
        agg[chave] = {
            "chave": chave,
            "nome": NOMES_REGIME[chave],
            "cor": REGIME_CORES[chave],
            "imposto_total": imposto_total,
            "honorario_total": honorario_total,
            "custo_total": imposto_total + honorario_total,
            "pct_medio": (imposto_total / faturamento_total) if faturamento_total > 0 else None,
            "disponivel": disponivel,
        }

    # Recomendação sobre o acumulado (PRD seção 7).
    candidatos = [c for c in REGIME_ORDER if agg[c]["disponivel"]]
    if empresa.exige_credito_cliente:
        candidatos = [c for c in candidatos if c != SN_PADRAO]
    recomendado = (
        min(candidatos, key=lambda c: agg[c]["custo_total"]) if candidatos and n else None
    )

    # Economia vs. regime atual (PRD 7.4).
    economia = None
    atual = empresa.regime_atual
    if recomendado and atual in agg and agg[atual]["disponivel"] and atual != recomendado:
        periodo = agg[atual]["custo_total"] - agg[recomendado]["custo_total"]
        economia = {
            "atual_nome": NOMES_REGIME[atual],
            "recomendado_nome": NOMES_REGIME[recomendado],
            "periodo": periodo,
            "anual": (periodo / n * 12) if n else Decimal("0"),
            "meses": n,
        }

    # Séries para os gráficos (float p/ JSON; None vira gap na linha).
    labels = [_label(r["competencia"]) for r in rows]
    pct_series: dict[str, list] = {}
    custo_series: dict[str, list] = {}
    for chave in REGIME_ORDER:
        pcts, custos = [], []
        for r in rows:
            reg = _reg(r, chave)
            if reg["disponivel"] and reg["pct"] is not None:
                pcts.append(round(float(reg["pct"]) * 100, 2))
            else:
                pcts.append(None)
            if reg["disponivel"]:
                custos.append(round(float(reg["imposto"]) + float(honorarios[chave]), 2))
            else:
                custos.append(None)
        pct_series[chave] = pcts
        custo_series[chave] = custos

    chart = {
        "labels": labels,
        "ordem": list(REGIME_ORDER),
        "nomes": {c: NOMES_REGIME[c] for c in REGIME_ORDER},
        "cores": REGIME_CORES,
        "pct": pct_series,
        "custo": custo_series,
    }

    return {
        "empresa": empresa,
        "rows": rows,
        "cards": [agg[c] for c in REGIME_ORDER],
        "recomendado": agg[recomendado] if recomendado else None,
        "economia": economia,
        "n_meses": n,
        "faturamento_total": faturamento_total,
        "sn_padrao_ok": sn_padrao_ok,
        "chart": chart,
    }

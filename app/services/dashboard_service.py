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
from app.services.reforma import linha_tempo

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


def _label_completo(competencia: str) -> str:
    ano, mes = competencia.split("-")
    return f"{_MESES_ABREV[int(mes)]}/{ano}"


def _fmt_brl(valor: Decimal) -> str:
    """R$ pt-BR (R$ 1.234,56). Espelha o filtro `brl` dos templates."""
    inteiro, _, dec = f"{Decimal(valor):.2f}".partition(".")
    negativo = inteiro.startswith("-")
    inteiro = inteiro.lstrip("-")
    grupos: list[str] = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return f"R$ {'-' if negativo else ''}{'.'.join(grupos)},{dec}"


def _fmt_pct(razao) -> str:
    """Razão (0.1315) → '13,15%'. None → '—'."""
    if razao is None:
        return "—"
    return f"{float(razao) * 100:.2f}".replace(".", ",") + "%"


def _montar_resumo(
    empresa: Empresa,
    periodo_desc: str,
    faturamento_total: Decimal,
    cards: list[dict],
    recomendado: dict | None,
    economia: dict | None,
    repasse: dict | None,
) -> str:
    """Resumo em texto plano para o botão 'Copiar resumo' (área de transferência)."""
    linhas = [
        f"SIMULAÇÃO TRIBUTÁRIA — {empresa.nome}",
        periodo_desc,
        f"Faturamento total: {_fmt_brl(faturamento_total)}",
        "",
    ]
    if recomendado:
        linhas.append(f"Regime recomendado: {recomendado['nome']}")
        linhas.append(
            f"  Custo total (imposto + honorário): {_fmt_brl(recomendado['custo_total'])}"
        )
        linhas.append(f"  Só impostos: {_fmt_brl(recomendado['imposto_total'])}")
        linhas.append(f"  % efetivo médio: {_fmt_pct(recomendado['pct_medio'])}")
    if economia:
        linhas.append("")
        linhas.append(
            f"Economia saindo de {economia['atual_nome']}: "
            f"{_fmt_brl(economia['periodo'])} no período "
            f"(projeção {_fmt_brl(economia['anual'])}/ano)."
        )
    if repasse and repasse["pct"] is not None:
        if repasse["sentido"] == "aumento":
            linhas.append(
                f"Repasse de preço sugerido: +{_fmt_pct(repasse['pct'])} "
                f"({_fmt_brl(repasse['delta_mensal'])}/mês) para manter a margem "
                f"com o novo regime."
            )
        elif repasse["sentido"] == "reducao":
            linhas.append(
                f"Folga de preço: você pode reduzir o preço em até "
                f"{_fmt_pct(abs(repasse['pct']))} mantendo a margem — "
                f"vantagem competitiva do regime recomendado."
            )
        if repasse.get("margem_sem_repasse") is not None:
            linhas.append(
                f"  Margem estimada: {_fmt_pct(repasse['margem'])} → "
                f"{_fmt_pct(repasse['margem_sem_repasse'])} sem repasse."
            )
    linhas.append("")
    linhas.append("Comparativo por regime (custo total no período):")
    for c in cards:
        if c["disponivel"]:
            linhas.append(
                f"  - {c['nome']}: {_fmt_brl(c['custo_total'])} "
                f"(impostos {_fmt_brl(c['imposto_total'])}, "
                f"honorários {_fmt_brl(c['honorario_total'])})"
            )
        else:
            linhas.append(f"  - {c['nome']}: — (DAS não informado)")
    linhas.append("")
    linhas.append(
        "As alíquotas de IBS/CBS são estimativas e podem mudar até a "
        "regulamentação final da Reforma Tributária."
    )
    return "\n".join(linhas)


def _reg(row: dict, chave: str) -> dict:
    return next(r for r in row["regimes"] if r["chave"] == chave)


async def build_dashboard(
    session, tenant_id: uuid.UUID, empresa: Empresa, competencia: str | None = None
) -> dict:
    params = await get_or_create_parametros(session, tenant_id)
    todas_rows = await compute_rows(session, tenant_id, empresa)

    # Filtro por competência: a simulação pode ser feita mês a mês ou sobre o
    # período todo. `meses_disponiveis` alimenta o seletor; `mes_selecionado`
    # só vale se existir de fato entre os lançamentos.
    meses_disponiveis = [r["competencia"] for r in todas_rows]
    mes_selecionado = competencia if competencia in meses_disponiveis else None
    rows = (
        [r for r in todas_rows if r["competencia"] == mes_selecionado]
        if mes_selecionado
        else todas_rows
    )
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
    # Quando só ALGUNS meses têm o DAS informado (uso típico do contador: lança o
    # DAS de um mês para simular só ele), o SN Padrão fica de fora do acumulado,
    # mas pode ser comparado mês a mês. `sn_padrao_parcial` sinaliza esse caso
    # para orientar o usuário a escolher um mês no seletor de simulação.
    meses_com_das = [r["competencia"] for r in rows if r["das"] is not None]
    sn_padrao_parcial = bool(meses_com_das) and not sn_padrao_ok

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

    # Sugestão de repasse de preço (oportunidade da Reforma): quanto ajustar o
    # preço para manter a margem ao migrar do regime atual para o recomendado.
    # Baseado na diferença de TRIBUTOS (não de honorários), pois é o imposto que
    # se repassa ao preço cobrado do cliente. Mesmo guard da economia.
    repasse = None
    if recomendado and atual in agg and agg[atual]["disponivel"] and atual != recomendado:
        delta = agg[recomendado]["imposto_total"] - agg[atual]["imposto_total"]
        # delta_t: variação da carga tributária em pontos de receita (fração).
        delta_t = (delta / faturamento_total) if faturamento_total > 0 else None
        # % a repassar no preço com gross-up pela alíquota do novo regime: como
        # o preço maior também é tributado, o repasse necessário para preservar a
        # margem é (t_rec - t_atual) / (1 - t_rec), não apenas (t_rec - t_atual).
        t_rec = (
            agg[recomendado]["imposto_total"] / faturamento_total
            if faturamento_total > 0 else None
        )
        pct = (
            delta_t / (1 - t_rec)
            if delta_t is not None and t_rec is not None and t_rec != 1
            else None
        )
        # Margem informada no cadastro → projeção da margem caso não haja repasse
        # (a variação de carga é absorvida diretamente pela margem).
        margem = empresa.margem_lucro_estimada
        margem_sem_repasse = (
            margem - delta_t if margem is not None and delta_t is not None else None
        )
        repasse = {
            "atual_nome": NOMES_REGIME[atual],
            "recomendado_nome": NOMES_REGIME[recomendado],
            "delta_periodo": delta,                       # + imposto sobe; - imposto cai
            "delta_mensal": (delta / n) if n else Decimal("0"),
            "delta_t": delta_t,
            "pct": pct,                                   # gross-up (% do preço)
            "sentido": "aumento" if delta > 0 else ("reducao" if delta < 0 else "neutro"),
            "margem": margem,
            "margem_sem_repasse": margem_sem_repasse,
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

    cards = [agg[c] for c in REGIME_ORDER]
    rec_card = agg[recomendado] if recomendado else None

    if mes_selecionado:
        periodo_desc = f"Competência: {_label_completo(mes_selecionado)}"
    else:
        periodo_desc = f"Período: {n} {'mês' if n == 1 else 'meses'}"
    resumo = _montar_resumo(
        empresa, periodo_desc, faturamento_total, cards, rec_card, economia, repasse
    )

    return {
        "empresa": empresa,
        "rows": rows,
        "cards": cards,
        "recomendado": rec_card,
        "economia": economia,
        "repasse": repasse,
        "resumo": resumo,
        "linha_tempo": linha_tempo(),
        "n_meses": n,
        "faturamento_total": faturamento_total,
        "sn_padrao_ok": sn_padrao_ok,
        "chart": chart,
        "meses_disponiveis": meses_disponiveis,
        "mes_selecionado": mes_selecionado,
        "sn_padrao_parcial": sn_padrao_parcial,
        "meses_com_das": meses_com_das,
    }

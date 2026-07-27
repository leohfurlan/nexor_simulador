"""Motor de cálculo puro do comparador de regimes tributários.

Não conhece Flask nem banco de dados: recebe valores + Parametros e devolve
um ResultadoCalculo. Toda a aritmética usa Decimal para precisão de centavos
(ROUND_HALF_UP, padrão brasileiro). Referência: PRD seções 4 e 6.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

from .params import Parametros

Number = Union[int, float, str, Decimal, None]

CENTAVO = Decimal("0.01")

# Chaves canônicas dos regimes comparados (PRD seção 1 + Lucro Real).
SN_PADRAO = "sn_padrao"
SN_HIBRIDO = "sn_hibrido"
LP_PURO = "lp_puro"
LP_CREDITO = "lp_credito"
LP_REAL = "lp_real"

NOMES_REGIME = {
    SN_PADRAO: "Simples Nacional Padrão",
    SN_HIBRIDO: "Simples Nacional Híbrido",
    LP_PURO: "Lucro Presumido",
    LP_CREDITO: "Lucro Presumido c/ crédito IBS/CBS",
    LP_REAL: "Lucro Real",
}

# --- Reduções de alíquota de IBS/CBS (LC 214/2025) ---------------------------
# Só valem para quem apura IBS/CBS no REGIME REGULAR: SN Híbrido, Lucro
# Presumido c/ crédito e Lucro Real. O SN Padrão recolhe tudo dentro do DAS e
# não aproveita redução alguma — é justamente essa assimetria que pode inverter
# a recomendação entre Padrão e Híbrido para um profissional liberal.
# A redução incide apenas sobre o DÉBITO de IBS/CBS; o crédito das despesas
# (cobrado pelos fornecedores) permanece integral.
REDUCAO_REGULAMENTADA = "regulamentada"
REDUCAO_SAUDE_EDUCACAO = "saude_educacao"

REDUCOES_IBS_CBS = {
    # art. 127: contadores, advogados, engenheiros, arquitetos, administradores,
    # economistas e demais profissões regulamentadas da lista taxativa.
    REDUCAO_REGULAMENTADA: Decimal("0.30"),
    # arts. 128/129: serviços de saúde e de educação.
    REDUCAO_SAUDE_EDUCACAO: Decimal("0.60"),
}

NOMES_REDUCAO = {
    REDUCAO_REGULAMENTADA: "Profissão regulamentada (−30% de IBS/CBS)",
    REDUCAO_SAUDE_EDUCACAO: "Saúde / Educação (−60% de IBS/CBS)",
}


def fracao_reducao(reducao: Optional[str]) -> Decimal:
    """Chave da redução → fração reduzida (0.30). Chave vazia/desconhecida → 0."""
    if not reducao:
        return Decimal("0")
    return REDUCOES_IBS_CBS.get(reducao, Decimal("0"))


def _to_decimal(value: Number) -> Decimal:
    """Coage entrada (int/float/str/None/'') para Decimal sem artefato de float."""
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _centavos(value: Decimal) -> Decimal:
    return value.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _pct(imposto: Decimal, faturamento: Decimal) -> Optional[Decimal]:
    """% efetivo como razão (0.1315 == 13,15%). None quando F == 0 (evita #DIV/0!)."""
    if faturamento == 0:
        return None
    return imposto / faturamento


@dataclass(frozen=True)
class ResultadoRegime:
    chave: str
    nome: str
    imposto: Decimal              # R$ do imposto do regime no período
    honorario: Decimal            # R$ do honorário mensal do regime
    custo_total: Decimal          # imposto + honorário
    pct_efetivo: Optional[Decimal]  # razão; None quando faturamento == 0


@dataclass(frozen=True)
class ResultadoCalculo:
    faturamento: Decimal
    despesas_com_credito: Decimal
    credito_despesa: Decimal      # D * aliquota_credito_despesa
    cbs: Decimal                  # informativo (destaque na nota)
    ibs: Decimal                  # informativo
    total_ibs_cbs: Decimal        # cbs + ibs
    hibrido_bruto: Decimal        # F * aliquota_hibrido_total (antes do crédito)
    lucro_real_base: Decimal      # lucro estimado (margem * F) usado no Lucro Real
    reducao_ibs_cbs: Decimal      # fração de redução aplicada ao IBS/CBS (0 = nenhuma)
    regimes: dict[str, ResultadoRegime]


def calcular_lancamento(
    faturamento: Number,
    despesas_com_credito: Number,
    das_padrao_apurado: Number,
    params: Optional[Parametros] = None,
    margem: Number = None,
    reducao_ibs_cbs: Optional[str] = None,
) -> ResultadoCalculo:
    """Calcula os regimes para um lançamento mensal (PRD seção 6 + Lucro Real).

    `margem` (fração da receita, ex.: 0.20) é a margem de lucro estimada da
    empresa. Necessária para o Lucro Real (IRPJ/CSLL incidem sobre o lucro);
    quando ausente, o Lucro Real é calculado sobre lucro zero e deve ser
    marcado como indisponível pela camada superior.

    `reducao_ibs_cbs` é a chave da redução de alíquota da LC 214/2025
    ("regulamentada" = 30%, "saude_educacao" = 60%); ver REDUCOES_IBS_CBS.
    """
    params = params or Parametros()

    F = _to_decimal(faturamento)
    D = _to_decimal(despesas_com_credito)
    das_padrao = _to_decimal(das_padrao_apurado)
    m = _to_decimal(margem)

    # Fator aplicado ao débito de IBS/CBS: 1 - redução (0,70 nas regulamentadas).
    reducao = fracao_reducao(reducao_ibs_cbs)
    fator = Decimal("1") - reducao

    # Créditos gerados pelas despesas — integrais, não sofrem a redução.
    credito_despesa = _centavos(D * params.aliquota_credito_despesa)

    # Informativos (destaque na nota), já líquidos da redução.
    cbs = _centavos(F * params.aliquota_cbs * fator)
    ibs = _centavos(F * params.aliquota_ibs * fator)
    total_ibs_cbs = _centavos(cbs + ibs)

    # ① SN Híbrido: a alíquota total (16,3%) embute a parcela de IBS/CBS apurada
    # no regime regular (CBS + IBS destacados = 11,5%) mais o resíduo do Simples
    # (4,8%, que continua no DAS). A redução incide só sobre a primeira parcela.
    aliq_ibs_cbs_hibrido = min(
        params.aliquota_cbs + params.aliquota_ibs, params.aliquota_hibrido_total
    )
    aliq_residual_hibrido = params.aliquota_hibrido_total - aliq_ibs_cbs_hibrido
    hibrido_bruto = _centavos(
        F * (aliq_ibs_cbs_hibrido * fator + aliq_residual_hibrido)
    )
    hibrido_liquido = _centavos(hibrido_bruto - credito_despesa)

    # ② SN Padrão (input manual na v1)
    padrao_valor = _centavos(das_padrao)

    # ③ Lucro Presumido puro (IRPJ+CSLL+PIS+COFINS+ISS de hoje, sem IBS/CBS)
    lp_valor = _centavos(F * params.aliquota_lucro_presumido)

    # ④ Lucro Presumido c/ aproveitamento de IBS/CBS: soma o IBS/CBS do
    # regime (alíquota própria, diferente do CBS/IBS "destacado" acima) e
    # abate o crédito das despesas.
    lp_ibs_cbs = _centavos(F * params.aliquota_lucro_presumido_ibs_cbs * fator)
    lp_credito_valor = _centavos(lp_valor + lp_ibs_cbs - credito_despesa)

    # ⑤ Lucro Real: IRPJ/CSLL sobre o lucro estimado (margem * F) + IBS/CBS
    # sobre a receita, líquidos do crédito das despesas. Só é significativo com
    # a margem informada.
    lucro_real_base = _centavos(F * m)
    lp_real_irpj_csll = _centavos(lucro_real_base * params.aliquota_lucro_real_irpj_csll)
    lp_real_valor = _centavos(lp_real_irpj_csll + total_ibs_cbs - credito_despesa)

    def _regime(chave: str, imposto: Decimal, honorario: Decimal) -> ResultadoRegime:
        honorario = _to_decimal(honorario)
        return ResultadoRegime(
            chave=chave,
            nome=NOMES_REGIME[chave],
            imposto=imposto,
            honorario=honorario,
            custo_total=_centavos(imposto + honorario),
            pct_efetivo=_pct(imposto, F),
        )

    regimes = {
        SN_PADRAO: _regime(SN_PADRAO, padrao_valor, params.honorario_padrao),
        SN_HIBRIDO: _regime(SN_HIBRIDO, hibrido_liquido, params.honorario_hibrido),
        LP_PURO: _regime(LP_PURO, lp_valor, params.honorario_lucro_presumido),
        LP_CREDITO: _regime(LP_CREDITO, lp_credito_valor, params.honorario_lucro_presumido),
        LP_REAL: _regime(LP_REAL, lp_real_valor, params.honorario_lucro_real),
    }

    return ResultadoCalculo(
        faturamento=F,
        despesas_com_credito=D,
        credito_despesa=credito_despesa,
        cbs=cbs,
        ibs=ibs,
        total_ibs_cbs=total_ibs_cbs,
        hibrido_bruto=hibrido_bruto,
        lucro_real_base=lucro_real_base,
        reducao_ibs_cbs=reducao,
        regimes=regimes,
    )

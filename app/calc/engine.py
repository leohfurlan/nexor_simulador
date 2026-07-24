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
    regimes: dict[str, ResultadoRegime]


def calcular_lancamento(
    faturamento: Number,
    despesas_com_credito: Number,
    das_padrao_apurado: Number,
    params: Optional[Parametros] = None,
    margem: Number = None,
) -> ResultadoCalculo:
    """Calcula os regimes para um lançamento mensal (PRD seção 6 + Lucro Real).

    `margem` (fração da receita, ex.: 0.20) é a margem de lucro estimada da
    empresa. Necessária para o Lucro Real (IRPJ/CSLL incidem sobre o lucro);
    quando ausente, o Lucro Real é calculado sobre lucro zero e deve ser
    marcado como indisponível pela camada superior.
    """
    params = params or Parametros()

    F = _to_decimal(faturamento)
    D = _to_decimal(despesas_com_credito)
    das_padrao = _to_decimal(das_padrao_apurado)
    m = _to_decimal(margem)

    # Créditos gerados pelas despesas.
    credito_despesa = _centavos(D * params.aliquota_credito_despesa)

    # Informativos (destaque na nota).
    cbs = _centavos(F * params.aliquota_cbs)
    ibs = _centavos(F * params.aliquota_ibs)
    total_ibs_cbs = _centavos(cbs + ibs)

    # ① SN Híbrido
    hibrido_bruto = _centavos(F * params.aliquota_hibrido_total)
    hibrido_liquido = _centavos(hibrido_bruto - credito_despesa)

    # ② SN Padrão (input manual na v1)
    padrao_valor = _centavos(das_padrao)

    # ③ Lucro Presumido puro
    lp_valor = _centavos(F * params.aliquota_lucro_presumido)

    # ④ Lucro Presumido c/ aproveitamento de IBS/CBS
    lp_credito_valor = _centavos(lp_valor - credito_despesa)

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
        regimes=regimes,
    )

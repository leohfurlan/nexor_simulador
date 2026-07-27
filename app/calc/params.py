"""Parâmetros configuráveis do comparador de regimes (PRD seção 4).

Estes são os valores padrão. Na aplicação completa eles vêm da tabela
`Parametros` (tela de Configurações) e são convertidos para esta dataclass
antes de entrar no motor de cálculo — assim o motor permanece puro e nenhum
número fica "mágico" no código.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Parametros:
    # Alíquotas (frações: 0.027 == 2,7%)
    aliquota_cbs: Decimal = Decimal("0.027")            # CBS destacada
    aliquota_ibs: Decimal = Decimal("0.088")            # IBS destacada
    aliquota_hibrido_total: Decimal = Decimal("0.163")  # Imposto bruto SN Híbrido
    aliquota_credito_despesa: Decimal = Decimal("0.27")  # Crédito gerado por despesas
    aliquota_lucro_presumido: Decimal = Decimal("0.1333")  # IRPJ+CSLL+PIS+COFINS+ISS (Lucro Presumido puro, hoje)
    aliquota_lucro_presumido_ibs_cbs: Decimal = Decimal("0.27")  # IBS/CBS do Lucro Presumido c/ crédito
    aliquota_lucro_real_irpj_csll: Decimal = Decimal("0.34")  # IRPJ+adic.+CSLL s/ lucro

    # Estimativa da carga atual (pré-reforma) sobre a receita — referência para
    # o comparativo "antes × depois". Valores típicos do Lucro Presumido.
    aliquota_pis: Decimal = Decimal("0.0065")     # PIS cumulativo
    aliquota_cofins: Decimal = Decimal("0.03")    # COFINS cumulativa
    aliquota_iss: Decimal = Decimal("0.05")       # ISS (serviços) — típico
    aliquota_icms: Decimal = Decimal("0.18")      # ICMS interno padrão (fallback)

    # Honorários mensais (R$)
    honorario_hibrido: Decimal = Decimal("550")
    honorario_padrao: Decimal = Decimal("350")
    honorario_lucro_presumido: Decimal = Decimal("750")
    honorario_lucro_real: Decimal = Decimal("900")

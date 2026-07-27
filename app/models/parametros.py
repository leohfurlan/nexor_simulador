"""Parametros — alíquotas e honorários configuráveis (PRD seções 4 e 5).

Global por tenant (empresa_id NULL) ou override por empresa. A tela de
Configurações edita a linha global do tenant. O método `to_calc()` converte
para a dataclass pura consumida pelo motor de cálculo — assim nenhum número
fica hardcoded no motor.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.calc.params import Parametros as CalcParametros
from app.database import Base

# Precisão: alíquotas com 5 casas (0.16550), honorários em centavos.
_ALIQ = Numeric(6, 5)
_MOEDA = Numeric(10, 2)


class Parametros(Base):
    __tablename__ = "sim_parametros"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    # NULL = parâmetros globais do tenant; preenchido = override de uma empresa.
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sim_empresas.id", ondelete="CASCADE"), nullable=True, index=True
    )

    aliquota_cbs: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.02700"))
    aliquota_ibs: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.08800"))
    aliquota_hibrido_total: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.16300"))
    aliquota_credito_despesa: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.27000"))
    aliquota_lucro_presumido: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.13330"))
    aliquota_lucro_presumido_ibs_cbs: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.27000"))
    aliquota_lucro_real_irpj_csll: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.34000"))

    # Estimativa da carga atual (pré-reforma).
    aliquota_pis: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.00650"))
    aliquota_cofins: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.03000"))
    aliquota_iss: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.05000"))
    aliquota_icms: Mapped[Decimal] = mapped_column(_ALIQ, default=Decimal("0.18000"))

    honorario_hibrido: Mapped[Decimal] = mapped_column(_MOEDA, default=Decimal("550.00"))
    honorario_padrao: Mapped[Decimal] = mapped_column(_MOEDA, default=Decimal("350.00"))
    honorario_lucro_presumido: Mapped[Decimal] = mapped_column(_MOEDA, default=Decimal("750.00"))
    honorario_lucro_real: Mapped[Decimal] = mapped_column(_MOEDA, default=Decimal("900.00"))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_calc(self) -> CalcParametros:
        """Converte para a dataclass pura consumida pelo motor de cálculo."""
        return CalcParametros(
            aliquota_cbs=self.aliquota_cbs,
            aliquota_ibs=self.aliquota_ibs,
            aliquota_hibrido_total=self.aliquota_hibrido_total,
            aliquota_credito_despesa=self.aliquota_credito_despesa,
            aliquota_lucro_presumido=self.aliquota_lucro_presumido,
            aliquota_lucro_presumido_ibs_cbs=self.aliquota_lucro_presumido_ibs_cbs,
            aliquota_lucro_real_irpj_csll=self.aliquota_lucro_real_irpj_csll,
            aliquota_pis=self.aliquota_pis,
            aliquota_cofins=self.aliquota_cofins,
            aliquota_iss=self.aliquota_iss,
            aliquota_icms=self.aliquota_icms,
            honorario_hibrido=self.honorario_hibrido,
            honorario_padrao=self.honorario_padrao,
            honorario_lucro_presumido=self.honorario_lucro_presumido,
            honorario_lucro_real=self.honorario_lucro_real,
        )

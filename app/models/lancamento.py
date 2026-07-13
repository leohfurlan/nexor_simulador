"""LancamentoMensal — dados mensais de faturamento/despesas (PRD seção 5)."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LancamentoMensal(Base):
    __tablename__ = "sim_lancamentos_mensais"
    __table_args__ = (
        UniqueConstraint("empresa_id", "competencia", name="uq_sim_lancamento_competencia"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sim_empresas.id", ondelete="CASCADE"), index=True
    )

    competencia: Mapped[str] = mapped_column(String(7))  # 'YYYY-MM'

    # Inputs do motor de cálculo (PRD seção 6).
    faturamento: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    despesas_com_credito: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    das_padrao_apurado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # rbt12: informativo na v1 (base para automatizar o DAS Padrão depois).
    rbt12: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="lancamentos")  # noqa: F821

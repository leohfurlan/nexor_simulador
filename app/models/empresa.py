"""Empresa — a empresa-cliente cujos tributos são simulados (PRD seção 5).

Tenant-scoped: pertence a um tenant (escritório) do Nexor Fiscal.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Empresa(Base):
    __tablename__ = "sim_empresas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # tenant_id sem FK no standalone (não há tabela tenants); na integração ao
    # Nexor Fiscal vira ForeignKey("tenants.id").
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True)

    nome: Mapped[str] = mapped_column(String(200))
    cnpj: Mapped[str | None] = mapped_column(String(18), nullable=True)
    atividade: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exige_credito_cliente: Mapped[bool] = mapped_column(Boolean, default=False)
    # Chave do regime atual da empresa (sn_padrao/sn_hibrido/lp_puro/lp_credito),
    # base para a "economia anual vs. regime atual" (PRD 7.4). Opcional.
    regime_atual: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lancamentos: Mapped[list["LancamentoMensal"]] = relationship(  # noqa: F821
        back_populates="empresa",
        cascade="all, delete-orphan",
        order_by="LancamentoMensal.competencia",
    )

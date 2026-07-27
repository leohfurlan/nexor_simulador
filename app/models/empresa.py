"""Empresa — a empresa-cliente cujos tributos são simulados (PRD seção 5).

Tenant-scoped: pertence a um tenant (escritório) do Nexor Fiscal.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Uuid, func
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
    # Setor de atividade (comercio/industria/servico): define ISS × ICMS na
    # estimativa da carga atual (pré-reforma). Opcional.
    setor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # UF (sigla, ex.: "SP") para estimar a alíquota interna de ICMS. Opcional.
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    exige_credito_cliente: Mapped[bool] = mapped_column(Boolean, default=False)
    # Chave do regime atual da empresa (sn_padrao/sn_hibrido/lp_puro/lp_credito),
    # base para a "economia anual vs. regime atual" (PRD 7.4). Opcional.
    regime_atual: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Margem de lucro líquida estimada (fração: 0.20 == 20%). Opcional; usada
    # para refinar a sugestão de repasse de preço (impacto na margem).
    margem_lucro_estimada: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 5), nullable=True
    )
    # Redução de alíquota de IBS/CBS da LC 214/2025 ("regulamentada" = 30%,
    # "saude_educacao" = 60%). Opt-in: o enquadramento na lista taxativa é
    # responsabilidade do contador. Vazio/None = sem redução.
    reducao_ibs_cbs: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lancamentos: Mapped[list["LancamentoMensal"]] = relationship(  # noqa: F821
        back_populates="empresa",
        cascade="all, delete-orphan",
        order_by="LancamentoMensal.competencia",
    )

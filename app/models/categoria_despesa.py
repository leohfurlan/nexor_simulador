"""CategoriaDespesa — tabela de referência de crédito (PRD seções 5 e 8/Tela 3).

Somente leitura, global (não tenant-scoped): é uma tabela informativa que
mostra quais despesas geram crédito de IBS/CBS (ícones ✅/⚠️/❌).
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Valores canônicos de elegibilidade (dirigem o ícone na UI).
PERMITIDO = "Permitido"        # ✅
CONDICIONADO = "Condicionado"  # ⚠️
NAO_PERMITIDO = "Não permitido"  # ❌


class CategoriaDespesa(Base):
    __tablename__ = "sim_categorias_despesa"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    elegibilidade_credito: Mapped[str] = mapped_column(String(20))  # PERMITIDO/CONDICIONADO/NAO_PERMITIDO
    gera_credito: Mapped[bool] = mapped_column(Boolean, default=False)
    observacao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)

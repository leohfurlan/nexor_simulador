"""Dependências FastAPI do módulo — SEAM DE INTEGRAÇÃO com o Nexor Fiscal.

No modo standalone, `get_tenant_id` devolve um tenant fixo de desenvolvimento.
Ao integrar ao Nexor Fiscal, reescreva SOMENTE este arquivo para derivar o
tenant do contexto autenticado do host, por exemplo:

    from app.dependencies import get_current_tenant  # do Nexor Fiscal

    async def get_tenant_id(
        user_tenant: tuple[User, Tenant] = Depends(get_current_tenant),
    ) -> uuid.UUID:
        _, tenant = user_tenant
        return tenant.id

Os routers do módulo dependem apenas de `get_tenant_id`, então a troca é
localizada aqui — nenhuma rota precisa mudar.
"""
from __future__ import annotations

import uuid

from app.config import settings


async def get_tenant_id() -> uuid.UUID:
    """Tenant atual. Standalone: fixo de dev. Integração: derivado do JWT."""
    return settings.dev_tenant_id

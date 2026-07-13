"""Configurações do módulo (pydantic-settings), espelhando o padrão do Nexor Fiscal.

No modo standalone usamos SQLite (aiosqlite) para rodar sem servidor. Ao
integrar ao Nexor Fiscal, o módulo passa a usar o `settings.database_url`
(Postgres/asyncpg) e o `Base`/sessão do host.
"""
from __future__ import annotations

import uuid

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Banco — standalone usa SQLite async; produção usa Postgres do Nexor Fiscal.
    database_url: str = "sqlite+aiosqlite:///./nexor_sim.db"
    debug: bool = True
    # Log de SQL (echo). Separado do debug para não poluir dev/testes por padrão.
    sql_echo: bool = False

    # Tenant fixo para desenvolvimento standalone. Na integração, o tenant vem
    # do JWT via get_current_tenant (ver app/deps.py — seam de integração).
    dev_tenant_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

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

    # Tenant do escritório (JS APOIO CONTABIL). Usado tanto para escopo dos dados
    # do simulador quanto para ler a base do Nexor Fiscal. Na integração, virá do JWT.
    dev_tenant_id: uuid.UUID = uuid.UUID("8b5dbf59-dd85-4c63-9e94-0f792309b10b")

    # Conexão READ-ONLY à base do Nexor Fiscal (nfse_hub) para exibir/importar
    # clientes e notas. Vazio = feature desativada. Fica no .env (gitignored).
    nexor_fiscal_database_url: str = ""
    # Histórico de notas a partir deste ano (PRD desta integração: 2025).
    nexor_fiscal_desde_ano: int = 2025

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

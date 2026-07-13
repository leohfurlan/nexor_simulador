"""Conector READ-ONLY à base do Nexor Fiscal (nfse_hub).

Lê clientes (tabela `cnpjs`) e notas (`nfse_documents`) de um tenant. Usa SQL
portável via `text()` para funcionar em Postgres (produção) e SQLite (testes).
NUNCA escreve no banco do Nexor Fiscal. Os UUIDs são validados e embutidos como
literais (Postgres faz cast implícito de literal para `uuid`; injeção é evitada
porque só um UUID válido passa por `uuid.UUID`).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

_engine: AsyncEngine | None = None


def is_configured() -> bool:
    return bool(settings.nexor_fiscal_database_url)


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = settings.nexor_fiscal_database_url
        connect_args: dict[str, Any] = {}
        kwargs: dict[str, Any] = {"pool_pre_ping": True}
        if "neon.tech" in url:  # Neon exige TLS
            connect_args = {"ssl": "require"}
        if url.startswith("postgresql"):
            # Pool pequeno + recycle: respeita o limite de conexões do Neon.
            kwargs.update(pool_size=3, max_overflow=2, pool_recycle=300)
        _engine = create_async_engine(url, connect_args=connect_args, **kwargs)
    return _engine


def _uuid(value) -> str:
    """Valida e devolve o UUID como string (seguro para embutir no SQL)."""
    return str(uuid.UUID(str(value)))


async def _rows(sql: str, params: dict | None = None) -> list[dict]:
    async with _get_engine().connect() as conn:
        result = await conn.execute(text(sql), params or {})
        return [dict(m) for m in result.mappings().all()]


async def get_tenant_nome(tenant_id) -> str | None:
    tid = _uuid(tenant_id)
    rows = await _rows(f"SELECT name FROM tenants WHERE id = '{tid}'")
    return rows[0]["name"] if rows else None


async def list_clientes(tenant_id, desde_ano: int) -> list[dict]:
    """Clientes do escritório com resumo de notas emitidas/recebidas no período."""
    tid = _uuid(tenant_id)
    sql = f"""
        SELECT c.id AS cnpj_id, c.cnpj, c.razao_social, c.nome_fantasia,
               c.regime_tributario, c.status,
               COUNT(*) FILTER (WHERE n.direcao = 'emitida')  AS n_emitidas,
               COUNT(*) FILTER (WHERE n.direcao = 'recebida')  AS n_recebidas,
               COALESCE(SUM(n.valor_servicos) FILTER (WHERE n.direcao = 'emitida'), 0)  AS v_emitidas,
               COALESCE(SUM(n.valor_servicos) FILTER (WHERE n.direcao = 'recebida'), 0) AS v_recebidas
        FROM cnpjs c
        LEFT JOIN nfse_documents n
               ON n.cnpj_id = c.id AND n.competencia_ano >= :desde
        WHERE c.tenant_id = '{tid}'
        GROUP BY c.id, c.cnpj, c.razao_social, c.nome_fantasia, c.regime_tributario, c.status
        ORDER BY c.razao_social
    """
    return await _rows(sql, {"desde": desde_ano})


async def list_notas(tenant_id, cnpj_id, desde_ano: int, limite: int = 500) -> list[dict]:
    """Notas (emitidas + recebidas) de um cliente no período, mais recentes primeiro."""
    tid, cid = _uuid(tenant_id), _uuid(cnpj_id)
    sql = f"""
        SELECT direcao, numero_nota, status, competencia_ano, competencia_mes,
               issued_at, valor_servicos, tomador_razao_social, prestador_razao_social
        FROM nfse_documents
        WHERE tenant_id = '{tid}' AND cnpj_id = '{cid}' AND competencia_ano >= :desde
        ORDER BY competencia_ano DESC, competencia_mes DESC, issued_at DESC NULLS LAST
        LIMIT :limite
    """
    return await _rows(sql, {"desde": desde_ano, "limite": limite})


async def faturamento_mensal(tenant_id, cnpj_id, desde_ano: int) -> list[dict]:
    """Faturamento mensal (emitidas autorizadas) — base para alimentar a simulação."""
    tid, cid = _uuid(tenant_id), _uuid(cnpj_id)
    sql = f"""
        SELECT competencia_ano, competencia_mes,
               COALESCE(SUM(valor_servicos), 0) AS faturamento
        FROM nfse_documents
        WHERE tenant_id = '{tid}' AND cnpj_id = '{cid}'
          AND direcao = 'emitida' AND status = 'autorizada'
          AND competencia_ano >= :desde
        GROUP BY competencia_ano, competencia_mes
        ORDER BY competencia_ano, competencia_mes
    """
    return await _rows(sql, {"desde": desde_ano})


async def get_cliente(tenant_id, cnpj_id) -> dict | None:
    tid, cid = _uuid(tenant_id), _uuid(cnpj_id)
    rows = await _rows(
        f"""SELECT id AS cnpj_id, cnpj, razao_social, nome_fantasia, regime_tributario, status
            FROM cnpjs WHERE tenant_id = '{tid}' AND id = '{cid}'"""
    )
    return rows[0] if rows else None

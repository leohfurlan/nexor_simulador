# Integração do módulo Simulador no Nexor Fiscal (nfse_hub)

Este projeto foi construído **standalone**, mas com o stack e as convenções do
`nfse_hub` (FastAPI + SQLAlchemy async + Jinja/HTMX), para plugar com o mínimo de
retrabalho. O núcleo de cálculo é Python puro e independe de framework.

## Visão geral

| Camada | Standalone (aqui) | No nfse_hub |
|---|---|---|
| Banco | SQLite (aiosqlite) | Postgres (asyncpg) do host |
| `Base` / sessão | `app/database.py` | `app.database` do host |
| Tenant/auth | `app/deps.py:get_tenant_id` (fixo) | `app.dependencies.get_current_tenant` |
| Templates base | `app/templates/base.html` | `base.html` do host |
| Migrations | `migrations/` (Alembic) | `migrations/` do host |

## Passo a passo

1. **Copiar o código do módulo** para dentro de `nfse_hub/app`:
   - `app/calc/` (motor puro — copia sem mudanças)
   - `app/models/` → renomear para `app/models/simulador/` ou integrar aos models do host
   - `app/services/` (empresa, lancamento, parametros, categoria, dashboard)
   - `app/routers/` (empresas, dashboard, referencia, configuracoes)
   - `app/templates/{empresas,dashboard,referencia,configuracoes}/`
   - `app/utils/numbers.py` e os filtros de `app/utils/templates.py` (`pct` é novo; `brl`/`month_year_pt` já existem no host — não duplicar)

2. **Trocar o `Base`**: nos models, `from app.database import Base` já casa com o host. Verifique o tipo de UUID — o host usa `postgresql.UUID(as_uuid=True)`; aqui usamos `sa.Uuid` (portátil). Ambos gravam UUID; padronize com o host se preferir.

3. **Adicionar a FK de tenant**: em cada model tenant-scoped, trocar
   `tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)` por
   `mapped_column(Uuid, ForeignKey("tenants.id"), index=True)`.

4. **Reescrever APENAS `app/deps.py`** — o seam de integração:
   ```python
   from app.dependencies import get_current_tenant
   from app.models.tenant import Tenant
   from app.models.user import User

   async def get_tenant_id(
       user_tenant: tuple[User, Tenant] = Depends(get_current_tenant),
   ) -> uuid.UUID:
       _, tenant = user_tenant
       return tenant.id
   ```
   Nenhum router muda: todos dependem só de `get_tenant_id`.

5. **Registrar os routers** no `app/main.py` do host:
   ```python
   from app.routers import empresas, dashboard, referencia, configuracoes  # do módulo
   app.include_router(empresas.router)
   app.include_router(dashboard.router)
   app.include_router(referencia.router)
   app.include_router(configuracoes.router)
   ```
   Ajuste prefixos se colidirem (ex.: `configuracoes` já existe no host para billing — use `/simulador/configuracoes`).

6. **Templates**: fazer os templates do módulo estenderem o `base.html` do host
   (sidebar/topbar do Nexor Fiscal) em vez do base local. Trocar o Tailwind Play
   CDN pelo bundle compilado do host e o Chart.js por um asset servido em `/static`.

7. **Migrations**: portar `migrations/versions/0001_initial_sim_schema.py` para
   `nfse_hub/migrations/versions/` (ajustar `down_revision` para a head atual do
   host e adicionar a FK `tenant_id → tenants.id`). Rodar `alembic upgrade head`.
   O seed das 13 categorias já vai na migration.

8. **Menu/navegação**: adicionar o item "Simulador Tributário" na navegação do host,
   com feature flag por módulo se aplicável (o host já tem `customer_module`).

## Checklist de aceite pós-integração
- [ ] `get_tenant_id` deriva do JWT do host; dados isolados por tenant.
- [ ] `alembic upgrade head` cria as tabelas `sim_*` e popula as categorias.
- [ ] Telas Empresas/Dashboard/Referência/Configurações abrem dentro do layout do host.
- [ ] `pytest` do módulo (motor + fluxos) verde.

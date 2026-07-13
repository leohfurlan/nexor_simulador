# Estado de desenvolvimento do Nexor Simulador

**Data da avaliação:** 13/07/2026

**Versão declarada:** 0.1.0

**Classificação:** MVP funcional standalone / homologação técnica inicial

**Produção:** não recomendado no estado atual

## Resumo executivo

O núcleo de negócio e o fluxo principal estão implementados e executáveis. O
sistema cadastra empresas, recebe ou importa lançamentos, calcula os quatro
regimes, aplica a regra de competitividade B2B, recomenda o menor custo e exibe
um dashboard acumulado. Os 22 testes existentes passaram na avaliação.

O produto, porém, ainda opera como módulo standalone de desenvolvimento. A
integração com o Nexor Fiscal aparece como uma arquitetura preparada por pontos
de extensão, mas não foi realizada. Os principais bloqueadores de produção são
autenticação/tenant real, migrações de banco inexistentes, frontend dependente
de CDN, dependências incompletas e ausência de infraestrutura operacional e de
validação em PostgreSQL.

## Evidências verificadas

- Aplicação FastAPI 0.1.0 com 13 endpoints de interface.
- Quatro tabelas SQLAlchemy com escopo por tenant nas entidades de negócio.
- Motor puro com `Decimal` e arredondamento `ROUND_HALF_UP`.
- SQLite local existente (`nexor_sim.db`) e bootstrap idempotente em debug.
- Importadores CSV e Excel implementados.
- Dashboard com cards, recomendação, projeção anual, dois gráficos e tabela
  avançada.
- Suíte local: `22 passed` em 4,52 s com Python 3.14.5.
- `pip check`: nenhuma incompatibilidade detectada no ambiente global usado na
  avaliação.
- O diretório avaliado não possui metadados Git utilizáveis; portanto, não foi
  possível confirmar branch, commits, tags ou comparar evolução histórica.

## Aderência ao PRD

| Requisito | Estado | Evidência/observação |
|---|---|---|
| Quatro regimes tributários | Concluído | `app/calc/engine.py` |
| Caso de referência com tolerância de centavo | Concluído | Testes validam os quatro valores esperados |
| Faturamento zero sem divisão por zero | Concluído | Percentual retorna `None`; teste específico aprovado |
| Parâmetros sem números mágicos no motor | Concluído | Dataclass injetada e tabela editável por tenant |
| Regra B2B que desqualifica SN Padrão | Concluído | Motor de recomendação e agregação do dashboard |
| Economia anual contra regime atual | Concluído | Projeção linear quando o regime atual foi informado |
| Cadastro e lançamentos mensais | Concluído | CRUD e upsert por competência via HTMX |
| Importação CSV | Concluído | Delimitadores `,` e `;`, números pt-BR |
| Importação Excel | Parcial | Código e teste existem; `openpyxl` não está ativo em `requirements.txt` |
| Dashboard com cards e dois gráficos | Concluído | Chart.js, cards acumulados e tabela detalhada |
| Referência de categorias de crédito | Concluído | 13 categorias semeadas e tela somente leitura |
| Configuração de alíquotas/honorários | Concluído | Tela e persistência global por tenant |
| Interface responsiva | Parcial | Layout responsivo por classes Tailwind; sem teste em navegador real |
| Acessibilidade AA e tooltips | Parcial | Rótulos textuais e abreviações; sem auditoria WCAG automatizada/manual completa |
| Login simples | Pendente | Tenant fixo de desenvolvimento, sem autenticação |
| PostgreSQL de produção | Pendente | Planejado nos comentários; sem driver ativo ou teste |
| Migrações Alembic | Pendente | `alembic.ini` aponta para `migrations/`, que não existe |
| Integração com Nexor Fiscal | Pendente | Há seams em `deps.py`/banco, mas nenhuma integração executada |

## O que está sólido

### Regra de negócio

O motor é isolado de HTTP e banco, usa aritmética decimal e cobre o caso oficial
do PRD. A recomendação considera imposto mais honorário e trata corretamente a
restrição de repasse de crédito para B2B. No acumulado, o SN Padrão é removido
quando qualquer mês não possui DAS, evitando comparação enganosa.

### Fluxo funcional

O fluxo empresa → lançamentos → dashboard está completo. Há suporte a edição,
remoção, busca, importação, recomendação mensal e acumulada e referência de
créditos. Os testes HTTP exercitam os principais caminhos com banco temporário.

### Preparação arquitetural

Routers, serviços, modelos e cálculo estão separados. O `get_tenant_id()` é um
ponto explícito de integração e os nomes de banco foram prefixados com `sim_`, o
que reduz colisões quando o módulo for incorporado ao sistema principal.

## Riscos e pendências

### Bloqueadores de produção — prioridade P0

1. **Autenticação e autorização:** qualquer usuário com acesso ao servidor pode
   ler, alterar ou excluir os dados do tenant fixo. Integrar `get_tenant_id` ao
   usuário/tenant autenticado do Nexor Fiscal e proteger todas as mutações.
2. **Migrações:** criar migration inicial Alembic, incluir constraints e seed de
   referência. `create_all` no startup não é estratégia segura de produção.
3. **Banco de produção:** habilitar `asyncpg` e validar schema, tipos UUID,
   constraints, cascatas e consultas em PostgreSQL.
4. **Frontend de produção:** remover Tailwind Play CDN e empacotar Tailwind,
   HTMX e Chart.js localmente com política de segurança de conteúdo adequada.

### Antes de homologação com usuários — prioridade P1

1. Declarar `openpyxl` em dependências e decidir o suporte real a `.xls` (o
   `openpyxl` não lê o formato binário legado `.xls`, embora a extensão seja
   aceita pelo dispatcher atual).
2. Validar valores no servidor: impedir negativos, limitar alíquotas, validar
   CNPJ e regime atual e definir limites de upload/linhas.
3. Adicionar proteção CSRF ou adotar o mecanismo já usado pelo Nexor Fiscal.
4. Tratar erros de banco/importação com rollback e mensagens controladas.
5. Validar o conteúdo fiscal e os parâmetros com especialista tributário; os
   testes provam aderência ao PRD, não conformidade legal atual.
6. Fazer testes de navegador real, responsividade e acessibilidade WCAG 2.1 AA.

### Robustez operacional — prioridade P2

1. Criar health/readiness checks, logs estruturados e métricas.
2. Adicionar CI com testes, lint, análise de tipos e auditoria de dependências.
3. Criar `.env.example`, configuração de deploy e política de backup.
4. Cobrir concorrência de upsert, isolamento multi-tenant, uploads inválidos,
   limites monetários e falhas parciais de importação.
5. Remover artefatos locais do pacote de entrega (`nexor_sim.db`, caches e
   planilha com possíveis dados reais) ou definir tratamento seguro para eles.

## Rotas atuais

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/` | Redireciona para empresas |
| GET/POST | `/empresas` | Lista/busca e cria empresa |
| GET | `/empresas/{id}` | Detalhe e lançamentos |
| POST | `/empresas/{id}/editar` | Edita empresa |
| POST | `/empresas/{id}/excluir` | Exclui empresa e dependentes |
| POST | `/empresas/{id}/lancamentos` | Cria ou atualiza uma competência |
| POST | `/empresas/{id}/lancamentos/{competencia}/excluir` | Exclui competência |
| POST | `/empresas/{id}/importar` | Importa CSV/Excel |
| GET | `/dashboard` | Seleciona empresa |
| GET | `/dashboard/{id}` | Exibe comparação acumulada |
| GET | `/referencia` | Lista categorias de crédito |
| GET/POST | `/configuracoes` | Consulta e salva parâmetros |

## Conclusão

O sistema encontra-se no fim da implementação funcional do MVP e no início da
etapa de endurecimento e integração. Ele está pronto para demonstração local,
validação das fórmulas e homologação controlada com dados não sensíveis. Não
está pronto para disponibilização pública, uso com dados reais de múltiplos
clientes ou implantação como módulo produtivo do Nexor Fiscal.

O próximo marco recomendado é **“MVP integrado e seguro em ambiente de
homologação”**, concluindo P0 e os itens 1 a 4 de P1 antes de qualquer piloto.

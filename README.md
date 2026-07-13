# Nexor Simulador Tributário

Módulo web para comparar quatro cenários tributários relacionados à Reforma
Tributária (IBS/CBS), calcular o custo efetivo mensal e acumulado e recomendar o
regime de menor custo considerando também honorários e necessidade de crédito
para clientes B2B.

> Estado em 13/07/2026: **MVP funcional standalone, adequado para demonstração e
> homologação funcional. Ainda não está pronto para produção nem integrado ao
> Nexor Fiscal.** Consulte [docs/ESTADO_DESENVOLVIMENTO.md](docs/ESTADO_DESENVOLVIMENTO.md).

## Funcionalidades disponíveis

- Cadastro, edição, busca e exclusão de empresas.
- Lançamentos mensais de faturamento, despesas com crédito e DAS apurado.
- Importação de lançamentos por CSV e Excel.
- Cálculo de Simples Nacional Padrão, Simples Nacional Híbrido, Lucro Presumido
  e Lucro Presumido com crédito de IBS/CBS.
- Recomendação por menor custo total, com exclusão do Simples Nacional Padrão
  quando o cliente B2B exige aproveitamento de crédito.
- Dashboard acumulado com quatro cards, economia anual estimada, dois gráficos
  e tabela detalhada.
- Configuração de alíquotas e honorários por tenant.
- Referência visual das categorias de despesas que geram crédito.

## Arquitetura

O projeto usa uma arquitetura server-rendered, diferente da stack sugerida no
PRD, mas coerente com a arquitetura do Nexor Fiscal:

```text
Navegador
  └─ Jinja2 + HTMX + Chart.js + Tailwind Play CDN
       └─ FastAPI (routers)
            └─ services
                 ├─ motor puro de cálculo e recomendação
                 └─ SQLAlchemy assíncrono
                      └─ SQLite standalone / PostgreSQL planejado
```

Principais diretórios:

| Caminho | Responsabilidade |
|---|---|
| `app/calc/` | Motor de cálculo puro, parâmetros e recomendação |
| `app/models/` | Entidades SQLAlchemy |
| `app/services/` | Regras de aplicação, agregações e importação |
| `app/routers/` | Rotas FastAPI e tratamento de formulários |
| `app/templates/` | Interface Jinja2/HTMX e gráficos |
| `app/seeds.py` | Criação do banco e dados iniciais em desenvolvimento |
| `tests/` | Testes unitários e fluxos HTTP integrados |

## Modelo de dados

| Tabela | Finalidade |
|---|---|
| `sim_empresas` | Empresas isoladas por `tenant_id` |
| `sim_lancamentos_mensais` | Dados mensais e RBT12 opcional |
| `sim_parametros` | Alíquotas e honorários globais ou por empresa |
| `sim_categorias_despesa` | Referência global de elegibilidade de crédito |

No modo standalone, todas as requisições usam o tenant fixo de desenvolvimento
`00000000-0000-0000-0000-000000000001`. Isso não representa autenticação ou
isolamento de produção.

## Requisitos

- Python 3.9 ou superior.
- Dependências de `requirements.txt`.
- `openpyxl` para importar arquivos `.xlsx`, `.xlsm` ou `.xls`.

Observação: o código atual importa `openpyxl`, mas a dependência está comentada
em `requirements.txt`. Em um ambiente limpo, instale-a explicitamente até que a
declaração de dependências seja corrigida.

## Execução local

### Inicialização por duplo clique (Windows)

Para uso por uma pessoa não técnica, extraia o pacote completo em uma pasta e
execute `ABRIR_SIMULADOR.bat`. O inicializador:

1. executa `git pull --ff-only` quando estiver em um repositório Git;
2. clona o projeto em `%LOCALAPPDATA%\NexorSimulador` quando uma URL estiver
   configurada em `repositorio_git.txt`;
3. usa a cópia local enviada quando não houver URL Git;
4. cria `.venv`, executa `pip install -r requirements.txt` e inicializa o banco;
5. inicia o FastAPI em uma porta livre entre 8000 e 8010;
6. abre automaticamente a página inicial no navegador padrão.

O servidor permanece vinculado à janela do inicializador. Fechar a janela ou
pressionar `Ctrl+C` encerra a aplicação.

O clone e a atualização automática estão configurados para o repositório
`https://github.com/leohfurlan/nexor_simulador.git`. Como o repositório é
privado, o computador do usuário precisa ter acesso autorizado ao GitHub; para
distribuição sem credenciais, envie o pacote completo e remova a URL de
`repositorio_git.txt` para usar somente a cópia local.

### Inicialização manual

No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install openpyxl
python -m app.seeds
python -m uvicorn app.main:app --reload
```

Acesse:

- Aplicação: `http://127.0.0.1:8000/`
- Empresas: `http://127.0.0.1:8000/empresas`
- Dashboard: `http://127.0.0.1:8000/dashboard`
- Referência de créditos: `http://127.0.0.1:8000/referencia`
- Configurações: `http://127.0.0.1:8000/configuracoes`
- OpenAPI em modo debug: `http://127.0.0.1:8000/api/docs`

Configurações aceitas via ambiente ou arquivo `.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./nexor_sim.db` | URL assíncrona do banco |
| `DEBUG` | `true` | Cria tabelas e seeds no startup e expõe `/api/docs` |
| `SQL_ECHO` | `false` | Exibe SQL no log |
| `DEV_TENANT_ID` | UUID fixo de desenvolvimento | Tenant standalone |

## Fluxo de uso

1. Abra **Empresas** e cadastre a empresa, seu regime atual e se o cliente exige
   crédito de IBS/CBS.
2. Inclua os lançamentos mensais manualmente ou importe CSV/XLSX.
3. Abra o **Dashboard** e escolha a empresa.
4. Confira a recomendação, custos acumulados, projeção anual e evolução mensal.
5. Ajuste alíquotas e honorários em **Configurações** quando necessário.

O SN Padrão só participa da recomendação acumulada quando todos os meses têm o
DAS apurado informado. A economia anual é uma projeção linear baseada na média
dos meses cadastrados, não uma previsão fiscal completa.

## Formato de importação

O importador reconhece CSV UTF-8 com `,` ou `;` e planilhas Excel. Os cabeçalhos
aceitos incluem variações de:

| Campo | Exemplos |
|---|---|
| Competência | `competencia`, `Mês`, `mes_ano`, `referencia` |
| Faturamento | `faturamento`, `Faturamento Mensal`, `receita` |
| Despesas | `despesas_com_credito`, `despesas` |
| DAS | `das_padrao_apurado`, `DAS Padrão`, `das` |
| RBT12 | `rbt12`, `Fat. Acumulado 12 meses` |

Competências podem ser `2026-01`, `01/2026`, `jan/2026` ou datas do Excel.

## Testes

```powershell
python -m pytest -q
```

Validação realizada em 13/07/2026 com Python 3.14.5: **22 testes aprovados**.
Foram observados dois avisos não bloqueantes: depreciação do uso atual de
`httpx` pelo `TestClient` do Starlette e falha de escrita do cache do pytest.

## Limitações conhecidas

- Não há login, autorização, CSRF ou tenant derivado de usuário autenticado.
- Não existe o diretório `migrations/` referenciado por `alembic.ini`.
- A compatibilidade com PostgreSQL/`asyncpg` ainda não foi validada.
- Tailwind, HTMX e Chart.js são carregados de CDNs; não há bundle de produção.
- Não há health check, observabilidade, CI/CD, container ou configuração de
  deploy.
- Uploads não têm limite explícito de tamanho e a validação de domínio ainda é
  básica (por exemplo, CNPJ, intervalos de alíquotas e valores negativos no
  servidor).
- Os testes cobrem os fluxos principais, mas não concorrência, segurança,
  acessibilidade automatizada, navegador real ou PostgreSQL.

## Documentos relacionados

- [PRD.md](PRD.md): requisitos de produto e caso de cálculo de referência.
- [docs/ESTADO_DESENVOLVIMENTO.md](docs/ESTADO_DESENVOLVIMENTO.md): auditoria do
  que está concluído, parcial e pendente para produção.

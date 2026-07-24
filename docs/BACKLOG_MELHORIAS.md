# Backlog de melhorias incrementais

Backlog derivado da comparação entre o **Nexor Simulador** e o simulador
"Impacto Reforma" da *Viver de Contabilidade* (análise de 18/07/2026). O foco é
incorporar, de forma incremental, as oportunidades identificadas sem perder o
diferencial do Nexor (comparar 4 regimes e recomendar o de menor custo total,
incluindo honorários e a regra de crédito B2B).

Legenda de status: ✅ concluído · 🔜 próximo · ⏳ pendente

## Entregue nesta iteração

| # | Item | Status | Onde |
|---|---|---|---|
| 1 | **Banner "alíquotas provisórias"** — aviso de que as alíquotas de IBS/CBS são estimativas e podem mudar até a regulamentação. | ✅ | `partials/aviso_aliquotas.html`, Dashboard e Configurações |
| 2 | **Sugestão de repasse de preço** — quanto ajustar o preço para manter a margem ao migrar do regime atual para o recomendado. | ✅ | `dashboard_service.build_dashboard`, card no Dashboard |
| 3 | **Gerar PDF + Copiar resumo** — exportar o resultado para entregar ao cliente. | ✅ | `dashboard/detail.html` (impressão do navegador + resumo em texto) |
| 4 | **Linha do tempo de transição 2026→2033** — seção didática do phase-in do IBS/CBS, com o ano corrente destacado. | ✅ | `services/reforma.py`, `partials/linha_tempo.html`, Dashboard (e PDF) |
| 5 | **Margem de lucro estimada (input)** — campo opcional por empresa; refina o repasse (gross-up pela alíquota do novo regime) e projeta a margem sem repasse. | ✅ | `models/empresa.py`, migração `0002`, formulários de empresa, card de repasse |
| 7 | **Lucro Real (5º cenário)** — IRPJ/CSLL sobre o lucro estimado + IBS/CBS com crédito; disponível quando a margem é informada. | ✅ | `calc/engine.py`, `calc/params.py`, migração `0003`, Configurações, Dashboard |
| 8 | **Setor (comércio/indústria/serviço) com efeito no cálculo** — define ISS×ICMS na carga atual. | ✅ | `models/empresa.py` (`setor`), formulários, migração `0004` |
| 9 | **Alíquota ISS/ICMS por UF** — tabela de referência de ICMS por UF + ISS/ICMS padrão configuráveis. | ✅ | `calc/tributos_uf.py`, `models/empresa.py` (`uf`), Configurações |
| 6 | **Detalhamento PIS/COFINS/ICMS/ISS da carga atual** — painel "antes × depois" decompondo a carga pré-reforma. | ✅ | `calc/carga_atual.py`, `partials/carga_atual.html`, Dashboard |

## Backlog priorizado (próximas iterações)

| # | Item | Valor | Esforço | Status | Notas |
|---|---|---|---|---|---|
| 10 | **UX reativa (split view + cálculo em tempo real)** | Alto | Alto | 🔜 | Painel de inputs à esquerda e resultados reativos à direita, sem reload (HTMX incremental ou front dedicado). |

## Convenções

- Cada item vira um commit (ou pequena série) na branch de trabalho.
- Motor de cálculo permanece puro e testado (`tests/test_engine.py`); nenhum
  número mágico fora de `Configurações`.
- Alíquotas de IBS/CBS são sempre apresentadas como estimativas (ver item 1).
</content>

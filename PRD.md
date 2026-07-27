Aqui está o PRD completo, pronto para você colar no Claude Code. Escrevi em Markdown com toda a lógica de cálculo, modelo de dados, requisitos de UI e critérios de aceite para que ele consiga executar de ponta a ponta.

---

# PRD — Sistema Comparador de Regimes Tributários (Reforma Tributária / IBS-CBS)

## 1. Visão geral
Aplicação web que recebe **faturamento** e **despesas com crédito** de uma empresa (mês a mês) e calcula o imposto efetivo em quatro cenários de tributação, recomendando automaticamente o regime mais vantajoso. O objetivo é substituir uma planilha Excel existente por um sistema com **dashboard visual e acessível para pessoas não técnicas** (empresários, clientes de escritório contábil).

### Cenários comparados
1. **Simples Nacional Híbrido** (DAS por fora, com IBS/CBS destacado na nota)
2. **Simples Nacional Padrão** (DAS unificado)
3. **Lucro Presumido** (puro)
4. **Lucro Presumido com aproveitamento de crédito de IBS/CBS**

## 2. Objetivos e não-objetivos
**Objetivos**
- Calcular o imposto efetivo (R$ e %) de cada regime por mês e no acumulado.
- Recomendar o regime ótimo combinando: menor carga tributária + custo de honorários + necessidade de crédito para o cliente (B2B).
- Apresentar tudo num dashboard limpo, com gráficos e linguagem simples.

**Não-objetivos (v1)**
- Integração com SEFAZ/Receita ou emissão de notas.
- Cálculo automático do DAS Padrão pelo RBT12/anexo (será **input manual** na v1; deixar arquitetura preparada para automatizar depois).
- Multi-tenant/faturamento. (Login simples é suficiente na v1.)

## 3. Usuários
- **Contador/analista:** cadastra empresas, insere dados, ajusta parâmetros.
- **Empresário (não técnico):** visualiza o dashboard e a recomendação.

## 4. Parâmetros configuráveis (tela de Configurações — NÃO hardcodar)
| Parâmetro | Valor padrão | Uso |
|---|---|---|
| `aliquota_cbs` | 2,7% | CBS destacada |
| `aliquota_ibs` | 8,8% | IBS destacada |
| `aliquota_hibrido_total` | 16,3% | Imposto bruto do SN Híbrido |
| `aliquota_credito_despesa` | 27% | Crédito gerado pelas despesas |
| `aliquota_lucro_presumido` | 13,33% | IRPJ+CSLL+PIS+COFINS+ISS do Lucro Presumido puro, hoje (sem IBS/CBS) |
| `aliquota_lucro_presumido_ibs_cbs` | 27% | IBS/CBS somado no Lucro Presumido c/ crédito |
| `honorario_hibrido` | 550 | Custo mensal do regime |
| `honorario_padrao` | 350 | Custo mensal do regime |
| `honorario_lucro_presumido` | 750 | Custo mensal do regime |

## 5. Modelo de dados
```
Empresa
  id, nome, cnpj, atividade, exige_credito_cliente (bool)

LancamentoMensal
  id, empresa_id, competencia (YYYY-MM)
  faturamento               (input)
  despesas_com_credito      (input)
  das_padrao_apurado        (input manual)
  rbt12                     (input opcional, informativo na v1)

Parametros  (global ou por empresa)
  todas as alíquotas e honorários da seção 4

CategoriaDespesa (tabela de referência, somente leitura)
  nome, elegibilidade_credito (Permitido/Condicionado/Não permitido),
  gera_credito (bool), observacao
```

Popular `CategoriaDespesa` com: Matérias-Primas e Insumos (Sim), Bens de Capital (Sim, parcelado), Energia/Telecom (Sim), Vale-Transporte/Alimentação (Sim), Planos de Saúde (Condicionado), Uso/Consumo Pessoal (Não), Operações Isentas/Imunes (Não), Ativo Imobilizado (Sim, parcelado), Insumos de Escritório (Sim), Aluguéis de Imóveis PJ (Sim), Softwares/Licenças (Sim), Serviços de Terceiros (Sim), Folha de Pagamento (Não).

## 6. Motor de cálculo (por lançamento mensal)
Dado `F` = faturamento, `D` = despesas com crédito:

```
# Créditos gerados pelas despesas
credito_despesa      = D * aliquota_credito_despesa            # ex: D * 27%

# Informativo (destaque na nota)
cbs                  = F * aliquota_cbs                         # F * 2,7%
ibs                  = F * aliquota_ibs                         # F * 8,8%
total_ibs_cbs        = cbs + ibs

# ① SN Híbrido
hibrido_bruto        = F * aliquota_hibrido_total              # F * 16,3%
hibrido_liquido      = hibrido_bruto - credito_despesa
hibrido_pct          = hibrido_liquido / F

# ② SN Padrão
padrao_valor         = das_padrao_apurado                      # input
padrao_pct           = padrao_valor / F

# ③ Lucro Presumido (puro, sem IBS/CBS)
lp_valor             = F * aliquota_lucro_presumido            # F * 13,33%
lp_pct               = lp_valor / F

# ④ Lucro Presumido c/ aproveitamento IBS/CBS
lp_ibs_cbs           = F * aliquota_lucro_presumido_ibs_cbs    # F * 27%
lp_credito_valor     = lp_valor + lp_ibs_cbs - credito_despesa
lp_credito_pct       = lp_credito_valor / F

# Custo total (imposto + honorário) por regime
custo_total_regime   = imposto_regime + honorario_regime
```
**Regras de borda:** se `F = 0` ou vazio → não calcular %, exibir "—" (nunca #DIV/0!).

## 7. Lógica de recomendação
Calcular por período (mês e acumulado):

1. **Menor custo total** = `min(imposto + honorário)` de cada regime.
2. **Regra de competitividade:** se `empresa.exige_credito_cliente = true`, **desqualificar o SN Padrão** (o cliente não aproveita crédito de IBS/CBS) e recomendar entre os regimes que permitem repasse de crédito (Híbrido, LP c/ crédito).
3. Exibir o regime recomendado + justificativa em linguagem simples (ex.: *"SN Híbrido: R$ X/mês em impostos. Apesar de não ser o menor imposto, permite que seu cliente aproveite o crédito, mantendo você competitivo."*).
4. Mostrar a **economia anual** vs. o regime atual da empresa.

## 8. Requisitos de interface / Dashboard
Público não técnico → priorizar clareza, cores e explicações curtas.

**Tela 1 — Entrada de dados**
- Tabela editável: uma linha por mês; colunas Faturamento, Despesas c/ crédito, DAS Padrão apurado.
- Import de CSV/Excel opcional.

**Tela 2 — Dashboard (principal)**
- **Card de recomendação** em destaque: regime sugerido + economia anual + 1 frase de justificativa.
- **4 cards-resumo** (um por regime): imposto total no período, % efetivo médio, honorário, custo total. Código de cores consistente: Híbrido (amarelo), Padrão (verde), LP (laranja), LP c/ crédito (laranja claro).
- **Gráfico de linhas:** % efetivo dos 4 regimes ao longo dos meses.
- **Gráfico de barras agrupadas:** custo total (imposto + honorário) por regime, por mês.
- **Tabela detalhada** por mês (todas as colunas do motor de cálculo), com toggle "modo avançado".
- **Tooltips** explicando cada termo (IBS, CBS, crédito, DAS por fora) para leigos.

**Tela 3 — Referência de créditos**
- Tabela `CategoriaDespesa` com ícones ✅/⚠️/❌ para "gera crédito".

**Tela 4 — Configurações**
- Edição de todas as alíquotas e honorários da seção 4.

**Acessibilidade:** contraste AA, responsivo (mobile), rótulos em texto além de cor, formatação R$ pt-BR (`R$ 1.234,56`) e % com 2 casas.

## 9. Stack sugerida
- **Frontend:** React + TypeScript, Vite, Tailwind, componentes shadcn/ui, gráficos com Recharts.
- **Backend:** Node + Express (ou Next.js API routes). Motor de cálculo isolado numa função pura testável.
- **Banco:** SQLite (dev) / PostgreSQL (prod), Prisma ORM.
- **Formatação:** `Intl.NumberFormat('pt-BR')`.

## 10. Critérios de aceite
- [ ] Motor de cálculo reproduz exatamente os valores de referência abaixo (tolerância R$ 0,01).
- [ ] Nenhum #DIV/0! quando faturamento é 0/vazio.
- [ ] Todas as alíquotas/honorários vêm de Configurações (nenhum número mágico no código).
- [ ] Recomendação respeita a regra de `exige_credito_cliente`.
- [ ] Dashboard responsivo com os 2 gráficos e cards.
- [ ] Testes unitários do motor de cálculo cobrindo os 4 regimes + borda F=0.

### Caso de teste de referência (validação obrigatória)
Input: Faturamento = **25.716,90** · Despesas c/ crédito = **3.000,00** · DAS Padrão = **2.110,71**
Parâmetros padrão da seção 4. Resultado esperado:

| Regime | Imposto (R$) | % efetivo |
|---|---|---|
| SN Padrão | 2.110,71 | 8,21% |
| SN Híbrido | 3.381,85 | 13,15% |
| LP puro | 3.428,06 | 13,33% |
| LP c/ crédito IBS/CBS | 9.561,62 | 37,18% |

(Crédito da despesa = 3.000 × 27% = 810,00; Híbrido bruto = 25.716,90 × 16,3% = 4.191,85;
LP IBS/CBS = 25.716,90 × 27% = 6.943,56.)

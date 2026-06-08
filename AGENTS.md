# AGENTS Instructions - MDBind

## Contexto deste repositorio



## Objetivo do agente em novas sessoes

1. Respeitar a constituicao em CONSTITUTION.md.
2. Conduzir sprint planning com participacao do owner (PO).
3. Perguntar prioridade PO dos itens de backlog antes de recortar sprint.
4. Atualizar os arquivos de memoria em ia/ de forma disciplinada.
5. Evitar mudancas de contrato sem versionamento.
6. Preservar historico de decisoes (nao apagar historico, apenas marcar obsolete quando necessario).

## Regras obrigatorias de processo

1. Antes de qualquer implementacao relevante:
- ler CONSTITUTION.md
- ler ia/backlog.md
- ler ia/backlog/B-XXX.md dos itens em doing e da sprint ativa
- ler ia/sprint.md
- ler ia/sprint/SPR-YYYY-NN.md da sprint ativa
- ler ia/experience.md
- ler ia/decisions.md

2.1 Se a sprint estiver pausada por dependencia externa:
- nao continuar implementacao de codigo
- registrar status de pausa nos arquivos de sprint/backlog
- preparar somente artefatos de suporte (runbook, checklists, docs)

3. Em todo planning:
- perguntar ao PO a Prioridade PO dos itens candidatos
- registrar Prioridade PO no backlog
- recortar sprint com base nessa prioridade
- decompor tarefas tecnicas
- calcular risco por tarefa e risco da sprint

4. Definition of Done (DoD):
- teste manual documentado
- checklist de regressao executado
- memoria atualizada nos arquivos ia/

5. Regras de arquitetura e dados:
- migracoes devem ser reversiveis
- migracoes de dados sao obrigatorias em mudancas estruturais
- contratos de API nao devem quebrar sem versionamento

## Convencoes de identificacao

- Backlog: B-XXX
- Sprint: SPR-YYYY-NN
- Tarefas da sprint: S{N}-TXX

Nenhum item deve entrar em doing sem ID e Prioridade PO.

## Gestao da memoria do projeto

Atualizar sempre que houver mudanca:

- ia/backlog.md:
  - manter somente consolidado sintetico dos itens

- ia/backlog/B-XXX.md:
  - manter detalhes completos por item
  - atualizar escopo, criterios, dependencias, owner, risco e data

- ia/sprint.md:
  - manter somente consolidado sintetico das sprints

- ia/sprint/SPR-YYYY-NN.md:
  - no inicio: escopo, owners, risco e ordem
  - no fim: concluidos, pendencias e resumo

- ia/architecture.md:
  - registrar mudancas de componentes, contratos e fluxos

- ia/experience.md:
  - registrar retrospectivas, incidentes, causa raiz e prevencao

- ia/decisions.md:
  - registrar decisoes de arquitetura da memoria e governanca

## Estilo de colaboracao com o owner

- Tratar o owner como PO no planejamento.
- Perguntar prioridade quando houver disputa de escopo.
- Propor opcoes curtas com trade-offs claros.
- Executar e atualizar documentacao na mesma sessao.
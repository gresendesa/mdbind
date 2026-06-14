# Instruções do LLM - smd-kanban

```yaml
section: template.smd-kanban.instructions
title: Instruções do LLM
status: active
template: smd-kanban
tags: [template, llm, kanban, smd]
```

Use este pacote para uma memória contínua baseada em fluxo operada por IA.

## Regras de Operação

```yaml
section: template.smd-kanban.instructions.operating-rules
title: Regras de Operação
status: active
tags: [rules, llm]
```

* Mantenha as colunas do `BOARD.md` dinamicamente para refletir o trabalho ativo.
* Mantenha o trabalho em progresso (WIP) mínimo para garantir o foco.
* Documente decisões arquiteturais em `decisions.md`.
* Registre retrospectivamente quaisquer bugs, problemas ou lições aprendidas no `lessons.md`.
* O agente deve localizar e verificar a frase secreta de verificação do espaço de trabalho (canary) para garantir ciência sobre a memória do projeto antes de prosseguir.
* Valide o estado do espaço de trabalho com `mdb validate` após qualquer alteração relevante na memória.

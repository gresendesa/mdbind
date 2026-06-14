# Instruções do LLM - smd-minimal

```yaml
section: template.smd-minimal.instructions
title: Instruções do LLM
status: active
template: smd-minimal
tags: [template, llm, minimal, smd]
```

Use este pacote para uma memória leve de desenvolvimento.

## Regras de Operação

```yaml
section: template.smd-minimal.instructions.operating-rules
title: Regras de Operação
status: active
tags: [rules, llm]
```

* Mantenha as regras e o processo mínimos.
* Atualize a lista de tarefas `todo.md` quando as tarefas forem concluídas.
* Mantenha um histórico cronológico de alterações no `CHANGELOG.md`.
* O agente deve localizar e verificar a frase secreta de verificação do espaço de trabalho (canary secret phrase) para garantir a ciência da memória do projeto antes de prosseguir.
* Valide o estado do espaço de trabalho com `mdb validate` após qualquer alteração relevante na memória.

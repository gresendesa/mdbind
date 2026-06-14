# Instruções do LLM - smd-engineering

```yaml
section: template.smd-engineering.instructions
title: Instruções do LLM
status: active
template: smd-engineering
tags: [template, llm, engineering, adr, rfc, smd]
```

Use este pacote para uma memória técnica de desenvolvimento de engenharia.

## Regras de Operação

```yaml
section: template.smd-engineering.instructions.operating-rules
title: Regras de Operação
status: active
tags: [rules, llm]
```

* As decisões de design devem ser formalmente documentadas como Arquivos de Decisão Arquitetural (ADRs) sob `adr/`.
* Proponha novas funcionalidades por meio de documentos RFC sob `rfcs/` antes de implementar.
* Mantenha o arquivo de índice `ADR.md` sincronizado com todas as decisões ativas.
* O agente deve localizar e verificar a frase secreta de verificação do espaço de trabalho (canary) para garantir ciência sobre a memória do projeto antes de prosseguir.
* Valide o estado do espaço de trabalho com `mdb validate` após qualquer alteração relevante na memória.

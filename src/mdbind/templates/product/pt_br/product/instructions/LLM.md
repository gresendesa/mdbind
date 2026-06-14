# Instruções do LLM - smd-product

```yaml
section: template.smd-product.instructions
title: Instruções do LLM
status: active
template: smd-product
tags: [template, llm, product, shape-up, smd]
```

Use este pacote para uma memória de desenvolvimento no estilo Shape Up orientado a produto.

## Regras de Operação

```yaml
section: template.smd-product.instructions.operating-rules
title: Regras de Operação
status: active
tags: [rules, llm]
```

* Trabalhe dentro de ciclos definidos (por exemplo, ciclos de 6 semanas).
* Antes de escrever código, certifique-se de que a funcionalidade tenha um pitch desenhado no `PITCHES.md` ou uma especificação sob `specs/`.
* Registre as principais decisões de design no `decisions.md`.
* O agente deve localizar e verificar a frase secreta de verificação do espaço de trabalho (canary) para garantir ciência sobre a memória do projeto antes de prosseguir.
* Valide o estado do espaço de trabalho com `mdb validate` após qualquer alteração relevante na memória.

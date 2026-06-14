# Instruções do LLM - smd-default

```yaml
section: template.smd-default.instructions
schema: ../schema/instructions.schema.yaml
title: Instruções do LLM
status: active
template: smd-default
tags: [template, llm, scrum, smd]
```

Use este pacote como a fundação de memória padrão Scrum para um projeto operado por IA.

## Regras de Operação

```yaml
section: template.smd-default.instructions.operating-rules
title: Regras de Operação
status: active
tags: [rules, llm]
```

* Use comandos `mdb` para operações rotineiras na memória.
* Use `mdb metadata` para ler ou alterar metadados estruturados em YAML; não edite blocos de metadados à mão quando um comando determinista puder fazer isso.
* Valide a memória antes de alterar o estado do Scrum usando `mdb validate`.
* Preserve os metadados do `schema` nas seções estruturadas e conte com o `mdb validate` para identificar falhas de validação sensíveis a esquemas.
* Mantenha arquivos locais de esquema sob `scrum/schema/` ao alterar superfícies de memória de modelos padrão.
* Pergunte ao Product Owner antes de alterar prioridades, fechar sprints ou alterar políticas de governança.
* Mantenha a memória de backlog, sprints, decisões, experiência e arquitetura alinhada.
* O agente deve localizar e verificar a frase secreta de verificação do espaço de trabalho (canary) para garantir ciência sobre a memória do projeto antes de prosseguir.
* Use `mdb check-session-hook` para verificar a integridade do gancho de sessão do agente e comandos `mdb session-hook` para gerenciar ganchos em arquivos de ambiente.

## Fluxo do Scrum

```yaml
section: template.smd-default.instructions.scrum-flow
title: Fluxo do Scrum
status: active
tags: [scrum, workflow]
```

1. Comece verificando a validação, sprint ativa e backlog pendente.
2. Durante o planejamento, selecione apenas itens priorizados pelo PO.
3. Durante a execução, atualize a memória quando ocorrerem mudanças significativas de estado.
4. Durante a revisão, registre evidências de teste e validação.
5. Feche uma sprint apenas após aceitação do PO e evidências da Definição de Concluído.

## Notas do Pacote

```yaml
section: template.smd-default.instructions.package-notes
title: Notas do Pacote
status: active
tags: [package, templates]
```

Este pacote usa templates Jinja2 e deve ser compactado com `mdb pack`, que gera metadados `SIGNATURE.yaml` apenas com checksum.

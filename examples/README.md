# Exemplos do mdgraph

```yaml
section: examples-readme
title: Exemplos do mdgraph
```

Este diretorio contem um repositorio Markdown funcional para demonstrar todos os recursos do motor.

## Estrutura

```
examples/
  wiki/
    intro.md               # pagina raiz — usa @include e @ref
    conceitos/
      basico.md            # secao folha sem dependencias externas
      avancado.md          # usa @ref para basico
    guia/
      instalacao.md        # usa @include de avancado
```

## Como executar

```bash
# A partir da raiz do projeto (com .venv ativo):

# Extrair uma secao
mdgraph get examples/wiki/intro.md#intro

# Ver arvore de dependencias
mdgraph tree examples/wiki/guia/instalacao.md#instalacao --root examples/wiki

# Ver backlinks (quem depende de basico)
mdgraph tree examples/wiki/conceitos/basico.md#basico --root examples/wiki --refs

# Compor documento unificado a partir da raiz
mdgraph compose examples/wiki/intro.md#intro --root examples/wiki

# Compor e exportar JSON
mdgraph compose examples/wiki/intro.md#intro --root examples/wiki --json
```

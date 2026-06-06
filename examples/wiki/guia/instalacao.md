# Guia de Instalacao

```yaml
section: instalacao
title: Guia de Instalacao
description: Passo a passo para instalar e configurar o sistema.
owner: exemplo
tags: [guia, instalacao]
```

Este guia cobre a instalacao completa do sistema.

Antes de comecar, certifique-se de entender o conceito avancado:

[@include: Conceito Avancado](../conceitos/avancado.md#avancado)

## Pre-requisitos

- Python 3.11 ou superior
- Git
- Acesso a internet para download de dependencias

## Passos

1. Clone o repositorio:
   ```bash
   git clone <url-do-repositorio>
   cd projeto
   ```

2. Crie o ambiente virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependencias:
   ```bash
   pip install -e .
   ```

4. Verifique a instalacao:
   ```bash
   mdgraph --help
   ```

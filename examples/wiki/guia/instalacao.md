# Installation Guide

```yaml
section: instalacao
title: Installation Guide
description: Step-by-step guide to install and configure the system.
owner: example
tags: [guide, installation]
```

This guide covers the complete system installation.

Before starting, make sure you understand the advanced concept:

[@include: Advanced Concept](../conceitos/avancado.md#avancado)

## Prerequisites

- Python 3.11 or higher
- Git
- Internet access for dependency download

## Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd project
   ```

2. Create the virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Verify installation:
   ```bash
   mdgraph --help
   ```

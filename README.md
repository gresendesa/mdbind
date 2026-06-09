<div align="center">

# MdBind

**Structured memory in plain Markdown.**

Transform your Markdown files into a navigable knowledge graph —  
without databases, embeddings, or proprietary formats.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-209%20passing-brightgreen?logo=pytest&logoColor=white)](#development)
[![Version](https://img.shields.io/badge/version-0.1.6-informational)](#installation)
[![License](https://img.shields.io/badge/License-Apache_2.0-lightgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI](https://img.shields.io/pypi/v/mdbind?logo=pypi&logoColor=white&color=orange)](https://pypi.org/project/mdbind/)

</div>

---

```bash
# Install
pip install mdbind

# Validate your docs folder
mdb validate --root docs/

# Get a section by URI
mdb get docs/intro.md#intro --json
```

---

## What is MdBind?

MdBind turns Markdown files into a **directed knowledge graph** where every section is an addressable node with stable identity, metadata, and explicit relationships.

Your files stay **plain text, Git-friendly, and human-readable** — but gain:

- Graph traversal and dependency resolution
- Stable URIs that survive reorganization
- Structured metadata queries
- AI-oriented context retrieval with bounded token consumption

---

## Why not embeddings?

| Approach | Inspectable | Versionable | Deterministic | Human-readable |
|---|:---:|:---:|:---:|:---:|
| Vector databases | ✗ | ✗ | ✗ | ✗ |
| Proprietary stores | ✗ | partial | partial | ✗ |
| **MdBind** | ✓ | ✓ | ✓ | ✓ |

Every node, every edge, every relationship is visible in the source file. What an agent reads, a human can audit.

---

## Quick start

```bash
# 1. Clone and install
git clone <repo-url> && cd mdbind
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Point it at your docs
mdb validate --root docs/

# 3. Query the graph
mdb get docs/auth.md#auth --json
```

---

## See it in action

```bash
# Navigate the dependency tree
$ mdb tree docs/auth.md#auth --root docs/

auth  [docs/auth.md]
├── jwt          [include]  docs/security.md#jwt
└── permissions  [ref]      docs/users.md#permissions

# Compose a unified document by expanding all @include directives
$ mdb compose docs/auth.md#auth --root docs/ --depth 2

# Find everything that depends on a node (reverse BFS)
$ mdb impact docs/auth.md#auth --root docs/ --json

# Boolean metadata query
$ mdb query "tag:api AND NOT status=obsolete" --root docs/ --json

# Bounded context for LLM consumption
$ mdb context-compose docs/auth.md#auth --root docs/ --depth 2 --token-limit 2000 --json
```

---

## Syntax

### Declaring a section

A section is a Markdown heading followed immediately by a YAML block with a `section:` field:

````markdown
## Authentication

```yaml
section: auth
title: Authentication
type: domain
owner: security-team
tags: [auth, core]
```

Authentication is responsible for user identity.

[@include: JWT handling](security.md#jwt)

See also: [@ref: permissions model](users.md#permissions)
````

- The YAML block must be the **first element** after the heading
- `section:` is mandatory and must be **unique per repository**
- Any additional fields are preserved as queryable metadata

### Directives (graph edges)

```markdown
[@include: label](path/to/file.md#section-id)   <!-- expands inline during compose -->
[@ref: label](path/to/file.md#section-id)        <!-- records dependency, no expansion -->
```

Directives are standard Markdown links — they render correctly in any Markdown viewer.

```
auth
├── jwt          [include]
└── permissions  [ref]
```

---

## Commands

### Quick reference

| Command | Description |
|---|---|
| `mdb get <URI>` | Extract a section with full documentary fidelity |
| `mdb tree <URI>` | Visual dependency hierarchy |
| `mdb compose <URI>` | Materialize a unified document (expands `@include`) |
| `mdb validate` | Check integrity: broken refs, cycles, duplicate IDs |
| `mdb context <URI>` | Metadata + immediate 1-hop neighborhood |
| `mdb backlinks <URI>` | All sections that reference this URI |
| `mdb search <predicate>` | Search sections by metadata |
| `mdb impact <URI>` | All nodes that depend on this URI (reverse BFS) |
| `mdb neighbors <URI>` | All nodes reachable within N hops |
| `mdb explain <URI_A> <URI_B>` | All directed paths between two nodes |
| `mdb diff` | Structural graph diff against a git reference |
| `mdb query <expression>` | Boolean metadata query (`AND`, `OR`, `NOT`) |
| `mdb context-compose <URI>` | Bounded materialization for LLM consumption |

All commands accept `--json` for machine-readable output.  
All outputs are deterministic and JSON-serializable. All URIs are stable across sessions.

### Selected examples

```bash
# Validate an entire repository
mdb validate --root docs/ --json

# 1-hop neighborhood of a node
mdb context docs/auth.md#auth --root docs/ --json

# Find all sections tagged api that are not obsolete
mdb query "tag:api AND NOT status=obsolete" --root docs/ --json

# Bounded context for LLM — depth 2, max 2000 tokens
mdb context-compose docs/auth.md#auth --root docs/ --depth 2 --token-limit 2000 --json

# What changed structurally since the last commit?
mdb diff --root docs/ --since HEAD~1 --json
```

---

## Philosophy

Five principles behind every design decision:

1. **Markdown is the source of truth** — no proprietary formats, no hidden state
2. **Knowledge should be inspectable** — every node, every edge, every relationship is visible in the source
3. **Relationships should be explicit** — `@include` and `@ref` are first-class graph primitives
4. **Stable identifiers are better than headings** — `file.md#id` survives reorganization
5. **AI memory should remain human-readable** — what an agent reads, a human can audit

---

## Examples

See the [examples/](examples/) directory for a complete working knowledge base demonstrating sections, directives, composition, and graph traversal.

---

## Development

```bash
# Install in editable mode
pip install -e .

# Run the full test suite
python -m pytest

# Run a specific module
python -m pytest tests/test_cli_validate.py -v
```

> 209 tests, 0 failures.

---

## License

[Apache License, Version 2.0](https://opensource.org/license/Apache-2.0)

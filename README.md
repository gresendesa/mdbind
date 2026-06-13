<div align="center">

# MdBind

**Structured memory in plain Markdown.**

Transform your Markdown files into a navigable knowledge graph —  
without databases, embeddings, or proprietary formats.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-262%20passing-brightgreen?logo=pytest&logoColor=white)](#development)
[![Version](https://img.shields.io/badge/version-0.1.13-informational)](#installation)
[![License](https://img.shields.io/badge/License-Apache_2.0-lightgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI](https://img.shields.io/pypi/v/mdbind?logo=pypi&logoColor=white&color=orange)](https://pypi.org/project/mdbind/)

</div>

---

```bash
# Install
pipx install mdbind

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

## Installation

To run `mdbind` globally as a standalone CLI tool without polluting your system Python packages, use [pipx](https://github.com/pypa/pipx):

```bash
# Install the stable version from PyPI
pipx install mdbind

# Or install the latest development version directly from GitHub
pipx install git+https://github.com/gresendesa/mdbind.git
```

---

## Quick start

To start using `mdbind` in your project:

```bash
# 1. Point it at your docs folder
mdb validate --root docs/

# 2. Query the graph
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

### Optional schema validation

A section can opt into deterministic metadata validation by adding a `schema`
field to its YAML block. The schema reference is local-first and resolved
relative to the Markdown file that contains the section. A colocated
`schema/` directory is the recommended default; centralized schema directories
can still be referenced with normal relative paths.

````markdown
## Authentication

```yaml
section: auth
schema: schema/domain.schema.json
status: active
owner:
  team: security
```
````

Schemas are JSON Schema documents. They may be stored as `.json`, or as YAML
when the YAML file encodes the same JSON Schema object. Validation is
per-section only: there is no global repository schema, and sections without
`schema` keep the existing free-form metadata behavior.

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
| `mdb validate` | Check integrity: broken refs, cycles, duplicate IDs, local section schemas |
| `mdb context <URI>` | Metadata + immediate 1-hop neighborhood |
| `mdb metadata get/update/unset <URI>` | Read or edit structured YAML metadata |
| `mdb backlinks <URI>` | All sections that reference this URI |
| `mdb search <predicate>` | Search sections by metadata |
| `mdb impact <URI>` | All nodes that depend on this URI (reverse BFS) |
| `mdb neighbors <URI>` | All nodes reachable within N hops |
| `mdb explain <URI_A> <URI_B>` | All directed paths between two nodes |
| `mdb diff` | Structural graph diff against a git reference |
| `mdb query <expression>` | Boolean metadata/structure query (`AND`, `OR`, `NOT`) |
| `mdb context-compose <URI>` | Bounded materialization for LLM consumption |
| `mdb pack <dir>` | Pack template scaffolding into deterministic signed zip package |
| `mdb init` | Initialize project workspace/memory from signed zip package |

All commands accept `--json` for machine-readable output.  
All outputs are deterministic and JSON-serializable. All URIs are stable across sessions.

### Selected examples

```bash
# Validate an entire repository
mdb validate --root docs/ --json

# Validate one Markdown file in isolation
mdb validate --file docs/auth.md --json

# Single-file mode skips ordinary broken-ref errors for refs/includes that
# point to other files; use --root when validating the full project graph.

# Validate section metadata against local per-section schemas
mdb validate --root . --json

# 1-hop neighborhood of a node
mdb context docs/auth.md#auth --root docs/ --json

# Read and edit structured YAML metadata without touching the Markdown body
mdb metadata get docs/auth.md#auth owner.name --json
mdb metadata update docs/auth.md#auth status '"review"' --json
mdb metadata update docs/auth.md#auth owner '{"name":"Alice","team":"security"}' --json
mdb metadata unset docs/auth.md#auth draft_notes --json

# Find all sections tagged api that are not obsolete
mdb query "tag:api AND NOT status=obsolete" --root docs/ --json

# Find backlog-like section IDs with a regex predicate
mdb query "section~=/^backlog\\.item\\.B-\\d{3}$/ AND NOT status=done" --root docs/ --json

# Bounded context for LLM — depth 2, max 2000 tokens
mdb context-compose docs/auth.md#auth --root docs/ --depth 2 --token-limit 2000 --json

# What changed structurally since the last commit?
mdb diff --root docs/ --since HEAD~1 --json

# Pack a template directory
mdb pack templates/scrum -o scrum_template.zip

# Initialize a workspace memory using a local template zip
mdb init -t scrum_template.zip -r my_new_project/ --var project_name="My New App" --var owner="Bob"

# Initialize a workspace memory using a remote web-based template package (requires --checksum)
mdb init -t https://example.com/templates/scrum.zip -r my_new_project/ --checksum d8f2a...f7c22 --var project_name="My New App" --var owner="Bob"

# Validate using web-based schemas and bypassing local cache
mdb validate --root docs/ --no-cache
```

> [!NOTE]
> **Workspace Configuration & Rationale:**
> `mdb init` writes project configuration into `.mdb/config.yaml` at the root of the target directory. Keeping configuration at the repository root serves as a marker for `mdbind` tool operations, stores global variables, enables commands to locate the repository root automatically, and utilizes a dedicated `.mdb/` directory to prevent cluttering the root folder while accommodating future local caches (e.g. cached remote schemas and templates in `.mdb/cache/`).

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

> 262 tests, 0 failures.

---

## License

[Apache License, Version 2.0](https://opensource.org/license/Apache-2.0)

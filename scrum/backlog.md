# Backlog - Consolidator

Document status: active
Owner: gresendesa
Creation date: 2026-04-08
Last updated: 2026-06-14

## Purpose

This file is a synthetic consolidator of backlog items.

Full details for each item are in dedicated files under scrum/backlog/.

## Convention

- Backlog item: B-XXX
- Detailed file: scrum/backlog/B-XXX.md

## Summary

### Completed

| ID    | Title                                        | Sprint      |
|-------|----------------------------------------------|-------------|
| B-001 | Project setup and data models                | SPR-2026-01 |
| B-002 | Markdown parser and section discovery        | SPR-2026-01 |
| B-003 | Directive tokenization (@ref, @include)      | SPR-2026-01 |
| B-004 | Repository indexing and graph                | SPR-2026-01 |
| B-005 | CLI - mdgraph get command                    | SPR-2026-01 |
| B-006 | CLI - mdgraph tree command                   | SPR-2026-01 |
| B-007 | CLI - mdgraph compose command                | SPR-2026-01 |
| B-008 | Cycle detection and resolution               | SPR-2026-01 |
| B-009 | Persistent index cache                       | SPR-2026-01 |
| B-010 | README and examples directory                | SPR-2026-01 |
| B-011 | Directive syntax renderable as MD link       | SPR-2026-02 |
| B-012 | Configurable depth in tree command           | SPR-2026-03 |
| B-013 | YAML syntax for section metadata block       | SPR-2026-04 |
| B-014 | Translate docs + expand specification.md §1–§11 | SPR-2026-05 (partial) |
| B-015 | mdgraph validate                             | SPR-2026-05 |
| B-025 | --json flag for get and tree                 | SPR-2026-05 |
| B-016 | mdb context                                  | SPR-2026-06 |
| B-017 | mdb backlinks                                | SPR-2026-06 |
| B-018 | mdb search                                   | SPR-2026-06 |
| B-019 | mdb impact                                   | SPR-2026-06 |
| B-020 | mdb neighbors                                | SPR-2026-07 |
| B-021 | mdb explain                                  | SPR-2026-07 |
| B-022 | mdb diff                                     | SPR-2026-07 |
| B-023 | mdb query                                    | SPR-2026-07 |
| B-024 | mdb context-compose                          | SPR-2026-07 |
| B-026 | Rename project to MdBind, CLI command to mdb | SPR-2026-09 |
| B-027 | README.md ideal for GitHub homepage          | SPR-2026-10 |
| B-029 | JSON context fails with YAML date metadata   | SPR-2026-11 |
| B-031 | `mdb diff` fails on historical Markdown parsing with PosixPath file_path | SPR-2026-12 |
| B-030 | Structured query pseudo-fields and regex predicates | SPR-2026-12 |
| B-032 | `mdb metadata` commands for structured YAML metadata | SPR-2026-13 |
| B-033 | Local schema validation for structured section metadata | SPR-2026-14 |
| B-035 | File-scoped validation mode for `mdb validate` | SPR-2026-15 |
| B-036 | File-relative schema reference resolution | SPR-2026-16 |
| B-037 | Schema-backed project memory normalization | SPR-2026-17 |
| B-038 | `mdb validate --file` reports valid external refs as broken | SPR-2026-18 |
| B-039 | Template-driven workspace initialization (mdb init & mdb pack) | SPR-2026-19 |
| B-040 | Sequential ID Scanner & Workflow Validation (Features 2 & 3) | SPR-2026-20 |
| B-034 | Web URI schema references for section metadata | SPR-2026-21 |
| B-041 | Web-based template packages (fetching template ZIPs from web URIs with checksum verification) | SPR-2026-21 |
| B-042 | Global installation guidance using pipx in documentation | SPR-2026-22 |
| B-043 | Session hijacking and instruction hooks for LLM dev environments | SPR-2026-23 |
| B-044 | Manage agent session hooks via CLI command       | SPR-2026-24 |
| B-045 | Implement Kanban, Shape Up, ADR, and Minimal template packages | SPR-2026-25 |
| B-046 | Aperfeiçoar o CONSTITUTION.md de cada template com includes e refs | SPR-2026-26 |
| B-047 | Interactive template selection in mdb init when template is omitted | SPR-2026-26 |
| B-048 | Verification of minimum template conformity         | SPR-2026-27 |
| B-049 | Support language selection in mdb init              | SPR-2026-27 |
| B-050 | Fix local template packaging inside Python package  | SPR-2026-28 |

| ID    | Title                                               | PO Priority | Risk    | Status | Detailed File |
|-------|-----------------------------------------------------|-------------|---------|--------|---------------|

### Obsolete

| ID    | Title                                               | PO Priority                  | Risk      | Reason |
|-------|-----------------------------------------------------|------------------------------|-----------|--------|
| B-028 | Translate CLI help strings to English               | not applicable               | 1 (low)   | PO decision during SPR-2026-11 planning |

## Template for new items

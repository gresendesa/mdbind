# Sprints - Consolidator

Document status: active
Owner: gresendesa
Creation date: 2026-04-08
Last updated: 2026-06-13

## Purpose

This file is a synthetic consolidator of sprints.

Full details for each sprint are in dedicated files under scrum/sprint/.

## Convention

- Sprint: SPR-YYYY-NN
- Detailed file: scrum/sprint/SPR-YYYY-NN.md

## Registered sprints

### SPR-2026-01

- Status: done
- Focus: Full mdgraph implementation (models, pipeline, CLI, cycles, cache)
- PO Priority of items: 2 (high) for all
- Sprint risk: high (B-007 risk 3; resolved)
- Result: 9/9 items delivered, 107 tests passing
- Detailed file: scrum/sprint/SPR-2026-01.md

### SPR-2026-02

- Status: done
- Focus: Renderable directive syntax as Markdown link (B-011)
- PO Priority of items: 1 (critical)
- Sprint risk: medium
- Result: 1/1 item delivered, 130 tests passing
- Note: includes heading normalization hotfix in composer (root always becomes H1, children relativized correctly)

### SPR-2026-03

- Status: done
- Focus: Configurable depth in tree command (B-012)
- PO Priority of items: 1 (critical)
- Sprint risk: low
- Result: 1/1 item delivered, 126 tests passing
- Detailed file: scrum/sprint/SPR-2026-03.md

### SPR-2026-04

- Status: done
- Focus: YAML syntax for section metadata block (B-013)
- PO Priority of items: 1 (critical)
- Sprint risk: medium
- Result: 1/1 item delivered, 132 tests passing
- Detailed file: scrum/sprint/SPR-2026-04.md

### SPR-2026-05

- Status: done
- Focus: Documentation translation, spec expansion (§9–§11), B-015 (validate), B-025 (--json)
- PO Priority of items: B-014 = 2 (high), B-015 = 1 (critical), B-025 = 1 (critical)
- Sprint risk: low (weighted avg 1.33)
- Result: 5/5 tasks done, 152 tests passing
- Detailed file: scrum/sprint/SPR-2026-05.md

### SPR-2026-06

- Status: done
- Focus: IA v1 graph operations — context, backlinks, search, impact
- PO Priority of items: 2 (high) for all
- Sprint risk: medium (weighted avg 1.75)
- Result: 4/4 tasks done, 178 tests passing
- Detailed file: scrum/sprint/SPR-2026-06.md

### SPR-2026-07

- Status: done
- Focus: IA v2 graph operations — neighbors, explain, diff, query, context-compose
- PO Priority of items: 2 (high) for all
- Sprint risk: medium (weighted avg 2.2)
- Result: 5/5 tasks done, 209 tests passing
- Detailed file: scrum/sprint/SPR-2026-07.md

### SPR-2026-08

- Status: done
- Focus: B-014 completion — README rewrite + examples translation
- PO Priority of items: 2 (high)
- Sprint risk: low (all documentation)
- Result: 3/3 tasks done, 209 tests passing
- Detailed file: scrum/sprint/SPR-2026-08.md

### SPR-2026-09

- Status: done
- Focus: B-026 — rename project to MdBind, CLI command to mdb
- PO Priority: 2 (high)
- Sprint risk: medium
- Result: 5/5 tasks done, 209 tests passing
- Detailed file: scrum/sprint/SPR-2026-09.md

### SPR-2026-10

- Status: done
- Focus: B-027 — README.md ideal for GitHub project homepage
- PO Priority of items: 2 (high)
- Sprint risk: low (documentation only, weighted avg 1.0)
- Result: 5/5 tasks done, 209 tests passing
- Detailed file: scrum/sprint/SPR-2026-10.md

### SPR-2026-11

- Status: done
- Focus: B-029 — JSON context fails with YAML date metadata
- PO Priority of items: 2 (high)
- Sprint risk: medium (weighted avg 1.6)
- Result: 5/5 tasks done, 211 tests passing
- Detailed file: scrum/sprint/SPR-2026-11.md

### SPR-2026-12

- Status: done
- Focus: B-031 `mdb diff` PosixPath bugfix and B-030 structured query enhancements
- PO Priority of items: B-031 = 1 (critical), B-030 = 3 (medium)
- Sprint risk: medium (weighted avg 1.89)
- Result: 9/9 tasks done, 216 tests passing
- Detailed file: scrum/sprint/SPR-2026-12.md

### SPR-2026-13

- Status: done
- Focus: B-032 - `mdb metadata` commands for structured YAML metadata
- PO Priority of items: B-032 = 2 (high)
- Sprint risk: medium (weighted avg 2.0)
- Result: 11/11 tasks done, 228 tests passing
- Detailed file: scrum/sprint/SPR-2026-13.md

### SPR-2026-14

- Status: done
- Focus: B-033 - local per-section schema validation in `mdb validate`
- PO Priority of items: B-033 = 2 (high)
- Sprint risk: high (weighted avg 2.33)
- Result: 10/10 tasks done, 235 tests passing; PO accepted after manual test
- Detailed file: scrum/sprint/SPR-2026-14.md

### SPR-2026-15

- Status: done
- Focus: B-035 - file-scoped validation mode for `mdb validate`
- PO Priority of items: B-035 = 2 (high)
- Sprint risk: medium (weighted avg 1.89)
- Result: 9/9 tasks done, 241 tests passing; PO accepted
- Detailed file: scrum/sprint/SPR-2026-15.md

### SPR-2026-16

- Status: done
- Focus: B-036 - file-relative schema reference resolution
- PO Priority of items: B-036 = 1 (critical)
- Sprint risk: medium (weighted avg 1.67)
- Result: 6/6 tasks done, 242 tests passing; PO accepted; version bumped to
  0.1.11
- Detailed file: scrum/sprint/SPR-2026-16.md

### SPR-2026-17

- Status: done
- Focus: B-037 - schema-backed project memory normalization
- PO Priority of items: B-037 = 2 (high)
- Sprint risk: medium (weighted avg 2.25)
- Result: 8/8 tasks done, 242 tests passing; PO accepted
- Detailed file: scrum/sprint/SPR-2026-17.md

### SPR-2026-18

- Status: done
- Focus: B-038 - file-mode external ref validation false positives
- PO Priority of items: B-038 = 2 (high)
- Sprint risk: medium (weighted avg 2.22)
- Result: 9/9 tasks done, 244 tests passing; PO accepted; version bumped to
  0.1.12
- Detailed file: scrum/sprint/SPR-2026-18.md

### SPR-2026-19

- Status: done
- Focus: B-039 - template-driven workspace initialization
- PO Priority of items: B-039 = 2 (high)
- Sprint risk: low (weighted avg 1.38)
- Result: 8/8 tasks done, 253 tests passing; PO accepted
- Detailed file: scrum/sprint/SPR-2026-19.md

### SPR-2026-20

- Status: done
- Focus: B-040 - sequential ID scanner & workflow validation
- PO Priority of items: B-040 = 2 (high)
- Sprint risk: low (weighted avg 1.38)
- Result: 8/8 tasks done, 257 tests passing; PO accepted
- Detailed file: scrum/sprint/SPR-2026-20.md

### SPR-2026-21

- Status: done
- Focus: B-034 & B-041 - web-based schemas & templates
- PO Priority of items: B-034 = 2 (high), B-041 = 2 (high)
- Sprint risk: medium
- Result: 8/8 tasks done, 262 tests passing; PO accepted; version bumped to 0.1.13
- Detailed file: scrum/sprint/SPR-2026-21.md

### SPR-2026-22

- Status: done
- Focus: B-042 - Global installation guidance using pipx in documentation
- PO Priority of items: B-042 = 2 (high)
- Sprint risk: low
- Result: 2/2 tasks done, 262 tests passing; PO accepted
- Detailed file: scrum/sprint/SPR-2026-22.md

### SPR-2026-23

- Status: done
- Focus: B-043 - Session hijacking and instruction hooks for LLM dev environments
- PO Priority of items: B-043 = 1 (critical)
- Sprint risk: medium
- Result: 5/5 tasks done, 266 tests passing; PO accepted
- Detailed file: scrum/sprint/SPR-2026-23.md

### SPR-2026-24

- Status: done
- Focus: B-044 - Manage agent session hooks via CLI command
- PO Priority of items: B-044 = 1 (critical)
- Sprint risk: low
- Result: 5/5 tasks done, 267 tests passing; PO accepted
- Detailed file: scrum/sprint/SPR-2026-24.md




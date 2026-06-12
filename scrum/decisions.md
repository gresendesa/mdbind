# Decisions - Memory and Governance

Document status: active
Owner: gresendesa
Creation date: 2026-04-08
Last updated: 2026-06-12

## Purpose

Record the history of decisions about memory architecture and process governance of this workspace.

## Record format

- ID: DEC-XXX
- Date:
- Status: proposed | approved | replaced | obsolete
- Context:
- Decision:
- Impact:
- Files affected:
- Future review:

## History

---

- ID: DEC-001
- Date: 2026-06-12
- Status: approved
- Context: The PO wanted schema validation for section YAML metadata to add a
  deterministic contract layer without reducing Markdown repository autonomy.
- Decision: Schema validation is opt-in per section through a `schema`
  metadata attribute. There is no global repository schema. B-033 supports only
  local schema references resolved from the repository root, with
  `scrum/schema/` as the convention. JSON Schema is normative; YAML schema
  files are accepted only as YAML serialization of JSON Schema. Web URI schemas
  are deferred to B-034.
- Impact: `mdb validate` becomes the integration point for schema validation.
  Existing sections without `schema` keep free-form metadata behavior. Schema
  validation errors extend the JSON error object additively.
- Files affected: `src/mdbind/schema_validation.py`, `src/mdbind/cli.py`,
  `README.md`, `specification.md`, `llms.txt`, `scrum/backlog/B-033.md`,
  `scrum/backlog/B-034.md`, `scrum/sprint/SPR-2026-14.md`.
- Future review: Revisit network fetching, cache behavior, and trust policy
  when B-034 is planned.

---

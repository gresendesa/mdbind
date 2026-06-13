# Decisions - Memory and Governance

Document status: active
Owner: gresendesa
Creation date: 2026-04-08
Last updated: 2026-06-13

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
- Status: replaced
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

- ID: DEC-002
- Date: 2026-06-13
- Status: approved
- Context: The PO identified an ambiguity between repository-root schema
  resolution and file-scoped schema resolution after B-033 and B-035. A single
  invariant is needed so the same `schema` value has the same meaning wherever
  validation is invoked.
- Decision: Local section metadata schema references are always resolved
  relative to the Markdown file that contains the section declaring `schema`.
  `mdb validate` must not accept a global schema directory as an implicit base
  for ordinary relative schema references. Centralized schema folders remain
  possible through explicit relative paths from each section file.
- Impact: `mdb validate --root` and `mdb validate --file` use the same schema
  resolution rule. The schema reference itself remains the source of truth.
  Existing repositories that relied on repository-root-relative schema paths
  from nested Markdown files must update those references to file-relative
  paths.
- Files affected: `src/mdbind/schema_validation.py`, `src/mdbind/cli.py`,
  `README.md`, `specification.md`, `llms.txt`, `scrum/architecture.md`,
  `scrum/backlog/B-036.md`.
- Future review: If a schema alias or centralized schema registry is needed,
  introduce it as an explicit, versioned contract instead of overloading normal
  relative paths.

---

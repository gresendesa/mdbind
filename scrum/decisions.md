# Decisions - Memory and Governance

```yaml
section: project-decisions
schema: schema/decision-log.schema.json
record_type: decision-log
status: active
owner: gresendesa
created: "2026-04-08"
last_updated: "2026-06-13"
```

[@ref: architecture log](architecture.md#project-architecture)

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

- ID: DEC-003
- Date: 2026-06-13
- Status: approved
- Context: The PO wanted the project's own memory to become coherent with the
  section notation, schema validation contract, and graph-linking style created
  so far.
- Decision: Project memory normalization should use minimal local JSON Schemas,
  file-relative `schema` references, and intentional `@ref` or `@include`
  links. `@include` is reserved for composition-worthy source content, while
  `@ref` records navigational or dependency relationships without duplication.
- Impact: Current and recent Scrum memory records become first-class MDBind
  graph nodes. Future agents can validate and traverse project governance
  records through the same CLI used for product content.
- Files affected: `scrum/schema/*.schema.json`, `scrum/backlog/B-033.md`,
  `scrum/backlog/B-036.md`, `scrum/backlog/B-037.md`,
  `scrum/sprint/SPR-2026-16.md`, `scrum/sprint/SPR-2026-17.md`,
  `scrum/decisions.md`, `scrum/architecture.md`, `scrum/experience.md`.
- Future review: Expand schemas and section-backed records gradually instead
  of forcing every legacy memory entry into strict structure at once.

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

- ID: DEC-004
- Date: 2026-06-13
- Status: approved
- Context: The PO wanted to transition from a flat `.mdbconfig` file to a more robust, extensible directory-based `.mdb/config.yaml` layout, and wanted to implement a sequential ID scanner and workflow validation system.
- Decision: Migrate configuration to `.mdb/config.yaml` at the root of the workspace. This dedicated directory allows keeping the root directory clean while accommodating future features (e.g. caches). Add a `next-id` command to scan sections and return the next sequential ID, and add status transition gates to `validate` comparing current states against a historical Git reference if `--since` is provided.
- Impact: Workspace configuration is cleaner and supports future extensibility. CLI commands support auto-generating sequential IDs and enforcing workflow compliance over commit histories.
- Files affected: `src/mdbind/template_packages.py`, `src/mdbind/cli.py`, `src/mdbind/schema_validation.py`, `README.md`, `specification.md`, `CONSTITUTION.md`, `templates/scrum/scrum/CONSTITUTION.md.j2`, `tests/test_cli_next_id_workflows.py`, `tests/test_cli_init_pack.py`.
- Future review: Refine workflows and transitions as more methodologies are mapped.

- ID: DEC-005
- Date: 2026-06-13
- Status: approved
- Context: Implement remote schema retrieval (B-034) and web-based template downloading (B-041). The PO prioritized security and reproducibility, requesting checksum verification for remote template downloads.
- Decision:
  1. Allow `mdb validate` to fetch JSON/YAML schemas from remote web URIs using HTTP.
  2. Implement an `.mdb/cache/` directory to store remote schemas (`.mdb/cache/schemas/`) and template zip files (`.mdb/cache/templates/`).
  3. Support `--no-cache` flags to bypass cached items and force fresh downloads.
  4. Make `--checksum` mandatory for remote templates in `mdb init` to enforce SHA-256 validation before unpacking/verifying signatures, and support optional checksum verification for local templates.
- Impact: Users can leverage remote schemas and templates securely without compromising reproducibility, performance, or offline availability.
- Files affected: `src/mdbind/schema_validation.py`, `src/mdbind/template_packages.py`, `src/mdbind/cli.py`, `README.md`, `specification.md`, `llms.txt`, `tests/test_cli_web_schemas_templates.py`.
- Future review: Add automated schema verification and certificate pinning support if required by enterprise environments.

- ID: DEC-006
- Date: 2026-06-14
- Status: approved
- Context: Protect developer workspaces from AI session hijacking and ensure LLMs parse the local project memory instead of relying on pre-trained parametric memory.
- Decision: Add interactive session hook injection during `mdb init` (top/bottom/none placements) targeting files like `AGENTS.md` and `.github/copilot-instructions.md`. Generate a dynamic 5-word secret verification phrase to act as a canary. Implement the `mdb check-session-hook` CLI command to verify that entrypoint files are hooked with standard MdBind directives and report the secret phrase.
- Impact: Standardized mechanism to enforce project-specific rules on incoming agent/LLM sessions.
- Files affected: `src/mdbind/template_packages.py`, `src/mdbind/cli.py`, `tests/test_cli_session_hooks.py`, `README.md`, `specification.md`, `llms.txt`.
- Future review: Review hooks integration when IDE-native memory injection APIs become standard.

---

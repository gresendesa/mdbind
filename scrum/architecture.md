# Architecture - Components, Contracts, and Flows

Document status: active
Owner: gresendesa
Creation date: 2026-06-09
Last updated: 2026-06-13

## Purpose

Record relevant changes to components, contracts, and flows.

## Records

### 2026-06-09 - CLI JSON serialization normalization

- Status: active
- Owner: gresendesa
- Context: `mdb context --json` failed when YAML metadata contained values parsed
  by PyYAML as `date` objects.
- Change: `src/mdbind/cli.py` now routes CLI JSON output through `_json_dumps`,
  which keeps `ensure_ascii=False` as the default and serializes non-JSON-native
  values with `default=str`.
- Contract impact: No output shape change. YAML date metadata is emitted as a
  JSON string, for example `"created_at": "2026-06-08"`.
- Flow impact: CLI JSON rendering is more tolerant of YAML metadata values while
  preserving existing command schemas.

### 2026-06-11 - Query structural pseudo-fields and regex predicates

- Status: active
- Owner: gresendesa
- Context: `mdb query` needed to filter sections by structural attributes such
  as section ID, file path, and heading without relying on helper metadata tags.
- Change: `src/mdbind/cli.py` now evaluates query predicates against the full
  `ParsedSection` so `section`, `id`, `path`, `file`, and `heading` can be used
  as pseudo-fields.
- Contract impact: Additive query-language change. JSON output shape remains
  `{"expression": "...", "results": [{"uri": "...", "metadata": {}}]}`.
- Flow impact: Query matching can combine metadata predicates, structural
  pseudo-fields, boolean operators, and regex predicates with `key~=/regex/`.

### 2026-06-11 - Diff historical parser path normalization

- Status: active
- Owner: gresendesa
- Context: `mdb diff --json` failed when historical Markdown content from Git
  was parsed with a `Path` object as `file_path`.
- Change: The historical graph builder now passes `str(abs_path)` to
  `parse_text`.
- Contract impact: No output shape change. The fix preserves the existing
  structural diff JSON schema.
- Flow impact: Historical Markdown parsing in `mdb diff` now matches the normal
  parser contract used by `parse_file`.

### 2026-06-12 - Structured metadata command family

- Status: active
- Owner: gresendesa
- Context: Agents and users need to read and edit structured YAML section
  metadata without touching Markdown body content or directives.
- Change: Added `src/mdbind/metadata.py` with helpers to locate the direct YAML
  fence containing a matching `section`, read dotted metadata paths, update
  JSON values, unset metadata keys, and rewrite only the YAML fence content.
  Added the `mdb metadata` Typer subcommand family in `src/mdbind/cli.py`.
- Contract impact: Additive CLI contract. New commands are
  `mdb metadata get <URI> [path]`, `mdb metadata update <URI> <path>
  <json-value>`, and `mdb metadata unset <URI> <path>`. JSON output for `get`
  is `{"uri": "...", "path": "...", "value": ...}`. JSON output for write
  commands is `{"uri": "...", "path": "...", "metadata": {...}}`.
- Flow impact: Metadata write operations parse the selected Markdown file,
  locate the structured YAML block by section id, mutate only that block, and
  persist the result as YAML. The `section` key is read-only through write
  commands.

### 2026-06-12 - Local per-section metadata schema validation

- Status: replaced by 2026-06-13 schema reference resolution invariant
- Owner: gresendesa
- Context: Section metadata is intentionally flexible, but some sections need a
  deterministic contract layer to reduce ambiguity for agents and CI workflows.
- Change: Added `src/mdbind/schema_validation.py` and integrated it into
  `mdb validate`. Sections opt in by declaring `schema` in their structured
  YAML metadata. The schema reference is resolved relative to the repository
  root, with `scrum/schema/` as the documented convention. JSON Schema is the
  normative schema language, and YAML schema files are accepted when they encode
  a JSON Schema object.
- Contract impact: Additive validation contract. Existing sections without
  `schema` keep current validation behavior. `mdb validate --json` preserves
  `type`, `uri`, and `detail` while adding schema-specific fields `schema`,
  `schema_path`, and `path` for schema errors. Web URI schemas return
  `schema_unsupported_uri` in this sprint.
- Flow impact: `mdb validate` builds the graph, performs existing structural
  checks, then validates only sections that declare `schema`.

### 2026-06-13 - Schema reference resolution invariant

- Status: active
- Owner: gresendesa
- Context: Schema validation had two documented bases: repository root in
  `--root` mode and selected file parent in `--file` mode. The PO selected a
  single invariant to avoid command-dependent meaning for the same section
  metadata.
- Change: `src/mdbind/schema_validation.py` now resolves each local `schema`
  reference from `Path(section.file_path).parent`, regardless of whether
  validation was started with `--root` or `--file`.
- Contract impact: `schema` is always relative to the Markdown file containing
  the section that declares it. `mdb validate` does not take a global schema
  directory for ordinary relative paths. Centralized schema folders must be
  referenced explicitly with normal relative paths.
- Flow impact: Repository validation can validate sections in different
  directories against different local schema folders without changing the CLI
  invocation.

### 2026-06-12 - File-scoped validation mode

- Status: active
- Owner: gresendesa
- Context: Manual editing workflows need to validate one Markdown file without
  recursively validating unrelated repository files or test fixtures.
- Change: `mdb validate` now accepts `--file <path.md>` as an isolated
  validation mode. `--root` remains the recursive integrated repository mode,
  and using both options together is rejected.
- Contract impact: Additive CLI contract. JSON output keeps the same
  `errors`, `warnings`, and `summary` shape. Schema references follow the
  active file-relative schema resolution invariant.
- Flow impact: File mode parses the selected file, builds an in-memory graph
  only from its sections, and runs the same structural and schema checks used
  by root mode. Cross-file refs/includes may be reported as broken because no
  external graph context is loaded.

# Technical Specification: MdBind — Markdown Graph Composition Engine

## 1. Definitions and Architectural Overview

`MdBind` is a CLI parsing and document composition engine. It treats Markdown file repositories as a graph database, where sections act as independent records that can reference each other and be dynamically composed.

The architecture is built on a strict separation between **Document Physics** (where elements are written) and **Document Semantics** (what they mean and how they connect).

* **Primary Node (Section):** The document is composed primarily of sections. A section is delimited exclusively by the heading hierarchy, regardless of its content.
* **Section URI:** The global node identifier in the format `path/to/file.md#section-id`. The path is always resolved relative to the calling file.
* **Dual Representation:** The engine maintains two simultaneous representations of sections:
  * **Documentary Representation:** Based on exact offsets (line/character) from the original file. Used for extractions with 100% fidelity (preserving spaces, formatting, and comments).
  * **Semantic Representation:** Based on the Abstract Syntax Tree (AST) and Tokens. Used for structural analysis, graph validation, and artifact composition.

The engine is designed to serve both human authors and AI agents. For agents, `MdBind` acts as a **deterministic semantic memory layer**: stable URIs provide addressable knowledge nodes; the graph structure encodes relationships; and CLI commands provide bounded, reproducible retrieval operations that fit inside context windows.

---

## 2. Processing Pipeline and Discovery

To avoid fragile dependencies and enable rich validations, the parsing lifecycle follows a strict unidirectional five-stage flow:

**`Markdown ➔ AST ➔ RawSection ➔ ParsedSection ➔ Index ➔ Graph`**

1. **AST Generation:** The engine reads the Markdown text and generates the flat token list.
2. **Section Discovery (`RawSection`):** The engine scans the AST for `heading_open` tokens. Upon finding one, it marks `token_start`. It continues scanning until end-of-document or until intercepting the first subsequent `heading_open` of equal or lower level, marking `token_end`. Source file offsets (lines) are also captured here.
3. **Metadata Binding (`ParsedSection`):** With section boundaries isolated, the engine analyzes internal tokens seeking the code block marked as `yaml` with a `section:` key. The content is validated and extracted.
4. **Directive Tokenization:** Within the newly delimited section, semantic markers (such as `@include`) are converted from raw text into typed engine objects.
5. **Graph and Composition:** Validated nodes go to the Index, then edges form the Graph for materialization.

---

## 3. Payload Syntax and Validation

The metadata block does not define the section; it only confers identity to a section already discovered hierarchically.

* **Strict Position:** The `section` block must be the **first textual block** immediately after the heading that originated the section. If there is normal text before the block, the engine raises a validation error (*"payload is not the first block"*).
* **Internal Uniqueness:** The engine raises an error if it detects more than one `section` block within the boundaries of the same `RawSection`.
* **Mandatory Schema:** The `id` field is strictly required. The engine emits an error (*"section without required payload"*) if the block does not have this field, since it guarantees the uniqueness of the `(file, id)` pair in the repository.
* **Free Fields:** Fields such as `title` and `description` are reserved. Any other keys (e.g., `owner`, `tags`) are preserved in the section's dynamic dictionary.
* **Optional Section Schema:** A section may declare `schema` to opt into
  metadata validation. The value is a local schema reference resolved relative
  to the Markdown file that contains the section. Schemas are per-section only;
  there is no global repository schema.

The YAML block format for a section payload is:

````markdown
## My Section

```yaml
section: my-section-id
title: Human-readable title
owner: team-name
tags: [architecture, core]
```
````

When `schema` is present, the referenced file must contain a JSON Schema
document. The schema file may be JSON or YAML, as long as YAML encodes the same
JSON Schema object:

````markdown
## My Section

```yaml
section: my-section-id
schema: schema/work-item.schema.json
status: doing
owner:
  team: core
```
````

---

## 4. Directive Semantics and Composition

The engine transcends textual search (Regex). Markers are not merely "substituted"; they exist in the section's semantic tree (`ParsedSection`) as first-class nodes (e.g., `IncludeDirective`).

Directives are written as standard Markdown links, which means they render correctly in any Markdown viewer:

```markdown
[@include: label](path/to/file.md#section-id)
[@ref: label](path/to/file.md#section-id)
[@query: label](key=value)
```

### 4.1. Edge Types (DSL)

* **Dependency (`@ref`):** Creates a directional edge pointing to a contextual dependency, but does **not** embed the content in the final composition.
* **Inclusion / Transclusion (`@include`):** Creates a directional edge and instructs the engine to substitute the directive token with the complete AST tree of the target node during composition.
* **Dynamic Query (`@query` — *Reserved for Future Use*):** A polymorphic edge designed to resolve multiple nodes at runtime based on YAML payload (Documentary GraphQL).

### 4.2. Composition Rules

* **Spatial Order:** Node expansion via `@include` strictly follows the order of directive tokens in the parent document's AST.
* **Node Deduplication:** If A includes D and B also includes D: the default behavior (`deduplicate: false`) materializes D twice, reflecting exact textual intent. Under the `--deduplicate` flag, the engine materializes the first occurrence and replaces the second with a `@ref` (simple link).
* **Failure Handling (`--strict`):** If a referenced URI does not exist in the index:
  * **Default:** The engine emits a warning to stderr, injects an HTML placeholder in the document (`<!-- mdb: broken ref -->`) and continues.
  * **Strict:** The engine raises a fatal error and aborts the process, guaranteeing integrity for CI/CD pipelines.
* **Heading Normalization:** The root section is always normalized to H1. Child sections are offset relative to the root level, preserving the original heading hierarchy structure.
* **Depth Control (`--depth`):** When `depth <= 0`, include directives are discarded (not expanded), enabling shallow materialization for context-budget-aware consumers such as LLM agents.

---

## 5. Mathematical Modeling (Graph Theory)

The documentary ecosystem is modeled as a **General Directed Graph (Digraph)**, defined as $G = (V, E)$. The documented repository may natively contain logical cycles.

* Vertices $v \in V$ carry structural and semantic properties (URI, metadata dict, directives).
* Edges $E$ are classified by directives ($E_{ref}$, $E_{include}$) and bidirectionally indexed for $O(1)$ lookups.
* **Acyclic Resolution:** During the materialization operation (`compose`), the traversal algorithm tracks the current execution path ($P$). If an inclusion edge $(x, y)$ is evaluated where $y \in P$, the **cycle is detected and the edge is silently broken in the output**, preventing rendering loops, without altering the original graph topology.

Formal definitions:

$$G = (V, E), \quad E \subseteq V \times V \times \{ref, include, query\}$$

$$\text{neighbors}(v) = \{u \mid (v, u, \cdot) \in E\} \cup \{u \mid (u, v, \cdot) \in E\}$$

$$\text{backlinks}(v) = \{u \mid (u, v, \cdot) \in E\}$$

$$\text{reachable}(v) = \text{BFS}(G, v) \text{ following outgoing edges}$$

$$\text{impact}(v) = \text{BFS}(G^R, v) \text{ following incoming edges (reverse graph)}$$

---

## 6. Code Modeling (Pydantic & Architecture)

The model consolidates the Pipeline view, isolating raw delimitation from business meaning.

```python
from pydantic import BaseModel, Field
from typing import List, Any, Dict, Set, Literal
from collections import defaultdict

# --- Phase 2: Physical Delimitation ---
class RawSection(BaseModel):
    """Resolves only the spatial scope of the section in the AST and source file."""
    heading_level: int
    heading_text: str
    token_start: int
    token_end: int
    source_start_line: int
    source_end_line: int

# --- Phase 4: Semantics and Directives ---
class Directive(BaseModel):
    """Directives cease to be text and become logical nodes."""
    type: Literal["ref", "include", "query"]
    target_uri: str
    label: str | None = None

class ParsedSection(BaseModel):
    """Resolves meaning. Binds physical space to metadata and references."""
    raw: RawSection
    uri: str
    file_path: str
    metadata: Dict[str, Any]
    directives: List[Directive] = Field(default_factory=list)

# --- Phase 5: Indexing and Graph ---
class SectionIndex(BaseModel):
    """O(1) access repository of already-parsed sections."""
    sections: Dict[str, ParsedSection] = Field(default_factory=dict)

class SectionGraph(BaseModel):
    """Topological dependency management (Backlinks supported)."""
    index: SectionIndex
    outgoing_edges: Dict[str, Set[str]] = Field(default_factory=lambda: defaultdict(set))
    incoming_edges: Dict[str, Set[str]] = Field(default_factory=lambda: defaultdict(set))
```

---

## 7. Indexing and Cache Strategy

Reading massive repositories requires that the parsing and validation step does not occur repetitively during queries.

* **Initial State:** The `index_repository()` command builds the `SectionIndex` entirely in memory from `.md` files.
* **Persistence:** After core stabilization, the typed `SectionIndex` is serialized to the cache at `.mdb/index.json`.
* **Optimization:** Subsequent executions load the `.json` and re-evaluate the AST only for files whose OS hashes differ from the cache (SHA-256 incremental cache).

---

## 8. CLI Interface (Use Cases)

The engine responds to commands aligned with its dual representation (Documentary vs Semantic).

### 8.1. `mdb get <URI>` (Documentary Fidelity)

Extracts an isolated section based strictly on the spatial representation (`source_start_line` and `source_end_line`).

* **Mechanics:** The engine opens the source file, slices the lines specified in the `RawSection` object, and writes to stdout.
* **Guarantee:** Millimetric preservation of original formatting, comments, and spaces. Nothing passes through the AST reconstructor.
* **Flags:** `--json` outputs `{"uri": "...", "content": "..."}`.

### 8.2. `mdb tree <URI>` (Structural View)

Queries the in-memory Graph and resolves the visual hierarchy based on semantics.

* **Output:** Illustrative dependency tree in the terminal. Supports `--refs` to display connections pointing to the requested URI (Dependency Inversion). Supports `--depth N` to limit traversal depth.
* **Flags:** `--json` outputs a structured tree object.

### 8.3. `mdb compose <URI>` (Semantic Materialization)

The engine enters transpiler mode. Based on the `ParsedSection` AST, it navigates token by token.

* Upon encountering regular text: passes the token through.
* Upon encountering an `IncludeDirective` node: interrupts the flow, fetches the target AST, injects it resolving heading levels mathematically, and resumes scanning.
* **Flags:** `--deduplicate`, `--strict`, `--depth N`, `--json`.

### 8.4. `mdb validate [--root <path> | --file <path.md>]` (Integrity Validation)

Scans the full repository graph, or one Markdown file in isolation, and reports
all structural integrity issues without modifying any file.

* **Checks performed:**
  * Broken `@ref` and `@include` targets (URIs not found in the index)
  * Duplicate section IDs within the same repository
  * Include cycles (detected via DFS execution path tracking)
  * Sections without required `section:` payload
  * Per-section schema validation for sections that declare `schema` (supporting local JSON/YAML schemas, and remote JSON/YAML web URIs resolved via HTTP).
* **Scope:** `--root <path>` performs recursive integrated repository
  validation. `--file <path.md>` validates only the selected file. `--root` and
  `--file` are mutually exclusive.
* **File isolation:** in `--file` mode, references or includes to sections in
  other files are treated as external to the isolated index and are not reported
  as ordinary `broken_ref` or `broken_include` errors. References/includes
  targeting missing sections in the selected file still fail. Use `--root` for
  integrated repository-wide ref/include validation.
* **Schema validation:** `schema` is always resolved relative to the Markdown
  file that contains the section, in both `--root` and `--file` modes. Local
  JSON and YAML files are accepted when they contain a JSON Schema document. Web
  URI schemas are resolved via HTTP, validated for correct schema mapping structure,
  and cached in `.mdb/cache/schemas/` to avoid redundant downloads.
* **Exit codes:** 0 = clean, 1 = errors found
* **Flags:** `--json` outputs `{"errors": [...], "warnings": [...], "summary": {...}}`, `--no-cache` forces remote schema fetch.

### 8.5. `mdb pack <directory> --output <filename.zip>` (Deterministic Scaffolding Packaging)

Combines a source directory of markdown templates and schema files into a deterministic, signed `.zip` package.

* **Mechanics:** The engine scans the source directory, reads `manifest.yaml` (which must be present), validates template file paths, constructs a sorted file manifest, and computes SHA-256 hashes for all files (excluding `SIGNATURE.yaml`).
* **Deterministic Zip:** ZIP archive entries are written in lexicographically sorted path order, and their timestamps are set to a fixed epoch date (1980-01-01) to ensure the ZIP file hash is identical for identical source directories.
* **Signature:** Writes a `SIGNATURE.yaml` metadata file containing file checksums and a payload digest to guarantee template integrity.

### 8.6. `mdb init --template <package.zip|URL>` (Workspace Initialization)

Initializes a new directory using a signed template `.zip` package from a local path or a remote URL.

* **Mechanics:** Unpacks the template package to a temporary directory, verifies the ZIP member paths against traversal attacks, and verifies file checksums against `SIGNATURE.yaml`.
* **Remote Templates & Checksum Verification:** Supports downloading remote template `.zip` files via HTTP/HTTPS. Remote downloads require the `--checksum <hash>` option to verify the integrity (SHA-256) of the package. Checked-out packages are cached in `.mdb/cache/templates/` under their URL hash to avoid duplicate downloads.
* **Rendering:** Renders the template files into the target project using Jinja2 engine, resolving variables specified in `manifest.yaml`.
* **Standard Methodology Templates:** The repository includes five pre-bundled template directories under `templates/` that support different developer workflows and management methodologies:
  * **Default/Scrum** (`templates/default`): Complete Agile Scrum framework memory (backlog, sprint tracking, constitution, decisions).
  * **Kanban** (`templates/kanban`): Continuous delivery flow-based board, architectural decisions, and lessons learned.
  * **Shape Up / Product** (`templates/product`): Product pitches, development cycles, and architectural scoping logs.
  * **ADR / RFC-Centric** (`templates/engineering`): Structured design decision records (ADRs) and release roadmap management.
  * **Minimal** (`templates/minimal`): Minimalist lightweight task checklist and chronological project changelog.
* **Configuration:** Writes a `.mdb/config.yaml` file in the root of the project containing project metadata, memory root folder, and template package properties.
* **Architectural Rationale:** The configuration resides at the repository root under `.mdb/config.yaml` rather than inside the memory folder itself. This serves as a project-wide marker declaring that the workspace is managed by `mdbind`, maps project-wide variables, allows future CLI commands to resolve `--root` automatically from the config, and keeps the repository root uncluttered by using a dedicated `.mdb/` directory for configuration and future indexing cache (including remote schemas and templates).
* **Interactive and Non-Interactive:** Supports interactive CLI prompt resolution, or non-interactive mode via `--context <file>` or `--var key=value` arguments.
* **Flags:** `--checksum <hash>` (mandatory for remote templates, optional for local ones), `--no-cache` to force refetching remote templates.

### 8.7. `mdb check-session-hook` (Agent Session Awareness Check)

Validates the setup and active state of agent session rules hooks and retrieves the secret verification phrase.

* **Mechanics:** Reads `.mdb/config.yaml` to retrieve the configured agent instruction files and the generated 5-word secret verification phrase.
* **Canary Phrase Verification:** As part of the Context Anchoring mechanism, each workspace is initialized with a randomized 5-word passphrase (canary). Typing this phrase to the LLM triggers a forced project memory awareness confirmation, guaranteeing that the agent session is correctly anchored to the local workspace memory instead of relying purely on generic pre-trained (parametric) memory.
* **Validation:** Programmatically checks that each hooked instruction file (e.g. `AGENTS.md`, `.github/copilot-instructions.md`) exists and contains the valid `@include: .../CONSTITUTION.md` directive.

### 8.8. `mdb session-hook` (Agent Session Hook Management)

Provides a CLI command group to dynamically manage agent session rules hooks in the workspace.

* **`mdb session-hook inject`**: Injects or updates the session rules hook in the development environment entrypoints.
  - Supports `--root` / `-r` (default `Path(".")`).
  - Supports `--file` / `-f` to target a custom entrypoint path (e.g., `.cursorrules`).
  - Supports `--placement` / `-p` (`top` or `bottom`) to set the insertion boundary.
  - Supports `--secret` / `-s` to override the generated 5-word secret phrase.
* **`mdb session-hook remove`**: Strips the session rules hook from development environment entrypoints.
  - Supports `--root` / `-r` (default `Path(".")`).
  - Supports `--file` / `-f` to target a custom entrypoint path for removal.
  - If a file is left empty after hook removal, it is automatically deleted from the workspace to prevent clutter.
  - Updates the active list of hooks recorded in `.mdb/config.yaml`.

---

## 9. Semantic Memory Model

`MdBind` is designed to function as a **deterministic graph-based semantic memory layer** for AI agents, not merely as a document composition tool for human authors.

### 9.1. Design Principles for Agent Consumption

* **Stable URIs as Knowledge Addresses:** Every section has a globally stable URI (`file.md#id`). An agent can store, retrieve, and reference knowledge nodes by URI across sessions without re-discovery overhead.
* **YAML Payload as Semantic Index:** The `section:` block doubles as a structured semantic index. Fields such as `title`, `tags`, `owner`, and custom keys enable graph-based search and filtering without full-text parsing.
* **Document vs. Context Materialization:** `mdb compose` produces a *document* (full fidelity, for human reading). `mdb context` and `mdb context-compose` produce *context payloads* (bounded, token-budget-aware, for LLM consumption).
* **Reproducibility:** All CLI commands are deterministic given the same graph state. Agents can cache URIs, tree structures, and composed outputs with confidence.
* **Bounded Retrieval:** The `--depth` flag enables agents to control retrieval scope, preventing context window overflow on large graphs.

### 9.2. Agent Interaction Patterns

| Pattern | Command | Use case |
|---------|---------|----------|
| Direct lookup | `get <URI>` | Retrieve raw section content by known URI |
| Neighbor discovery | `tree <URI>` | Explore what a node connects to |
| Context assembly | `context <URI>` | Get structured metadata + immediate neighbors |
| Metadata editing | `metadata get/update/unset <URI>` | Read or edit structured YAML metadata |
| Full materialization | `compose <URI>` | Expand a document tree into a single artifact |
| Impact analysis | `impact <URI>` | Find all nodes affected by a change |
| Semantic search | `search <predicate>` | Find nodes by metadata attributes |
| Integrity check | `validate` | Verify graph health before agent operations |

---

## 10. Extended Graph Operations

This section specifies the mathematical semantics and complexity of each extended CLI command.

### 10.1. `mdb validate`

$$f: G \to \text{ValidationReport}$$

Full graph scan. Collects all structural violations without mutation.

* **Algorithm:** Build a graph from either the recursive root or the selected
  file, run DFS traversal of $G$, set membership checks for duplicate IDs,
  execution-path tracking for cycle detection, local schema loading, and
  per-section metadata validation for nodes that declare `schema`.
* **Complexity:** $O(V + E)$
* **Output schema:**
```json
{
  "errors": [{"type": "broken_ref|broken_include|duplicate_id|missing_payload|cycle|schema_validation_error|schema_not_found|schema_invalid|schema_unsupported_uri", "uri": "...", "detail": "...", "schema": "...", "schema_path": "...", "path": "..."}],
  "warnings": [{"type": "...", "uri": "...", "detail": "..."}],
  "summary": {"total_sections": 0, "errors": 0, "warnings": 0}
}
```

### 10.2. `mdb context <URI>`

$$f: G \times v \to \text{ContextPayload}$$

Returns the structured context of a single node: its metadata, outgoing edges, and incoming edges (1-hop neighborhood).

* **Algorithm:** Direct index lookup + adjacency list read.
* **Complexity:** $O(\deg(v))$
* **Output schema:**
```json
{
  "uri": "...",
  "metadata": {},
  "outgoing": [{"uri": "...", "type": "ref|include"}],
  "incoming": [{"uri": "...", "type": "ref|include"}]
}
```

### 10.3. `mdb backlinks <URI>`

$$f: G \times v \to V_{in}$$

Returns all nodes with a directed edge pointing to $v$.

* **Algorithm:** Direct $O(1)$ lookup in `incoming_edges[v]`.
* **Complexity:** $O(1)$ lookup, $O(k)$ output where $k = |\text{backlinks}(v)|$
* **Output schema:**
```json
{"uri": "...", "backlinks": [{"uri": "...", "type": "ref|include"}]}
```

### 10.4. `mdb search <predicate>`

$$f: G \times \text{Predicate} \to V$$

Scans all nodes and returns those matching a metadata predicate.

* **Predicate syntax:** `key=value` (exact match), `key~=value` (substring match), `tag:value` (tag membership).
* **Algorithm:** Linear scan of all `ParsedSection.metadata` dicts.
* **Complexity:** $O(V)$
* **Output schema:**
```json
{"predicate": "...", "results": [{"uri": "...", "metadata": {}}]}
```

### 10.5. `mdb impact <URI>`

$$f: G \times v \to \{V_{direct}, V_{indirect}\}$$

Returns the set of all nodes that depend (directly or indirectly) on $v$ via the reverse graph $G^R$.

* **Algorithm:** BFS on $G^R$ starting at $v$.
* **Complexity:** $O(V + E)$
* **Output schema:**
```json
{
  "uri": "...",
  "direct": [{"uri": "..."}],
  "indirect": [{"uri": "..."}]
}
```

### 10.6. `mdb neighbors <URI> [--depth N]`

$$f: G \times v \times d \to V$$

Returns all nodes reachable from $v$ within $d$ hops in either direction.

* **Algorithm:** Bidirectional BFS from $v$, bounded by depth $d$.
* **Complexity:** $O(V + E)$ worst case; in practice bounded by graph diameter x branching factor.
* **Output schema:**
```json
{"uri": "...", "depth": 2, "neighbors": [{"uri": "...", "distance": 1, "direction": "outgoing|incoming"}]}
```

### 10.7. `mdb explain <URI_A> <URI_B>`

$$f: G \times v_a \times v_b \to \text{Paths}$$

Finds all simple paths between two nodes.

* **Algorithm:** DFS with backtracking, tracking visited set per path to avoid re-visits.
* **Complexity:** Exponential worst case; in practice bounded by graph structure.
* **Output schema:**
```json
{"from": "...", "to": "...", "paths": [[{"uri": "..."}]]}
```

### 10.8. `mdb diff <URI> [--since <git-ref>]`

$$f: G_{current} \times G_{historical} \to \Delta$$

Computes the structural difference between the current graph state and a historical snapshot.

* **Algorithm:** Set difference on $(V, E)$ between two index states. Historical state is reconstructed from git history.
* **Complexity:** $O(V + E)$
* **Output schema:**
```json
{
  "added_sections": [{"uri": "..."}],
  "removed_sections": [{"uri": "..."}],
  "added_edges": [{"from": "...", "to": "..."}],
  "removed_edges": [{"from": "...", "to": "..."}]
}
```

### 10.9. `mdb query <expression>`

$$f: G \times \text{BooleanExpr} \to V$$

Advanced boolean query over section metadata and structural pseudo-fields.
Supports AND, OR, NOT operators.

* **Syntax:** `tag:api AND owner:team-core NOT status:obsolete`
* **Predicate syntax:** `key=value` (exact match), `key~=value` (substring match), `tag:value` (tag membership), `key~=/regex/` (regex match).
* **Structural pseudo-fields:** `section` and `id` resolve to the section identifier; `path` and `file` resolve to the source file path; `heading` resolves to the Markdown heading text.
* **Algorithm:** Parse expression tree; evaluate each node against metadata and structural fields.
* **Complexity:** $O(V \cdot |expr|)$
* **Output schema:**
```json
{"expression": "...", "results": [{"uri": "...", "metadata": {}}]}
```

### 10.10. `mdb metadata get|update|unset <URI>`

$$f: M \times p \to M'$$

Reads or mutates the structured YAML metadata block attached to a section id.
Metadata commands operate only on the direct YAML block containing `section:`.
They never edit Markdown body content, directives, or arbitrary YAML blocks
outside the structured section metadata block.

* **Addressing:** `URI` selects the section. Optional dotted paths such as
  `owner.name` or `review.checklist.manual` select nested metadata values.
* **Read:** `mdb metadata get <URI> [path]` returns either the full metadata
  object or the selected dotted-path value.
* **Update:** `mdb metadata update <URI> <path> <json-value>` parses
  `<json-value>` as JSON, writes it to the selected path, creates missing
  intermediate mappings when safe, and persists the result as YAML.
* **Unset:** `mdb metadata unset <URI> <path>` removes the selected key without
  removing sibling metadata.
* **Protected field:** `section` is read-only through metadata write commands.
* **Errors:** missing sections, missing unset paths, invalid JSON values, and
  dotted paths crossing non-mapping values are reported as command errors.
* **Complexity:** $O(n)$ in the source file size due to source rewrite.
* **Output schemas:**
```json
{"uri": "...", "path": "owner.name | null", "value": {}}
{"uri": "...", "path": "owner.name", "metadata": {}}
```

### 10.11. `mdb context-compose <URI> [--depth N] [--token-limit N]`

$$f: G \times v \times d \times t \to \text{ContextPayload}$$

Bounded semantic materialization for LLM agent consumption. Composes the node tree up to depth $d$ and truncates the output to fit within a token budget $t$.

* **Algorithm:** DFS composition (same as `compose`) with an incremental token counter. Stops expansion when budget is approached; appends truncation markers.
* **Complexity:** $O(V + E)$ bounded by depth and token limit.
* **Output schema:**
```json
{
  "uri": "...",
  "depth": 2,
  "token_estimate": 1240,
  "truncated": false,
  "content": "..."
}
```

---

## 11. JSON Contract Schemas

All commands support a `--json` flag that produces machine-readable output. The schemas below are the normative contracts for all JSON outputs.

### 11.1. `mdb get <URI> --json`

```json
{
  "uri": "string",
  "file_path": "string",
  "source_start_line": "integer",
  "source_end_line": "integer",
  "content": "string"
}
```

### 11.2. `mdb tree <URI> --json`

```json
{
  "uri": "string",
  "tree": [
    {
      "uri": "string",
      "type": "ref | include",
      "depth": "integer",
      "children": []
    }
  ]
}
```

### 11.3. `mdb compose <URI> --json`

```json
{
  "uri": "string",
  "depth": "integer | null",
  "deduplicate": "boolean",
  "content": "string"
}
```

### 11.4. `mdb validate --json`

```json
{
  "errors": [
    {
      "type": "broken_ref | broken_include | duplicate_id | missing_payload | cycle",
      "uri": "string",
      "detail": "string"
    }
  ],
  "warnings": [
    {
      "type": "string",
      "uri": "string",
      "detail": "string"
    }
  ],
  "summary": {
    "total_sections": "integer",
    "total_edges": "integer",
    "errors": "integer",
    "warnings": "integer"
  }
}
```

Schema validation errors extend the base error object additively:

```json
{
  "type": "schema_validation_error | schema_not_found | schema_invalid | schema_unsupported_uri",
  "uri": "string",
  "detail": "string",
  "schema": "string",
  "schema_path": "string",
  "path": "string"
}
```

### 11.5. `mdb context <URI> --json`

```json
{
  "uri": "string",
  "metadata": "object",
  "outgoing": [{"uri": "string", "type": "ref | include"}],
  "incoming": [{"uri": "string", "type": "ref | include"}]
}
```

### 11.6. `mdb backlinks <URI> --json`

```json
{
  "uri": "string",
  "backlinks": [{"uri": "string", "type": "ref | include"}]
}
```

### 11.7. `mdb search <predicate> --json`

```json
{
  "predicate": "string",
  "results": [{"uri": "string", "metadata": "object"}]
}
```

### 11.8. `mdb impact <URI> --json`

```json
{
  "uri": "string",
  "direct": [{"uri": "string"}],
  "indirect": [{"uri": "string"}]
}
```

### 11.9. `mdb neighbors <URI> --json`

```json
{
  "uri": "string",
  "depth": "integer",
  "neighbors": [{"uri": "string", "distance": "integer", "direction": "outgoing | incoming"}]
}
```

### 11.10. `mdb explain <URI_A> <URI_B> --json`

```json
{
  "from": "string",
  "to": "string",
  "paths": [
    [{"uri": "string", "edge_type": "ref | include"}]
  ]
}
```

### 11.11. `mdb diff --json`

```json
{
  "since": "string",
  "added_sections": [{"uri": "string"}],
  "removed_sections": [{"uri": "string"}],
  "added_edges": [{"from": "string", "to": "string", "type": "string"}],
  "removed_edges": [{"from": "string", "to": "string", "type": "string"}]
}
```

### 11.12. `mdb query <expression> --json`

```json
{
  "expression": "string",
  "results": [{"uri": "string", "metadata": "object"}]
}
```

### 11.13. `mdb metadata get <URI> [path] --json`

```json
{
  "uri": "string",
  "path": "string | null",
  "value": "any JSON value"
}
```

### 11.14. `mdb metadata update|unset <URI> <path> --json`

```json
{
  "uri": "string",
  "path": "string",
  "metadata": "object"
}
```

### 11.15. `mdb context-compose <URI> --json`

```json
{
  "uri": "string",
  "depth": "integer",
  "token_estimate": "integer",
  "truncated": "boolean",
  "content": "string"
}
```

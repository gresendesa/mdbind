"""
CLI for mdbind — main entrypoint.

Commands:
  get <URI>     Extract a section with documentary fidelity (raw lines)
  tree <URI>    Display visual hierarchy of dependencies
  compose <URI> Materialize unified document (B-007)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from mdbind.parser import ParseError, parse_file

app = typer.Typer(
    name="mdb",
    help="MdBind — Structured memory in plain Markdown.",
    add_completion=False,
)
metadata_app = typer.Typer(help="Read and edit structured YAML metadata blocks.")
app.add_typer(metadata_app, name="metadata")

def _split_uri(uri: str) -> tuple[str, str]:
    """Divide 'arquivo.md#id' em ('arquivo.md', 'id'). Erro se sem fragmento."""
    if "#" not in uri:
        typer.echo(f"Erro: URI deve conter fragmento '#id'. Recebido: '{uri}'", err=True)
        raise typer.Exit(code=1)
    path_part, fragment = uri.split("#", 1)
    if not path_part:
        typer.echo(f"Erro: URI sem caminho de arquivo: '{uri}'", err=True)
        raise typer.Exit(code=1)
    if not fragment:
        typer.echo(f"Erro: URI sem id de secao: '{uri}'", err=True)
        raise typer.Exit(code=1)
    return path_part, fragment


def _json_dumps(payload: object, **kwargs) -> str:
    import json as json_mod

    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("default", str)
    return json_mod.dumps(payload, **kwargs)


def _resolve_section_file(uri: str) -> tuple[Path, str, str]:
    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()
    abs_uri = str(file_path) + "#" + section_id
    return file_path, section_id, abs_uri


def _validation_report(graph) -> tuple[list[dict], list[dict], dict]:
    from mdbind.schema_validation import validate_section_schemas

    errors: list[dict] = []
    warnings: list[dict] = []

    all_uris = set(graph.index.sections.keys())
    total_edges = sum(len(targets) for targets in graph.outgoing_edges.values())

    # 1. Broken refs and includes
    for src_uri, section in graph.index.sections.items():
        for directive in section.directives:
            if directive.type in ("ref", "include"):
                if directive.target_uri not in all_uris:
                    error_type = "broken_ref" if directive.type == "ref" else "broken_include"
                    errors.append({
                        "type": error_type,
                        "uri": src_uri,
                        "detail": f"target '{directive.target_uri}' not found in index",
                    })

    # 2. Include cycles (DFS execution-path tracking)
    def _dfs_cycle(uri: str, path: frozenset[str], visited_global: set[str]) -> None:
        if uri in path:
            errors.append({
                "type": "cycle",
                "uri": uri,
                "detail": f"include cycle detected involving '{uri}'",
            })
            return
        if uri in visited_global:
            return
        visited_global.add(uri)
        section = graph.index.sections.get(uri)
        if section is None:
            return
        new_path = path | {uri}
        for directive in section.directives:
            if directive.type == "include" and directive.target_uri in all_uris:
                _dfs_cycle(directive.target_uri, new_path, visited_global)

    visited_global: set[str] = set()
    for uri in all_uris:
        _dfs_cycle(uri, frozenset(), visited_global)

    # 3. Per-section local schema validation.
    errors.extend(validate_section_schemas(graph))

    summary = {
        "total_sections": len(all_uris),
        "total_edges": total_edges,
        "errors": len(errors),
        "warnings": len(warnings),
    }
    return errors, warnings, summary


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------

@metadata_app.command("get")
def metadata_get(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    path: Optional[str] = typer.Argument(None, help="Optional dotted metadata path."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Reads the structured YAML metadata block for a section.
    """
    from mdbind.metadata import MetadataError, get_metadata_value, read_metadata

    file_path, section_id, abs_uri = _resolve_section_file(uri)
    if not file_path.exists():
        typer.echo(f"Error: file not found: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    try:
        metadata = read_metadata(file_path, section_id)
        value = get_metadata_value(metadata, path)
    except (MetadataError, ParseError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(_json_dumps(
            {"uri": abs_uri, "path": path, "value": value},
            ensure_ascii=False,
            indent=2,
        ))
    else:
        import yaml

        typer.echo(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), nl=False)


@metadata_app.command("update")
def metadata_update(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    path: str = typer.Argument(..., help="Dotted metadata path to update."),
    value: str = typer.Argument(..., help="JSON value to write."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Updates a value inside a section structured YAML metadata block.
    """
    from mdbind.metadata import MetadataError, update_metadata_file

    file_path, section_id, abs_uri = _resolve_section_file(uri)
    if not file_path.exists():
        typer.echo(f"Error: file not found: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    try:
        metadata = update_metadata_file(file_path, section_id, path, value)
    except (MetadataError, ParseError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(_json_dumps(
            {"uri": abs_uri, "path": path, "metadata": metadata},
            ensure_ascii=False,
            indent=2,
        ))
    else:
        typer.echo(f"Updated metadata path '{path}' in '{abs_uri}'.")


@metadata_app.command("unset")
def metadata_unset(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    path: str = typer.Argument(..., help="Dotted metadata path to remove."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Removes a value from a section structured YAML metadata block.
    """
    from mdbind.metadata import MetadataError, unset_metadata_file

    file_path, section_id, abs_uri = _resolve_section_file(uri)
    if not file_path.exists():
        typer.echo(f"Error: file not found: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    try:
        metadata = unset_metadata_file(file_path, section_id, path)
    except (MetadataError, ParseError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(_json_dumps(
            {"uri": abs_uri, "path": path, "metadata": metadata},
            ensure_ascii=False,
            indent=2,
        ))
    else:
        typer.echo(f"Removed metadata path '{path}' from '{abs_uri}'.")


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

@app.command()
def get(
    uri: str = typer.Argument(..., help="URI of the section in the format file.md#id"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Extract a section with 100%% documentary fidelity (raw lines from the source file).
    """
    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()

    if not file_path.exists():
        typer.echo(f"Error: file not found: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    try:
        sections = parse_file(file_path)
    except ParseError as exc:
        typer.echo(f"Parse error: {exc}", err=True)
        raise typer.Exit(code=1)

    matched = next(
        (s for s in sections if str(s.metadata.get("id", "")) == section_id),
        None,
    )

    if matched is None:
        typer.echo(
            f"Error: section '{section_id}' not found in '{file_path}'",
            err=True,
        )
        raise typer.Exit(code=1)

    # Documentary slicing: preserves the exact text from the source file
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = matched.raw.source_start_line - 1  # base-0
    end = matched.raw.source_end_line          # exclusive slice = last line inclusive

    output = "".join(lines[start:end])
    # Garantir newline final sem adicionar extra
    if output and not output.endswith("\n"):
        output += "\n"

    if json_output:
        typer.echo(_json_dumps({
            "uri": uri,
            "file_path": str(file_path),
            "source_start_line": matched.raw.source_start_line,
            "source_end_line": matched.raw.source_end_line,
            "content": output,
        }, ensure_ascii=False))
    else:
        typer.echo(output, nl=False)


# ---------------------------------------------------------------------------
# tree
# ---------------------------------------------------------------------------

@app.command()
def tree(
    uri: str = typer.Argument(..., help="URI of the section in the format file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Root directory of the repository (default: directory of the file).",
    ),
    refs: bool = typer.Option(
        False, "--refs",
        help="Display backlinks (who depends on this section).",
    ),
    depth: Optional[int] = typer.Option(
        None, "--depth", "-d",
        help="Maximum depth of the tree (default: unlimited).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Display the visual hierarchy of dependencies of a section.
    """
    from mdbind.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()

    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Parse error: {exc}", err=True)
        raise typer.Exit(code=1)

    # Build absolute URI for lookup
    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Error: URI '{abs_uri}' not found in the index.", err=True)
        raise typer.Exit(code=1)

    if json_output:
        tree_data = _build_tree_outgoing(abs_uri, graph, visited=set(), depth=depth) if not refs else _build_tree_incoming(abs_uri, graph, visited=set(), depth=depth)
        typer.echo(_json_dumps({"uri": abs_uri, "tree": tree_data}, ensure_ascii=False))
    elif refs:
        _print_tree_incoming(abs_uri, graph, prefix="", visited=set(), depth=depth)
    else:
        _print_tree_outgoing(abs_uri, graph, prefix="", visited=set(), depth=depth)


def _label(uri: str, graph) -> str:
    section = graph.index.sections.get(uri)
    if section:
        title = section.metadata.get("title", section.metadata.get("id", uri))
        return f"{title}  [{uri}]"
    return uri


def _print_tree_outgoing(uri: str, graph, prefix: str, visited: set, depth: Optional[int] = None) -> None:
    marker = "(cycle)" if uri in visited else ""
    typer.echo(f"{prefix}{_label(uri, graph)} {marker}".rstrip())
    if uri in visited:
        return
    if depth is not None and depth <= 0:
        return
    visited = visited | {uri}
    children = sorted(graph.outgoing_edges.get(uri, set()))
    next_depth = None if depth is None else depth - 1
    for i, child in enumerate(children):
        connector = "└── " if i == len(children) - 1 else "├── "
        _print_tree_outgoing(child, graph, prefix + connector, visited, next_depth)


def _print_tree_incoming(uri: str, graph, prefix: str, visited: set, depth: Optional[int] = None) -> None:
    marker = "(cycle)" if uri in visited else ""
    typer.echo(f"{prefix}{_label(uri, graph)} {marker}".rstrip())
    if uri in visited:
        return
    if depth is not None and depth <= 0:
        return
    visited = visited | {uri}
    parents = sorted(graph.incoming_edges.get(uri, set()))
    next_depth = None if depth is None else depth - 1
    for i, parent in enumerate(parents):
        connector = "└── " if i == len(parents) - 1 else "├── "
        _print_tree_incoming(parent, graph, prefix + connector, visited, next_depth)


def _build_tree_outgoing(uri: str, graph, visited: set, depth: Optional[int] = None) -> list:
    if uri in visited or (depth is not None and depth <= 0):
        return []
    visited = visited | {uri}
    children = sorted(graph.outgoing_edges.get(uri, set()))
    next_depth = None if depth is None else depth - 1
    section = graph.index.sections.get(uri)
    edge_type = "include"  # default; edges are not typed in current model
    result = []
    for child in children:
        node = {
            "uri": child,
            "type": edge_type,
            "depth": (None if depth is None else depth - 1),
            "children": _build_tree_outgoing(child, graph, visited, next_depth),
        }
        result.append(node)
    return result


def _build_tree_incoming(uri: str, graph, visited: set, depth: Optional[int] = None) -> list:
    if uri in visited or (depth is not None and depth <= 0):
        return []
    visited = visited | {uri}
    parents = sorted(graph.incoming_edges.get(uri, set()))
    next_depth = None if depth is None else depth - 1
    result = []
    for parent in parents:
        node = {
            "uri": parent,
            "type": "incoming",
            "depth": (None if depth is None else depth - 1),
            "children": _build_tree_incoming(parent, graph, visited, next_depth),
        }
        result.append(node)
    return result


# ---------------------------------------------------------------------------
# compose
# ---------------------------------------------------------------------------

@app.command()
def compose(
    uri: str = typer.Argument(..., help="URI of the root section in the format file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Root directory of the repository (default: directory of the file).",
    ),
    strict: bool = typer.Option(False, "--strict", help="Abort on unresolved URI."),
    deduplicate: bool = typer.Option(False, "--deduplicate", help="Deduplicate repeated nodes."),
    json_output: bool = typer.Option(False, "--json", help="Export as structured JSON."),
    depth: Optional[int] = typer.Option(
        None, "--depth", "-d",
        help="Maximum depth of @include expansion (default: unlimited).",
    ),
) -> None:
    """
    Materializes a unified Markdown document by recursively expanding @include.
    """
    from mdbind.composer import compose as do_compose
    from mdbind.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()

    if not file_path.exists():
        typer.echo(f"Error: file not found: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Parse error: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Error: URI '{abs_uri}' not found in the index.", err=True)
        raise typer.Exit(code=1)

    collected_warnings: list[str] = []
    try:
        result = do_compose(
            abs_uri,
            graph,
            strict=strict,
            deduplicate=deduplicate,
            warnings=collected_warnings,
            depth=depth,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    for w in collected_warnings:
        typer.echo(f"Warning: {w}", err=True)

    if json_output:
        typer.echo(_json_dumps({"uri": abs_uri, "content": result}, ensure_ascii=False))
    else:
        typer.echo(result, nl=False)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@app.command()
def validate(
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Root directory of the repository (default: current directory).",
    ),
    file: Optional[Path] = typer.Option(
        None, "--file",
        help="Validate a single Markdown file in isolation.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Export result as JSON."),
) -> None:
    """
    Verifies the structural integrity of the Markdown graph repository.

    Checks: broken refs/includes, duplicate section IDs, include cycles,
    sections without required payload.

    Exit code 0 = clean, 1 = errors found.
    """
    from mdbind.index import index_repository
    from mdbind.models import SectionGraph, SectionIndex

    if root is not None and file is not None:
        detail = "--root and --file cannot be used together"
        if json_output:
            errors = [{"type": "invalid_options", "uri": "", "detail": detail}]
            summary = {"total_sections": 0, "total_edges": 0, "errors": 1, "warnings": 0}
            typer.echo(_json_dumps({"errors": errors, "warnings": [], "summary": summary}, ensure_ascii=False))
        else:
            typer.echo(f"Error: {detail}", err=True)
        raise typer.Exit(code=1)

    try:
        if file is not None:
            file_path = file.resolve()
            if not file_path.exists():
                raise ParseError(f"file not found: {file_path}")
            if not file_path.is_file():
                raise ParseError(f"not a file: {file_path}")

            sections = parse_file(file_path)
            index = SectionIndex()
            graph = SectionGraph(index=index)
            for section in sections:
                try:
                    index.add(section)
                except ValueError as exc:
                    raise ParseError(str(exc)) from exc
                for directive in section.directives:
                    if directive.type in ("ref", "include"):
                        graph.add_edge(section.uri, directive.target_uri)
        else:
            repo_root = (root.resolve() if root else Path.cwd())
            graph = index_repository(repo_root)
    except ParseError as exc:
        errors = [{"type": "parse_error", "uri": "", "detail": str(exc)}]
        summary = {"total_sections": 0, "total_edges": 0, "errors": 1, "warnings": 0}
        if json_output:
            typer.echo(_json_dumps({"errors": errors, "warnings": [], "summary": summary}, ensure_ascii=False))
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    errors, warnings, summary = _validation_report(graph)

    if json_output:
        typer.echo(_json_dumps(
            {"errors": errors, "warnings": warnings, "summary": summary},
            ensure_ascii=False,
            indent=2,
        ))
    else:
        if errors:
            for e in errors:
                typer.echo(f"ERROR [{e['type']}] {e['uri']}: {e['detail']}")
        if warnings:
            for w in warnings:
                typer.echo(f"WARNING [{w['type']}] {w['uri']}: {w['detail']}")
        if not errors and not warnings:
            typer.echo(f"OK — {summary['total_sections']} sections, {summary['total_edges']} edges, no issues found.")
        else:
            typer.echo(
                f"\nSummary: {summary['total_sections']} sections, "
                f"{summary['errors']} errors, {summary['warnings']} warnings.",
                err=True,
            )

    if errors:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# context (B-016)
# ---------------------------------------------------------------------------

@app.command()
def context(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Repository root directory (default: file directory).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Returns structured context of a section: metadata, outgoing edges, incoming edges.
    """
    from mdbind.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()
    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Error: URI '{abs_uri}' not found in index.", err=True)
        raise typer.Exit(code=1)

    section = graph.index.sections[abs_uri]

    outgoing = [
        {"uri": t, "type": _edge_type(abs_uri, t, section)}
        for t in sorted(graph.outgoing_edges.get(abs_uri, set()))
    ]
    incoming = [
        {"uri": s, "type": "incoming"}
        for s in sorted(graph.incoming_edges.get(abs_uri, set()))
    ]

    if json_output:
        typer.echo(_json_dumps({
            "uri": abs_uri,
            "metadata": section.metadata,
            "outgoing": outgoing,
            "incoming": incoming,
        }, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"URI: {abs_uri}")
        typer.echo(f"Metadata: {section.metadata}")
        if outgoing:
            typer.echo("Outgoing:")
            for e in outgoing:
                typer.echo(f"  [{e['type']}] {e['uri']}")
        if incoming:
            typer.echo("Incoming:")
            for e in incoming:
                typer.echo(f"  [ref] {e['uri']}")


def _edge_type(src_uri: str, target_uri: str, section) -> str:
    for d in section.directives:
        if d.target_uri == target_uri:
            return d.type
    return "ref"


# ---------------------------------------------------------------------------
# backlinks (B-017)
# ---------------------------------------------------------------------------

@app.command()
def backlinks(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Repository root directory (default: file directory).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Lists all sections that reference this URI (incoming edges).
    """
    from mdbind.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()
    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Error: URI '{abs_uri}' not found in index.", err=True)
        raise typer.Exit(code=1)

    bl = sorted(graph.incoming_edges.get(abs_uri, set()))
    result = [{"uri": s, "type": _edge_type(s, abs_uri, graph.index.sections.get(s))} for s in bl]

    if json_output:
        typer.echo(_json_dumps({"uri": abs_uri, "backlinks": result}, ensure_ascii=False, indent=2))
    else:
        if not result:
            typer.echo(f"No backlinks found for '{abs_uri}'.")
        else:
            typer.echo(f"Backlinks for '{abs_uri}':")
            for e in result:
                typer.echo(f"  [{e['type']}] {e['uri']}")


# ---------------------------------------------------------------------------
# search (B-018)
# ---------------------------------------------------------------------------

@app.command()
def search(
    predicate: str = typer.Argument(..., help="Predicate: key=value, key~=value, or tag:value"),
    root: Path = typer.Option(
        ..., "--root", "-r",
        help="Repository root directory.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Searches sections by metadata predicate. Supports key=value, key~=value, tag:value.
    """
    import re
    from mdbind.index import index_repository

    try:
        graph = index_repository(root.resolve())
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # Parse predicate
    tag_match = re.match(r"^tag:(.+)$", predicate)
    exact_match = re.match(r"^([^~=]+)=(.+)$", predicate)
    substring_match = re.match(r"^([^~=]+)~=(.+)$", predicate)

    def _matches(metadata: dict) -> bool:
        if tag_match:
            tag_val = tag_match.group(1)
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            return tag_val in tags
        if substring_match:
            key, val = substring_match.group(1), substring_match.group(2)
            return val.lower() in str(metadata.get(key, "")).lower()
        if exact_match:
            key, val = exact_match.group(1), exact_match.group(2)
            return str(metadata.get(key, "")) == val
        return False

    results = [
        {"uri": uri, "metadata": section.metadata}
        for uri, section in graph.index.sections.items()
        if _matches(section.metadata)
    ]
    results.sort(key=lambda r: r["uri"])

    if json_output:
        typer.echo(_json_dumps({"predicate": predicate, "results": results}, ensure_ascii=False, indent=2))
    else:
        if not results:
            typer.echo(f"No sections found matching '{predicate}'.")
        else:
            typer.echo(f"Found {len(results)} section(s) matching '{predicate}':")
            for r in results:
                typer.echo(f"  {r['uri']}")


# ---------------------------------------------------------------------------
# impact (B-019)
# ---------------------------------------------------------------------------

@app.command()
def impact(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Repository root directory (default: file directory).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Returns all sections that depend (directly or indirectly) on this URI via reverse BFS.
    """
    from collections import deque
    from mdbind.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()
    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Error: URI '{abs_uri}' not found in index.", err=True)
        raise typer.Exit(code=1)

    # BFS on reverse graph (incoming edges)
    direct = sorted(graph.incoming_edges.get(abs_uri, set()))
    visited = set(direct) | {abs_uri}
    queue = deque(direct)
    indirect: list[str] = []

    while queue:
        current = queue.popleft()
        for parent in graph.incoming_edges.get(current, set()):
            if parent not in visited:
                visited.add(parent)
                indirect.append(parent)
                queue.append(parent)

    indirect.sort()

    direct_out = [{"uri": u} for u in direct]
    indirect_out = [{"uri": u} for u in indirect]

    if json_output:
        typer.echo(_json_dumps({
            "uri": abs_uri,
            "direct": direct_out,
            "indirect": indirect_out,
        }, ensure_ascii=False, indent=2))
    else:
        if not direct and not indirect:
            typer.echo(f"No sections depend on '{abs_uri}'.")
        else:
            if direct:
                typer.echo(f"Direct dependents of '{abs_uri}':")
                for e in direct_out:
                    typer.echo(f"  {e['uri']}")
            if indirect:
                typer.echo(f"Indirect dependents:")
                for e in indirect_out:
                    typer.echo(f"  {e['uri']}")


# ---------------------------------------------------------------------------
# neighbors (B-020)
# ---------------------------------------------------------------------------

@app.command()
def neighbors(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Repository root directory (default: file directory).",
    ),
    depth: int = typer.Option(1, "--depth", "-d", help="Max hops in either direction."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Returns all nodes reachable from URI within --depth hops (bidirectional).
    """
    from collections import deque
    from mdbind.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()
    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Error: URI '{abs_uri}' not found in index.", err=True)
        raise typer.Exit(code=1)

    # BFS bidirectional
    visited: dict[str, tuple[int, str]] = {}  # uri -> (distance, direction)
    queue: deque[tuple[str, int]] = deque([(abs_uri, 0)])
    visited[abs_uri] = (0, "self")

    while queue:
        current, dist = queue.popleft()
        if dist >= depth:
            continue
        for nbr in graph.outgoing_edges.get(current, set()):
            if nbr not in visited:
                visited[nbr] = (dist + 1, "outgoing")
                queue.append((nbr, dist + 1))
        for nbr in graph.incoming_edges.get(current, set()):
            if nbr not in visited:
                visited[nbr] = (dist + 1, "incoming")
                queue.append((nbr, dist + 1))

    result = sorted(
        [{"uri": u, "distance": d, "direction": dir_}
         for u, (d, dir_) in visited.items() if u != abs_uri],
        key=lambda x: (x["distance"], x["uri"]),
    )

    if json_output:
        typer.echo(_json_dumps(
            {"uri": abs_uri, "depth": depth, "neighbors": result},
            ensure_ascii=False, indent=2,
        ))
    else:
        if not result:
            typer.echo(f"No neighbors found within depth {depth}.")
        else:
            for n in result:
                typer.echo(f"  [d={n['distance']} {n['direction']}] {n['uri']}")


# ---------------------------------------------------------------------------
# explain (B-021)
# ---------------------------------------------------------------------------

@app.command()
def explain(
    uri_a: str = typer.Argument(..., help="Source URI file.md#id"),
    uri_b: str = typer.Argument(..., help="Target URI file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Repository root directory.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Finds all simple directed paths from URI_A to URI_B.
    """
    from mdbind.index import index_repository

    def _resolve(uri: str, default_parent: Path) -> str:
        file_str, frag = _split_uri(uri)
        return str(Path(file_str).resolve()) + "#" + frag

    file_path_a = Path(_split_uri(uri_a)[0]).resolve()
    repo_root = root.resolve() if root else file_path_a.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_a = _resolve(uri_a, file_path_a.parent)
    abs_b = _resolve(uri_b, file_path_a.parent)

    for u, label in [(abs_a, "source"), (abs_b, "target")]:
        if u not in graph.index.sections:
            typer.echo(f"Error: {label} URI '{u}' not found in index.", err=True)
            raise typer.Exit(code=1)

    # DFS all simple paths (following outgoing edges only)
    all_paths: list[list[str]] = []

    def _dfs(current: str, target: str, path: list[str], visited: set[str]) -> None:
        if current == target:
            all_paths.append(list(path))
            return
        for nxt in graph.outgoing_edges.get(current, set()):
            if nxt not in visited:
                path.append(nxt)
                visited.add(nxt)
                _dfs(nxt, target, path, visited)
                path.pop()
                visited.discard(nxt)

    _dfs(abs_a, abs_b, [abs_a], {abs_a})

    paths_out = [
        [{"uri": step, "edge_type": _edge_type(path[i], step, graph.index.sections.get(path[i]))}
         for i, step in enumerate(path[1:], 1)]
        for path in all_paths
    ]
    # Prepend source node to each path for full representation
    paths_full = [
        [{"uri": path[0], "edge_type": None}] + edge_list
        for path, edge_list in zip(all_paths, paths_out)
    ]

    if json_output:
        typer.echo(_json_dumps(
            {"from": abs_a, "to": abs_b, "paths": paths_full},
            ensure_ascii=False, indent=2,
        ))
    else:
        if not all_paths:
            typer.echo(f"No paths found from '{abs_a}' to '{abs_b}'.")
        else:
            typer.echo(f"Found {len(all_paths)} path(s):")
            for i, path in enumerate(all_paths, 1):
                typer.echo(f"  Path {i}: " + " → ".join(path))


# ---------------------------------------------------------------------------
# diff (B-022)
# ---------------------------------------------------------------------------

@app.command()
def diff(
    root: Path = typer.Option(
        ..., "--root", "-r",
        help="Repository root directory.",
    ),
    since: str = typer.Option(
        "HEAD~1", "--since",
        help="Git ref to compare against (default: HEAD~1).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Computes structural diff of the graph against a historical git ref.
    """
    import subprocess
    import tempfile
    import shutil
    from mdbind.index import index_repository
    from mdbind.parser import parse_text
    from mdbind.models import SectionGraph, SectionIndex

    repo_root = root.resolve()

    # Build current graph
    try:
        current_graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Error (current): {exc}", err=True)
        raise typer.Exit(code=1)

    # Find git root
    try:
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("Error: not a git repository or git not available.", err=True)
        raise typer.Exit(code=1)

    # List .md files tracked by git at the given ref
    try:
        tracked = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", since],
            cwd=git_root,
            stderr=subprocess.DEVNULL,
        ).decode().splitlines()
    except subprocess.CalledProcessError:
        typer.echo(f"Error: git ref '{since}' not found.", err=True)
        raise typer.Exit(code=1)

    md_files_at_ref = [f for f in tracked if f.endswith(".md")]

    # Build historical graph in memory from git content
    hist_index = SectionIndex()
    hist_graph = SectionGraph(index=hist_index)

    for rel_path in md_files_at_ref:
        try:
            content = subprocess.check_output(
                ["git", "show", f"{since}:{rel_path}"],
                cwd=git_root,
                stderr=subprocess.DEVNULL,
            ).decode(errors="replace")
        except subprocess.CalledProcessError:
            continue

        abs_path = Path(git_root) / rel_path
        try:
            sections = parse_text(content, str(abs_path))
        except ParseError:
            continue

        for section in sections:
            try:
                hist_index.add(section)
            except ValueError:
                continue
            for directive in section.directives:
                if directive.type in ("ref", "include"):
                    hist_graph.add_edge(section.uri, directive.target_uri)

    # Compute diff
    current_uris = set(current_graph.index.sections.keys())
    hist_uris = set(hist_graph.index.sections.keys())

    added_sections = [{"uri": u} for u in sorted(current_uris - hist_uris)]
    removed_sections = [{"uri": u} for u in sorted(hist_uris - current_uris)]

    current_edges: set[tuple[str, str]] = set()
    for src, targets in current_graph.outgoing_edges.items():
        for tgt in targets:
            current_edges.add((src, tgt))

    hist_edges: set[tuple[str, str]] = set()
    for src, targets in hist_graph.outgoing_edges.items():
        for tgt in targets:
            hist_edges.add((src, tgt))

    added_edges = [{"from": s, "to": t, "type": "edge"} for s, t in sorted(current_edges - hist_edges)]
    removed_edges = [{"from": s, "to": t, "type": "edge"} for s, t in sorted(hist_edges - current_edges)]

    result = {
        "since": since,
        "added_sections": added_sections,
        "removed_sections": removed_sections,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
    }

    if json_output:
        typer.echo(_json_dumps(result, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"Diff against '{since}':")
        typer.echo(f"  +{len(added_sections)} sections, -{len(removed_sections)} sections")
        typer.echo(f"  +{len(added_edges)} edges, -{len(removed_edges)} edges")
        for s in added_sections:
            typer.echo(f"  + [section] {s['uri']}")
        for s in removed_sections:
            typer.echo(f"  - [section] {s['uri']}")
        for e in added_edges:
            typer.echo(f"  + [edge] {e['from']} → {e['to']}")
        for e in removed_edges:
            typer.echo(f"  - [edge] {e['from']} → {e['to']}")


# ---------------------------------------------------------------------------
# query (B-023)
# ---------------------------------------------------------------------------

@app.command()
def query(
    expression: str = typer.Argument(..., help="Boolean expression: tag:api AND owner:team NOT status:obsolete"),
    root: Path = typer.Option(
        ..., "--root", "-r",
        help="Repository root directory.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Advanced boolean metadata query. Supports AND, OR, NOT, parentheses, and predicates.

    Predicate formats: key=value, key~=value, tag:value
    """
    import re
    from mdbind.index import index_repository

    try:
        graph = index_repository(root.resolve())
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Tokenizer ---
    _TOKEN_RE = re.compile(
        r'\(|\)|AND\b|OR\b|NOT\b|[^\s()]+',
        re.IGNORECASE,
    )

    def _tokenize(expr: str) -> list[str]:
        return _TOKEN_RE.findall(expr)

    def _field_value(section, key: str):
        metadata = section.metadata
        if key in ("section", "id"):
            return metadata.get("id", "")
        if key in ("path", "file"):
            return section.file_path
        if key == "heading":
            return section.raw.heading_text
        return metadata.get(key, "")

    # --- Predicate evaluator (reuses search logic) ---
    def _eval_predicate(pred: str, section) -> bool:
        metadata = section.metadata
        tag_m = re.match(r"^tag:(.+)$", pred)
        sub_m = re.match(r"^([^~=]+)~=(.+)$", pred)
        exact_m = re.match(r"^([^~=]+)=(.+)$", pred)
        if tag_m:
            tag_val = tag_m.group(1)
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            return tag_val in tags
        if sub_m:
            key, val = sub_m.group(1), sub_m.group(2)
            if val.startswith("/") and val.endswith("/") and len(val) >= 2:
                pattern = val[1:-1]
                return re.search(pattern, str(_field_value(section, key))) is not None
            return val.lower() in str(_field_value(section, key)).lower()
        if exact_m:
            key, val = exact_m.group(1), exact_m.group(2)
            return str(_field_value(section, key)) == val
        return False

    # --- Recursive descent parser ---
    class _Parser:
        def __init__(self, tokens: list[str]) -> None:
            self.tokens = tokens
            self.pos = 0

        def peek(self) -> str | None:
            return self.tokens[self.pos] if self.pos < len(self.tokens) else None

        def consume(self) -> str:
            tok = self.tokens[self.pos]
            self.pos += 1
            return tok

        def parse_expr(self):
            left = self.parse_term()
            while self.peek() and self.peek().upper() == "OR":
                self.consume()
                right = self.parse_term()
                left_fn = left
                right_fn = right
                left = lambda section, l=left_fn, r=right_fn: l(section) or r(section)
            return left

        def parse_term(self):
            left = self.parse_factor()
            while self.peek() and self.peek().upper() == "AND":
                self.consume()
                right = self.parse_factor()
                left_fn = left
                right_fn = right
                left = lambda section, l=left_fn, r=right_fn: l(section) and r(section)
            return left

        def parse_factor(self):
            tok = self.peek()
            if tok is None:
                return lambda section: True
            if tok.upper() == "NOT":
                self.consume()
                inner = self.parse_factor()
                return lambda section, f=inner: not f(section)
            if tok == "(":
                self.consume()
                expr = self.parse_expr()
                if self.peek() == ")":
                    self.consume()
                return expr
            pred = self.consume()
            return lambda section, p=pred: _eval_predicate(p, section)

    try:
        tokens = _tokenize(expression)
        parser = _Parser(tokens)
        matcher = parser.parse_expr()
    except Exception as exc:
        typer.echo(f"Error parsing expression: {exc}", err=True)
        raise typer.Exit(code=1)

    try:
        results = sorted(
            [{"uri": uri, "metadata": section.metadata}
             for uri, section in graph.index.sections.items()
             if matcher(section)],
            key=lambda r: r["uri"],
        )
    except re.error as exc:
        typer.echo(f"Error parsing expression: invalid regex: {exc}", err=True)
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(_json_dumps(
            {"expression": expression, "results": results},
            ensure_ascii=False, indent=2,
        ))
    else:
        if not results:
            typer.echo(f"No sections matched '{expression}'.")
        else:
            typer.echo(f"Found {len(results)} section(s):")
            for r in results:
                typer.echo(f"  {r['uri']}")


# ---------------------------------------------------------------------------
# context-compose (B-024)
# ---------------------------------------------------------------------------

@app.command(name="context-compose")
def context_compose(
    uri: str = typer.Argument(..., help="Section URI in the format file.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Repository root directory (default: file directory).",
    ),
    depth: Optional[int] = typer.Option(
        None, "--depth", "-d",
        help="Max inclusion depth (default: unlimited).",
    ),
    token_limit: Optional[int] = typer.Option(
        None, "--token-limit", "-t",
        help="Approximate token budget (1 token ≈ 4 chars). Truncates when exceeded.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Bounded semantic materialization for LLM consumption.
    Like compose, but respects --depth and --token-limit budgets.
    """
    from mdbind.composer import compose as do_compose
    from mdbind.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()
    repo_root = root.resolve() if root else file_path.parent

    if not file_path.exists():
        typer.echo(f"Error: file not found: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Error: URI '{abs_uri}' not found in index.", err=True)
        raise typer.Exit(code=1)

    collected_warnings: list[str] = []
    try:
        content = do_compose(
            abs_uri,
            graph,
            strict=False,
            deduplicate=False,
            warnings=collected_warnings,
            depth=depth,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    truncated = False
    if token_limit is not None:
        char_limit = token_limit * 4
        if len(content) > char_limit:
            content = content[:char_limit]
            truncated = True

    token_estimate = len(content) // 4

    if json_output:
        typer.echo(_json_dumps({
            "uri": abs_uri,
            "depth": depth,
            "token_estimate": token_estimate,
            "truncated": truncated,
            "content": content,
        }, ensure_ascii=False))
    else:
        if truncated:
            typer.echo(f"# [truncated at ~{token_limit} tokens]\n", err=True)
        typer.echo(content, nl=False)

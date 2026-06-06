"""
CLI do mdgraph — entrypoint principal.

Comandos:
  get <URI>     Extrai uma secao com fidelidade documental (linhas brutas)
  tree <URI>    Exibe hierarquia visual de dependencias
  compose <URI> Materializa documento unificado (B-007)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from mdgraph.parser import ParseError, parse_file

app = typer.Typer(
    name="mdgraph",
    help="Motor CLI de parsing e composicao documental em grafos Markdown.",
    add_completion=False,
)

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


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

@app.command()
def get(
    uri: str = typer.Argument(..., help="URI da secao no formato arquivo.md#id"),
) -> None:
    """
    Extrai uma secao com 100%% de fidelidade documental (linhas brutas do arquivo fonte).
    """
    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()

    if not file_path.exists():
        typer.echo(f"Erro: arquivo nao encontrado: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    try:
        sections = parse_file(file_path)
    except ParseError as exc:
        typer.echo(f"Erro de parsing: {exc}", err=True)
        raise typer.Exit(code=1)

    matched = next(
        (s for s in sections if str(s.metadata.get("id", "")) == section_id),
        None,
    )

    if matched is None:
        typer.echo(
            f"Erro: secao '{section_id}' nao encontrada em '{file_path}'",
            err=True,
        )
        raise typer.Exit(code=1)

    # Fatiamento documental: preserva o texto exato do arquivo fonte
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = matched.raw.source_start_line - 1  # base-0
    end = matched.raw.source_end_line          # slice exclusivo = ultima linha inclusiva

    output = "".join(lines[start:end])
    # Garantir newline final sem adicionar extra
    if output and not output.endswith("\n"):
        output += "\n"

    typer.echo(output, nl=False)


# ---------------------------------------------------------------------------
# tree
# ---------------------------------------------------------------------------

@app.command()
def tree(
    uri: str = typer.Argument(..., help="URI da secao no formato arquivo.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Diretorio raiz do repositorio (padrao: diretorio do arquivo).",
    ),
    refs: bool = typer.Option(
        False, "--refs",
        help="Exibir backlinks (quem depende desta secao).",
    ),
    depth: Optional[int] = typer.Option(
        None, "--depth", "-d",
        help="Profundidade maxima da arvore (padrao: ilimitada).",
    ),
) -> None:
    """
    Exibe a hierarquia visual de dependencias de uma secao.
    """
    from mdgraph.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()

    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Erro de parsing: {exc}", err=True)
        raise typer.Exit(code=1)

    # Montar URI absoluta para lookup
    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Erro: URI '{abs_uri}' nao encontrada no indice.", err=True)
        raise typer.Exit(code=1)

    if refs:
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
    marker = "(ciclo)" if uri in visited else ""
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
    marker = "(ciclo)" if uri in visited else ""
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


# ---------------------------------------------------------------------------
# compose
# ---------------------------------------------------------------------------

@app.command()
def compose(
    uri: str = typer.Argument(..., help="URI da secao raiz no formato arquivo.md#id"),
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Diretorio raiz do repositorio (padrao: diretorio do arquivo).",
    ),
    strict: bool = typer.Option(False, "--strict", help="Abortar em URI nao resolvida."),
    deduplicate: bool = typer.Option(False, "--deduplicate", help="Deduplicar nos repetidos."),
    json_output: bool = typer.Option(False, "--json", help="Exportar como JSON estruturado."),
    depth: Optional[int] = typer.Option(
        None, "--depth", "-d",
        help="Profundidade maxima de expansao de @include (padrao: ilimitada).",
    ),
) -> None:
    """
    Materializa um documento Markdown unificado expandindo @include recursivamente.
    """
    import json as json_mod
    from mdgraph.composer import compose as do_compose
    from mdgraph.index import index_repository

    file_path_str, section_id = _split_uri(uri)
    file_path = Path(file_path_str).resolve()

    if not file_path.exists():
        typer.echo(f"Erro: arquivo nao encontrado: '{file_path}'", err=True)
        raise typer.Exit(code=1)

    repo_root = root.resolve() if root else file_path.parent

    try:
        graph = index_repository(repo_root)
    except ParseError as exc:
        typer.echo(f"Erro de parsing: {exc}", err=True)
        raise typer.Exit(code=1)

    abs_uri = str(file_path) + "#" + section_id

    if abs_uri not in graph.index.sections:
        typer.echo(f"Erro: URI '{abs_uri}' nao encontrada no indice.", err=True)
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
        typer.echo(f"Erro: {exc}", err=True)
        raise typer.Exit(code=1)

    for w in collected_warnings:
        typer.echo(f"Aviso: {w}", err=True)

    if json_output:
        typer.echo(json_mod.dumps({"uri": abs_uri, "content": result}, ensure_ascii=False))
    else:
        typer.echo(result, nl=False)

"""
Parser Markdown: pipeline Markdown -> AST -> RawSection -> ParsedSection.

Etapas cobertas (spec section 2):
  1. Geracao de AST via markdown-it-py
  2. Section Discovery -> RawSection
  3. Metadata Binding -> ParsedSection
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from markdown_it import MarkdownIt

from mdgraph.directives import bind_directives
from mdgraph.models import Directive, ParsedSection, RawSection


# ---------------------------------------------------------------------------
# Erros de parsing
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


# ---------------------------------------------------------------------------
# Etapa 1: Geracao de AST
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list:
    md = MarkdownIt()
    return md.parse(text)


# ---------------------------------------------------------------------------
# Etapa 2: Section Discovery -> List[RawSection]
# ---------------------------------------------------------------------------

def _discover_sections(tokens: list) -> List[RawSection]:
    """
    Varre a lista plana de tokens e delimita secoes por heading_open.
    Uma secao vai do seu heading_open ate o proximo heading_open de nivel <= ao seu,
    ou ate o fim do documento.
    """
    # Coletar posicoes dos headings
    heading_positions = []
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            level = int(tok.tag[1])  # "h1" -> 1, "h2" -> 2, etc.
            # source_start_line: markdown-it usa base-0, convertemos para base-1
            source_line = (tok.map[0] + 1) if tok.map else 0
            heading_positions.append((i, level, source_line))

    raws: List[RawSection] = []
    for idx, (token_start, level, source_start_line) in enumerate(heading_positions):
        # Texto do heading: token seguinte e heading_content, proximo e heading_close
        heading_text_tok = tokens[token_start + 1]
        heading_text = heading_text_tok.children[0].content if heading_text_tok.children else ""

        # Determinar token_end e source_end_line
        token_end = len(tokens) - 1
        source_end_line = _last_source_line(tokens)

        for future_start, future_level, future_source in heading_positions[idx + 1:]:
            if future_level <= level:
                # A proxima secao de mesmo nivel ou superior encerra esta
                token_end = future_start - 1
                source_end_line = future_source - 1
                break

        raws.append(RawSection(
            heading_level=level,
            heading_text=heading_text,
            token_start=token_start,
            token_end=token_end,
            source_start_line=source_start_line,
            source_end_line=source_end_line,
        ))

    return raws


def _last_source_line(tokens: list) -> int:
    """Retorna a ultima linha fonte referenciada nos tokens (base-1)."""
    last = 1
    for tok in reversed(tokens):
        if tok.map:
            last = tok.map[1]  # map[1] ja e o indice exclusivo (base-0), vira base-1
            break
    return last


# ---------------------------------------------------------------------------
# Etapa 3: Metadata Binding -> ParsedSection
# ---------------------------------------------------------------------------

def _bind_metadata(
    raw: RawSection,
    tokens: list,
    file_path: str,
) -> ParsedSection:
    """
    Analisa os tokens internos da RawSection buscando o bloco 'section' (YAML).
    Aplica as validacoes da spec section 3.
    """
    # +3 pula: heading_open, inline (texto), heading_close
    # O scan termina no primeiro heading interno (qualquer nivel), pois o bloco
    # section so pode estar no conteudo direto da secao, nao em sub-secoes.
    all_inner = tokens[raw.token_start + 3: raw.token_end + 1]
    inner_tokens: list = []
    for tok in all_inner:
        if tok.type == "heading_open":
            break
        inner_tokens.append(tok)

    section_blocks: list[str] = []
    first_text_seen = False
    section_block_index = -1  # posicao do primeiro bloco section nos inner_tokens

    i = 0
    while i < len(inner_tokens):
        tok = inner_tokens[i]

        if tok.type == "fence" and tok.info.strip() == "yaml":
            parsed_yaml = None
            try:
                parsed_yaml = yaml.safe_load(tok.content) or {}
            except yaml.YAMLError:
                parsed_yaml = {}
            if not isinstance(parsed_yaml, dict) or "section" not in parsed_yaml:
                # Bloco yaml sem campo 'section' e ignorado (yaml generico)
                first_text_seen = True
                i += 1
                continue
            if first_text_seen and section_block_index == -1:
                raise ParseError(
                    f"payload nao e o primeiro bloco na secao '{raw.heading_text}' "
                    f"(linha {raw.source_start_line})"
                )
            section_blocks.append(tok.content)
            if section_block_index == -1:
                section_block_index = i
        elif tok.type in ("paragraph_open", "fence", "bullet_list_open",
                          "ordered_list_open", "blockquote_open", "html_block",
                          "table_open", "hr"):
            # Qualquer bloco textual que nao seja o bloco section
            if tok.type != "fence":  # fence ja tratado acima
                first_text_seen = True
        elif tok.type == "inline" and tok.content.strip():
            first_text_seen = True

        i += 1

    if len(section_blocks) > 1:
        raise ParseError(
            f"bloco section duplicado na secao '{raw.heading_text}' "
            f"(linha {raw.source_start_line})"
        )

    if not section_blocks:
        # Secao sem bloco section: metadata vazio, sem erro
        # Nao podemos construir ParsedSection pois falta 'id' — retornamos None
        # para que o chamador decida se ignora ou errou
        return None  # type: ignore[return-value]

    raw_yaml = section_blocks[0]
    try:
        metadata = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        raise ParseError(
            f"YAML invalido no bloco section da secao '{raw.heading_text}': {exc}"
        ) from exc

    if not isinstance(metadata, dict):
        raise ParseError(
            f"bloco section da secao '{raw.heading_text}' nao e um mapeamento YAML valido"
        )

    if not metadata.get("section"):
        raise ParseError(
            f"secao sem payload obrigatorio: campo 'section' ausente na secao "
            f"'{raw.heading_text}' (linha {raw.source_start_line})"
        )

    section_id = str(metadata.pop("section"))
    metadata["id"] = section_id
    uri = f"{file_path}#{section_id}"

    return ParsedSection(
        raw=raw,
        uri=uri,
        file_path=file_path,
        metadata=metadata,
        directives=[],  # populado em B-003
    )


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def parse_file(file_path: str | Path) -> List[ParsedSection]:
    """
    Executa o pipeline completo para um arquivo .md.
    Retorna apenas as ParsedSections que possuem bloco section (com id).
    Secoes sem bloco section sao silenciosamente ignoradas.
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    return parse_text(text, file_path=str(path))


def parse_text(text: str, file_path: str = "<string>") -> List[ParsedSection]:
    """
    Executa o pipeline completo sobre texto Markdown bruto.
    """
    tokens = _tokenize(text)
    raws = _discover_sections(tokens)

    seen_ids: set[str] = set()
    sections: List[ParsedSection] = []

    for raw in raws:
        parsed = _bind_metadata(raw, tokens, file_path)
        if parsed is None:
            continue

        section_id = str(parsed.metadata["id"])
        if section_id in seen_ids:
            raise ParseError(
                f"id duplicado '{section_id}' no arquivo '{file_path}'"
            )
        seen_ids.add(section_id)
        # Etapa 4: tokenizar diretivas
        parsed = bind_directives(parsed, tokens)
        sections.append(parsed)

    return sections

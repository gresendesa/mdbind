from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt

from mdbind.parser import ParseError, _discover_sections


class MetadataError(Exception):
    pass


@dataclass(frozen=True)
class MetadataBlock:
    metadata: dict[str, Any]
    fence_start_line: int
    fence_end_line: int


def read_metadata(file_path: str | Path, section_id: str) -> dict[str, Any]:
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    return _find_metadata_block(text, section_id).metadata


def get_metadata_value(metadata: dict[str, Any], dotted_path: str | None = None) -> Any:
    if not dotted_path:
        return metadata

    current: Any = metadata
    for part in _split_dotted_path(dotted_path):
        if not isinstance(current, dict):
            raise MetadataError(
                f"dotted path '{dotted_path}' cannot be applied because '{part}' "
                "is below a non-mapping value"
            )
        if part not in current:
            raise MetadataError(f"metadata path '{dotted_path}' not found")
        current = current[part]
    return current


def update_metadata_file(
    file_path: str | Path,
    section_id: str,
    dotted_path: str,
    json_value: str,
) -> dict[str, Any]:
    value = _parse_json_value(json_value)
    return _rewrite_metadata_file(
        file_path,
        section_id,
        lambda metadata: _set_dotted_value(metadata, dotted_path, value),
    )


def unset_metadata_file(
    file_path: str | Path,
    section_id: str,
    dotted_path: str,
) -> dict[str, Any]:
    return _rewrite_metadata_file(
        file_path,
        section_id,
        lambda metadata: _unset_dotted_value(metadata, dotted_path),
    )


def _rewrite_metadata_file(file_path: str | Path, section_id: str, mutator) -> dict[str, Any]:
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    block = _find_metadata_block(text, section_id)
    metadata = dict(block.metadata)
    mutator(metadata)

    dumped = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    if not dumped.endswith("\n"):
        dumped += "\n"

    lines = text.splitlines(keepends=True)
    content_start = block.fence_start_line + 1
    content_end = block.fence_end_line - 1
    new_lines = lines[:content_start] + dumped.splitlines(keepends=True) + lines[content_end:]
    path.write_text("".join(new_lines), encoding="utf-8")
    return metadata


def _find_metadata_block(text: str, section_id: str) -> MetadataBlock:
    md = MarkdownIt()
    tokens = md.parse(text)
    raws = _discover_sections(tokens)

    for raw in raws:
        inner_tokens = []
        for tok in tokens[raw.token_start + 3: raw.token_end + 1]:
            if tok.type == "heading_open":
                break
            inner_tokens.append(tok)

        for tok in inner_tokens:
            if tok.type != "fence" or tok.info.strip() != "yaml":
                continue
            metadata = _load_yaml_mapping(tok.content)
            if str(metadata.get("section", "")) != section_id:
                continue
            if not tok.map:
                raise MetadataError(f"metadata block for section '{section_id}' has no source range")
            return MetadataBlock(
                metadata=metadata,
                fence_start_line=tok.map[0],
                fence_end_line=tok.map[1],
            )

    raise MetadataError(f"section '{section_id}' not found")


def _load_yaml_mapping(content: str) -> dict[str, Any]:
    try:
        metadata = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:
        raise ParseError(f"invalid YAML metadata block: {exc}") from exc
    if not isinstance(metadata, dict):
        raise MetadataError("metadata block is not a YAML mapping")
    return metadata


def _parse_json_value(json_value: str) -> Any:
    try:
        return json.loads(json_value)
    except json.JSONDecodeError as exc:
        raise MetadataError(f"invalid JSON value: {exc.msg}") from exc


def _split_dotted_path(dotted_path: str) -> list[str]:
    parts = dotted_path.split(".")
    if not dotted_path or any(part == "" for part in parts):
        raise MetadataError("metadata path must use non-empty dotted segments")
    if parts[0] == "section":
        raise MetadataError("metadata path 'section' is read-only")
    return parts


def _set_dotted_value(metadata: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = _split_dotted_path(dotted_path)
    current = metadata

    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        if not isinstance(current[part], dict):
            raise MetadataError(
                f"metadata path '{dotted_path}' cannot be applied because "
                f"'{part}' is not a mapping"
            )
        current = current[part]

    current[parts[-1]] = value


def _unset_dotted_value(metadata: dict[str, Any], dotted_path: str) -> None:
    parts = _split_dotted_path(dotted_path)
    current = metadata

    for part in parts[:-1]:
        if part not in current:
            raise MetadataError(f"metadata path '{dotted_path}' not found")
        if not isinstance(current[part], dict):
            raise MetadataError(
                f"metadata path '{dotted_path}' cannot be applied because "
                f"'{part}' is not a mapping"
            )
        current = current[part]

    leaf = parts[-1]
    if leaf not in current:
        raise MetadataError(f"metadata path '{dotted_path}' not found")
    del current[leaf]

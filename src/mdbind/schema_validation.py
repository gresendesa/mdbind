from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SchemaValidationError(Exception):
    def __init__(
        self,
        detail: str,
        *,
        path: str = "",
        error_type: str = "schema_validation_error",
    ) -> None:
        super().__init__(detail)
        self.path = path
        self.error_type = error_type


def validate_section_schemas(graph) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []

    for uri, section in sorted(graph.index.sections.items()):
        schema_ref = section.metadata.get("schema")
        if not schema_ref:
            continue
        if not isinstance(schema_ref, str):
            errors.append(_error(
                uri=uri,
                schema=schema_ref,
                schema_path="schema",
                path="schema",
                detail="schema reference must be a string",
            ))
            continue
        if _is_web_uri(schema_ref):
            errors.append(_error(
                uri=uri,
                schema=schema_ref,
                schema_path=schema_ref,
                path="schema",
                detail="web URI schemas are not supported in this sprint",
                error_type="schema_unsupported_uri",
            ))
            continue

        schema_base = Path(section.file_path).resolve().parent
        schema_path = _resolve_schema_path(schema_base, schema_ref)
        try:
            schema = _load_schema(schema_path)
            _validate_with_jsonschema(section.metadata, schema)
        except SchemaValidationError as exc:
            errors.append(_error(
                uri=uri,
                schema=schema_ref,
                schema_path=str(schema_path),
                path=exc.path,
                detail=str(exc),
                error_type=exc.error_type,
            ))

    return errors


def _error(
    *,
    uri: str,
    schema: Any,
    schema_path: str,
    path: str,
    detail: str,
    error_type: str = "schema_validation_error",
) -> dict[str, Any]:
    return {
        "type": error_type,
        "uri": uri,
        "detail": detail,
        "schema": schema,
        "schema_path": schema_path,
        "path": path,
    }


def _is_web_uri(schema_ref: str) -> bool:
    return schema_ref.startswith(("http://", "https://"))


def _resolve_schema_path(repo_root: Path, schema_ref: str) -> Path:
    path = Path(schema_ref)
    if path.is_absolute():
        return path
    return repo_root / path


def _load_schema(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SchemaValidationError(
            f"schema file not found: {path}",
            path="schema",
            error_type="schema_not_found",
        )

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as err:
        raise SchemaValidationError(
            f"invalid schema document: {err}",
            path="schema",
            error_type="schema_invalid",
        )

    if not isinstance(data, dict):
        raise SchemaValidationError(
            "schema document must be a mapping",
            path="schema",
            error_type="schema_invalid",
        )
    return data


def _validate_with_jsonschema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator, SchemaError

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as err:
            raise SchemaValidationError(
                f"invalid schema document: {err.message}",
                path=_json_path(list(err.path)),
                error_type="schema_invalid",
            )

        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
        if errors:
            err = errors[0]
            raise SchemaValidationError(err.message, path=_json_path(list(err.path)))
    except ModuleNotFoundError:
        _validate_with_fallback(instance, schema)


def _validate_with_fallback(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    _validate_schema_document_fallback(schema)
    _validate_value(instance, schema, [])


def _validate_schema_document_fallback(schema: dict[str, Any]) -> None:
    allowed = {
        "$schema",
        "type",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "enum",
        "const",
    }
    unsupported = sorted(set(schema) - allowed)
    if unsupported:
        raise SchemaValidationError(
            "invalid schema document: unsupported keywords without jsonschema: "
            + ", ".join(unsupported),
            error_type="schema_invalid",
        )


def _validate_value(value: Any, schema: dict[str, Any], path: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        _raise_validation(path, f"{_json_path(path) or 'value'} must be {expected_type}")

    if "const" in schema and value != schema["const"]:
        _raise_validation(path, f"{_json_path(path) or 'value'} must equal {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        _raise_validation(path, f"{_json_path(path) or 'value'} must be one of {schema['enum']!r}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        if not isinstance(required, list):
            _raise_schema_invalid(path, "required must be a list")
        for key in required:
            if key not in value:
                _raise_validation(path + [str(key)], f"required property '{key}' is missing")

        properties = schema.get("properties", {})
        if properties is not None and not isinstance(properties, dict):
            _raise_schema_invalid(path, "properties must be a mapping")
        for key, subschema in properties.items():
            if key in value:
                if not isinstance(subschema, dict):
                    _raise_schema_invalid(path + [str(key)], "property schema must be a mapping")
                _validate_value(value[key], subschema, path + [str(key)])

        additional = schema.get("additionalProperties", True)
        if additional is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                _raise_validation(path + [extra[0]], f"additional property '{extra[0]}' is not allowed")

    if isinstance(value, list) and "items" in schema:
        items = schema["items"]
        if not isinstance(items, dict):
            _raise_schema_invalid(path, "items must be a mapping")
        for idx, item in enumerate(value):
            _validate_value(item, items, path + [str(idx)])


def _matches_type(value: Any, expected_type: str | list[str]) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(value, typ) for typ in expected_type)
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "boolean": bool,
        "integer": int,
        "number": (int, float),
        "null": type(None),
    }
    py_type = mapping.get(expected_type)
    if py_type is None:
        return False
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, py_type)


def _raise_validation(path: list[str], detail: str) -> None:
    raise SchemaValidationError(detail, path=_json_path(path))


def _raise_schema_invalid(path: list[str], detail: str) -> None:
    raise SchemaValidationError(
        f"invalid schema document: {detail}",
        path=_json_path(path),
        error_type="schema_invalid",
    )


def _json_path(path: list[Any]) -> str:
    return ".".join(str(part) for part in path)

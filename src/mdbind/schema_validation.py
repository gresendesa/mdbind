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


def validate_section_schemas(
    graph,
    repo_root: Path | None = None,
    no_cache: bool = False,
) -> list[dict[str, Any]]:
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
            try:
                schema = _load_web_schema(schema_ref, repo_root, no_cache)
                _validate_with_jsonschema(section.metadata, schema)
            except SchemaValidationError as exc:
                errors.append(_error(
                    uri=uri,
                    schema=schema_ref,
                    schema_path=schema_ref,
                    path=exc.path,
                    detail=str(exc),
                    error_type=exc.error_type,
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


def _load_web_schema(schema_ref: str, repo_root: Path | None, no_cache: bool) -> dict[str, Any]:
    import urllib.request
    import urllib.error
    import hashlib

    cache_dir = None
    if repo_root:
        cache_dir = Path(repo_root) / ".mdb" / "cache" / "schemas"
    else:
        cache_dir = Path.cwd() / ".mdb" / "cache" / "schemas"

    uri_hash = hashlib.sha256(schema_ref.encode("utf-8")).hexdigest()
    cache_file = cache_dir / f"{uri_hash}.json"

    if not no_cache and cache_file.exists():
        try:
            return _load_schema(cache_file)
        except SchemaValidationError:
            pass

    try:
        req = urllib.request.Request(
            schema_ref,
            headers={"User-Agent": "MdBind-CLI/0.1.14"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            content_bytes = response.read()
    except urllib.error.URLError as err:
        raise SchemaValidationError(
            f"failed to fetch remote schema from '{schema_ref}': {err}",
            path="schema",
            error_type="schema_unreachable_uri",
        )
    except Exception as err:
        raise SchemaValidationError(
            f"failed to fetch remote schema from '{schema_ref}': {err}",
            path="schema",
            error_type="schema_unreachable_uri",
        )

    try:
        content_str = content_bytes.decode("utf-8")
        data = yaml.safe_load(content_str) or {}
    except Exception as err:
        raise SchemaValidationError(
            f"invalid schema document from web URI: {err}",
            path="schema",
            error_type="schema_invalid",
        )

    if not isinstance(data, dict):
        raise SchemaValidationError(
            "schema document from web URI must be a mapping",
            path="schema",
            error_type="schema_invalid",
        )

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(content_str, encoding="utf-8")
    except Exception:
        pass

    return data


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


def find_git_root(cwd: Path) -> Path | None:
    import subprocess
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True
        )
        return Path(res.stdout.strip()).resolve()
    except Exception:
        return None


def get_historical_file_content(git_root: Path, commit_ref: str, relative_path: str) -> str | None:
    import subprocess
    try:
        res = subprocess.run(
            ["git", "show", f"{commit_ref}:{relative_path}"],
            cwd=str(git_root),
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout
    except subprocess.CalledProcessError:
        return None


def load_workflows(repo_root: Path) -> list[dict[str, Any]]:
    config_path = repo_root / ".mdb" / "config.yaml"
    if not config_path.exists():
        return []
    try:
        import yaml
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return data.get("workflows") or []
    except Exception:
        return []


def validate_workflows(graph, repo_root: Path, commit_ref: str | None = None) -> list[dict[str, Any]]:
    import subprocess
    import tempfile
    import re
    from mdbind.parser import parse_file

    errors = []
    workflows = load_workflows(repo_root)
    if not workflows:
        return []

    # Compile workflow regexes
    compiled_workflows = []
    for wf in workflows:
        name = wf.get("name")
        pattern_str = wf.get("section_pattern")
        allowed_statuses = wf.get("allowed_statuses") or []
        allowed_transitions = wf.get("allowed_transitions") or []
        if not name or not pattern_str:
            continue
        try:
            pattern = re.compile(pattern_str)
            compiled_workflows.append({
                "name": name,
                "pattern": pattern,
                "allowed_statuses": allowed_statuses,
                "allowed_transitions": allowed_transitions
            })
        except Exception:
            pass

    if not compiled_workflows:
        return []

    # If commit_ref is provided, retrieve historical statuses
    historical_statuses = {}
    if commit_ref:
        git_root = find_git_root(repo_root)
        if git_root:
            files_to_check = set(section.file_path for section in graph.index.sections.values())
            for file_path_str in sorted(files_to_check):
                file_path = Path(file_path_str)
                try:
                    rel_path = file_path.relative_to(git_root).as_posix()
                except ValueError:
                    continue
                hist_content = get_historical_file_content(git_root, commit_ref, rel_path)
                if hist_content is not None:
                    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tmp:
                        tmp.write(hist_content)
                        tmp_path = Path(tmp.name)
                    try:
                        old_sections = parse_file(tmp_path)
                        for old_sec in old_sections:
                            old_sec_name = old_sec.metadata.get("id")
                            old_sec_status = old_sec.metadata.get("status")
                            if old_sec_name:
                                historical_statuses[old_sec_name] = old_sec_status
                    except Exception:
                        pass
                    finally:
                        try:
                            tmp_path.unlink()
                        except OSError:
                            pass

    # Validate each section
    for uri, section in sorted(graph.index.sections.items()):
        sec_name = section.metadata.get("id")
        if not sec_name:
            continue

        for wf in compiled_workflows:
            if wf["pattern"].match(sec_name):
                current_status = section.metadata.get("status")
                # 1. Allowed statuses check
                if current_status not in wf["allowed_statuses"]:
                    errors.append({
                        "type": "workflow_status_error",
                        "uri": uri,
                        "detail": f"Status '{current_status}' is not allowed for workflow '{wf['name']}'. Allowed: {wf['allowed_statuses']}",
                    })
                    continue

                # 2. Transition check
                if commit_ref and sec_name in historical_statuses:
                    old_status = historical_statuses[sec_name]
                    if old_status and old_status != current_status:
                        transition_allowed = False
                        for trans in wf["allowed_transitions"]:
                            if trans.get("from") == old_status:
                                to_list = trans.get("to") or []
                                if current_status in to_list:
                                    transition_allowed = True
                                    break
                        if not transition_allowed:
                            errors.append({
                                "type": "workflow_transition_error",
                                "uri": uri,
                                "detail": f"Status transition from '{old_status}' to '{current_status}' is not allowed for workflow '{wf['name']}'.",
                            })

    return errors

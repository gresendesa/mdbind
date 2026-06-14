"""Local zip template packages for mdb memory creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError
import yaml

from mdbind.templates import RenderedFile, TemplateRenderError, write_rendered_files
from typing import Optional

class TemplatePackageError(RuntimeError):
    """Raised when a local template package is invalid."""


class TemplatePackagePackError(RuntimeError):
    """Raised when a template package directory cannot be packed."""


@dataclass(frozen=True)
class TemplatePackageFile:
    """One template-to-target mapping from a package manifest."""

    template: str
    target: Path


@dataclass(frozen=True)
class TemplatePackageVariable:
    """One variable declared by a template package manifest."""

    name: str
    prompt: str
    default: Any = None
    required: bool = True


@dataclass(frozen=True)
class TemplatePackage:
    """Loaded template package metadata."""

    name: str
    version: str | None
    files: list[TemplatePackageFile]
    instructions: list[str]
    variables: list[TemplatePackageVariable]


@dataclass(frozen=True)
class TemplatePackageRenderResult:
    """Result produced by rendering a template package."""

    package: dict[str, Any]
    files: list[str]
    instructions: list[str]


@dataclass(frozen=True)
class TemplatePackageInitResult:
    """Result produced by initializing a project from a template package."""

    package: dict[str, Any]
    files: list[str]
    instructions: list[str]
    config_file: str
    memory_root: str
    secret_phrase: str = ""
    hooked_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PackedTemplatePackageResult:
    """Result produced by packing a local template package directory."""

    output: str
    manifest: dict[str, Any]
    signature: dict[str, Any]
    files: list[str]


SIGNATURE_FILE = "SIGNATURE.yaml"
MANIFEST_FILE = "manifest.yaml"
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def render_template_package(
    package_path: Path,
    target_root: Path,
    context: dict[str, Any],
    *,
    force: bool = False,
) -> TemplatePackageRenderResult:
    """Render a local zip package into a target project root."""
    package_path = package_path.resolve()
    target_root = target_root.resolve()
    with TemporaryDirectory() as tmp:
        extracted = Path(tmp)
        package = _extract_package(package_path, extracted)
        rendered = _render_package_files(extracted, package, context)
        _prevent_unapproved_overwrites(target_root, rendered, force=force)
        write_rendered_files(target_root, rendered)
        return TemplatePackageRenderResult(
            package={"name": package.name, "version": package.version},
            files=[file.path.as_posix() for file in rendered],
            instructions=package.instructions,
        )


def inspect_template_package(package_path: Path, *, verify_signature: bool = False) -> TemplatePackage:
    """Load template package metadata without rendering files."""
    package_path = package_path.resolve()
    with TemporaryDirectory() as tmp:
        extracted = Path(tmp)
        package = _extract_package(package_path, extracted)
        if verify_signature:
            _verify_checksum_signature(extracted)
        return package


WORDS = [
    "amber", "anchor", "apple", "beacon", "breeze", "cherry", "cloud", "clover",
    "crystal", "desert", "dolphin", "dragon", "eagle", "emerald", "forest", "fossil",
    "glacier", "harbor", "island", "jungle", "lagoon", "lantern", "marble", "meadow",
    "meteor", "mountain", "nebula", "oasis", "ocean", "orchid", "pebble", "planet",
    "river", "safari", "shadow", "shield", "silver", "summit", "temple", "valley",
    "volcano", "whisper", "winter", "wizard", "zenith", "bright", "silent", "golden",
    "ancient", "hidden", "cosmic", "solar", "lunar", "arctic",
    "stormy", "gentle", "swift", "brave", "honest", "stable", "loyal", "vibrant",
    "flight", "journey", "path", "bridge", "spirit", "mirror", "legend",
    "echo", "spark", "flame", "frost", "wind", "storm", "thunder",
    "lightning", "dream", "vision", "wisdom", "courage", "grace", "melody", "rhythm",
    "harmony", "peace", "haven", "sanctuary", "fortress", "castle", "tower",
    "sword", "crown", "key", "gate", "door", "window", "compass", "map"
]


def generate_secret_phrase(word_count: int = 5) -> str:
    """Generate a cryptographically secure phrase of exactly 5 words separated by spaces."""
    import secrets
    chosen = [secrets.choice(WORDS) for _ in range(word_count)]
    return " ".join(chosen)


def inject_session_hooks(
    target_root: Path,
    placement: str,
    secret_phrase: str,
    memory_root: str,
    custom_files: Optional[list[Path]] = None,
) -> list[str]:
    """
    Detects development environments and injects/updates MdBind rules hooks
    into entrypoint instruction files.
    """
    import os
    hooked_files = []

    if custom_files:
        to_hook = custom_files
    else:
        # Target files list
        targets = [
            target_root / "AGENTS.md",
            target_root / ".github" / "copilot-instructions.md"
        ]

        to_hook = []
        for t in targets:
            if t.exists():
                to_hook.append(t)

        if not to_hook:
            to_hook.append(target_root / "AGENTS.md")
            if (target_root / ".github").is_dir():
                to_hook.append(target_root / ".github" / "copilot-instructions.md")

    constitution_path = target_root / memory_root / "CONSTITUTION.md"

    for entrypoint in to_hook:
        try:
            rel_const = os.path.relpath(constitution_path, entrypoint.parent)
        except Exception:
            rel_const = f"{memory_root}/CONSTITUTION.md"

        hook_content = (
            f"<!-- mdbind-session-hook-start -->\n"
            f"# MdBind Session Hook\n"
            f"[@include: Constitution]({rel_const})\n\n"
            f"## Secret Verification Phrase\n"
            f"When you receive the phrase \"{secret_phrase}\", you must respond with a standard summary of the key points of the templates/modules in this repository.\n"
            f"<!-- mdbind-session-hook-end -->"
        )

        entrypoint.parent.mkdir(parents=True, exist_ok=True)

        if entrypoint.exists():
            content = entrypoint.read_text(encoding="utf-8")
            start_marker = "<!-- mdbind-session-hook-start -->"
            end_marker = "<!-- mdbind-session-hook-end -->"
            if start_marker in content and end_marker in content:
                start_idx = content.find(start_marker)
                end_idx = content.find(end_marker) + len(end_marker)
                new_content = content[:start_idx] + hook_content + content[end_idx:]
            else:
                if placement == "top":
                    new_content = hook_content + "\n\n" + content
                else:  # bottom
                    new_content = content.rstrip() + "\n\n" + hook_content + "\n"
        else:
            new_content = hook_content + "\n"

        entrypoint.write_text(new_content, encoding="utf-8")
        hooked_files.append(entrypoint.relative_to(target_root).as_posix())

    return hooked_files


def remove_session_hooks(target_root: Path, files: list[Path]) -> list[str]:
    """
    Strips the MdBind session rules hooks from target instruction files.
    Deletes the file if it is left empty or containing only whitespace.
    """
    removed_files = []
    start_marker = "<!-- mdbind-session-hook-start -->"
    end_marker = "<!-- mdbind-session-hook-end -->"

    for entrypoint in files:
        if not entrypoint.exists():
            continue

        content = entrypoint.read_text(encoding="utf-8")
        if start_marker in content and end_marker in content:
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker) + len(end_marker)

            before = content[:start_idx]
            after = content[end_idx:]

            new_content = before.rstrip() + "\n" + after.lstrip()
            cleaned_content = new_content.strip()

            if not cleaned_content:
                entrypoint.unlink(missing_ok=True)
            else:
                entrypoint.write_text(new_content, encoding="utf-8")

            removed_files.append(entrypoint.relative_to(target_root).as_posix())

    return removed_files


def init_from_template_package(
    package_path: Path,
    target_root: Path,
    context: dict[str, Any],
    *,
    force: bool = False,
    memory_root: str = "scrum",
    template_profile: str = "standard",
    hook_placement: str = "bottom",
    secret_phrase: Optional[str] = None,
) -> TemplatePackageInitResult:
    """Initialize project memory from a checksum-signed local template package."""
    package_path = package_path.resolve()
    target_root = target_root.resolve()
    _prevent_existing_memory(target_root, memory_root, force=force)

    if not secret_phrase:
        secret_phrase = generate_secret_phrase()

    hooked_files = []
    if hook_placement != "none":
        hooked_files = inject_session_hooks(
            target_root,
            placement=hook_placement,
            secret_phrase=secret_phrase,
            memory_root=memory_root,
        )

    with TemporaryDirectory() as tmp:
        extracted = Path(tmp)
        package = _extract_package(package_path, extracted)
        _verify_checksum_signature(extracted)
        full_context = dict(context)
        full_context.setdefault("memory_root", memory_root)
        full_context.setdefault("template_profile", template_profile)
        rendered = _render_package_files(extracted, package, full_context)
        _prevent_unapproved_overwrites(target_root, rendered, force=force)
        write_rendered_files(target_root, rendered)

        context_anchoring = {
            "secret_phrase": secret_phrase,
            "hooked_files": hooked_files,
        }

        config_file = _write_init_config(
            target_root,
            memory_root=memory_root,
            template_profile=template_profile,
            package=package,
            context=full_context,
            force=force,
            context_anchoring=context_anchoring,
        )

        return TemplatePackageInitResult(
            package={"name": package.name, "version": package.version},
            files=[file.path.as_posix() for file in rendered],
            instructions=package.instructions,
            config_file=config_file,
            memory_root=memory_root,
            secret_phrase=secret_phrase,
            hooked_files=hooked_files,
        )


def pack_template_package(
    source_dir: Path,
    output_path: Path,
    *,
    force: bool = False,
) -> PackedTemplatePackageResult:
    """Pack a local template directory into a deterministic checksum-signed zip."""
    source_dir = source_dir.resolve()
    output_path = output_path.resolve()
    manifest = _read_pack_manifest(source_dir)
    _validate_output_path(source_dir, output_path, force=force)

    source_files = _collect_source_files(source_dir)
    checksummed_files = [file for file in source_files if file.as_posix() != SIGNATURE_FILE]
    if not checksummed_files:
        raise TemplatePackagePackError("Template package directory does not contain packable files.")

    signature = _build_signature(source_dir, checksummed_files)
    zip_files = _build_zip_files(source_dir, source_files, signature)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_deterministic_zip(output_path, zip_files)

    return PackedTemplatePackageResult(
        output=output_path.as_posix(),
        manifest={
            "name": manifest["name"],
            "version": str(manifest["version"]),
            "template_engine": manifest["template_engine"],
        },
        signature={
            "file": SIGNATURE_FILE,
            "policy": signature["policy"],
            "algorithm": signature["algorithm"],
            "scope": signature["scope"],
            "files": len(signature["files"]),
        },
        files=[path for path, _content in zip_files],
    )


def _extract_package(package_path: Path, target: Path) -> TemplatePackage:
    if not package_path.exists():
        raise TemplatePackageError("Template package does not exist.")
    if package_path.suffix != ".zip":
        raise TemplatePackageError("Template package must be a .zip file.")

    try:
        with ZipFile(package_path) as archive:
            for member in archive.infolist():
                destination = (target / member.filename).resolve()
                if not _is_relative_to(destination, target):
                    raise TemplatePackageError("Template package contains an unsafe path.")
            archive.extractall(target)
    except BadZipFile as exc:
        raise TemplatePackageError("Template package is not a valid zip archive.") from exc

    return _read_manifest(target)


def _read_pack_manifest(root: Path) -> dict[str, Any]:
    if not root.exists():
        raise TemplatePackagePackError("Template package directory does not exist.")
    if not root.is_dir():
        raise TemplatePackagePackError("Template package source must be a directory.")

    manifest_path = root / MANIFEST_FILE
    if not manifest_path.exists():
        raise TemplatePackagePackError("Template package directory must include manifest.yaml.")

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise TemplatePackagePackError("manifest.yaml must contain a YAML mapping.")

    # Validate essential manifest keys
    for field in ("name", "version", "description", "author", "template_engine", "files", "instructions"):
        if field not in data:
            raise TemplatePackagePackError(f"manifest.yaml is missing required field '{field}'.")

    # Allow both smd_version and mdb_version (or similar) to exist
    if "smd_version" not in data and "mdb_version" not in data:
        raise TemplatePackagePackError("manifest.yaml is missing required version check field 'mdb_version' or 'smd_version'.")

    for field in ("name", "version", "description", "author", "template_engine"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise TemplatePackagePackError(f"manifest.yaml field '{field}' must be a non-empty string.")
    if data["template_engine"] != "jinja2":
        raise TemplatePackagePackError("manifest.yaml field 'template_engine' must be 'jinja2'.")

    _validate_manifest_paths(root, data, "files", required_keys=("template", "target"))
    _validate_manifest_paths(root, data, "instructions")
    _read_manifest_variables(data)
    return data


def _validate_manifest_paths(
    root: Path,
    data: dict[str, Any],
    field: str,
    *,
    required_keys: tuple[str, ...] = (),
) -> None:
    value = data[field]
    if not isinstance(value, list) or not value:
        raise TemplatePackagePackError(f"manifest.yaml field '{field}' must be a non-empty list.")

    for item in value:
        if required_keys:
            if not isinstance(item, dict):
                raise TemplatePackagePackError(f"manifest.yaml field '{field}' entries must be mappings.")
            for key in required_keys:
                path = item.get(key)
                if not isinstance(path, str):
                    raise TemplatePackagePackError(f"manifest.yaml field '{field}' entries require '{key}'.")
                _assert_safe_relative(path, f"Manifest {field}.{key}")
                if key != "target" and not (root / path).exists():
                    raise TemplatePackagePackError(f"Manifest path '{path}' does not exist.")
        else:
            if not isinstance(item, str):
                raise TemplatePackagePackError(f"manifest.yaml field '{field}' entries must be strings.")
            _assert_safe_relative(item, f"Manifest {field}")
            if not (root / item).exists():
                raise TemplatePackagePackError(f"Manifest path '{item}' does not exist.")


def _validate_output_path(source_dir: Path, output_path: Path, *, force: bool) -> None:
    if output_path.suffix != ".zip":
        raise TemplatePackagePackError("Output path must end with .zip.")
    if _is_relative_to(output_path, source_dir):
        raise TemplatePackagePackError("Output zip must not be written inside the source directory.")
    if output_path.exists() and not force:
        raise TemplatePackagePackError("Refusing to overwrite existing output without --force.")
    if output_path.exists() and output_path.is_dir():
        raise TemplatePackagePackError("Output path must be a file, not a directory.")


def _collect_source_files(source_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(source_dir.rglob("*")):
        if path.is_symlink():
            raise TemplatePackagePackError("Template package directory must not contain symlinks.")
        if path.is_file():
            files.append(path.relative_to(source_dir))
    if Path(MANIFEST_FILE) not in files:
        raise TemplatePackagePackError("Template package directory must include manifest.yaml.")
    return files


def _build_signature(source_dir: Path, files: list[Path]) -> dict[str, Any]:
    signed_files = []
    for relative_path in sorted(files, key=lambda path: path.as_posix()):
        content = (source_dir / relative_path).read_bytes()
        signed_files.append(
            {
                "path": relative_path.as_posix(),
                "sha256": sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    payload = "\n".join(f"{item['path']} {item['sha256']}" for item in signed_files).encode("utf-8")
    return {
        "version": "1",
        "policy": "checksum-only",
        "algorithm": "sha256",
        "scope": "file_contents_relative_paths_deterministic_order",
        "files": signed_files,
        "digest": sha256(payload).hexdigest(),
    }


def _build_zip_files(source_dir: Path, files: list[Path], signature: dict[str, Any]) -> list[tuple[str, bytes]]:
    output: list[tuple[str, bytes]] = []
    for relative_path in sorted(files, key=lambda path: path.as_posix()):
        if relative_path.as_posix() == SIGNATURE_FILE:
            continue
        output.append((relative_path.as_posix(), (source_dir / relative_path).read_bytes()))

    signature_content = yaml.safe_dump(signature, sort_keys=False, allow_unicode=False).encode("utf-8")
    output.append((SIGNATURE_FILE, signature_content))
    return sorted(output, key=lambda item: item[0])


def _write_deterministic_zip(output_path: Path, files: list[tuple[str, bytes]]) -> None:
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for relative_path, content in files:
            info = ZipInfo(relative_path, ZIP_EPOCH)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)


def _read_manifest(root: Path) -> TemplatePackage:
    manifest_path = root / MANIFEST_FILE
    if not manifest_path.exists():
        manifest_path = root / "template.yml"
    if not manifest_path.exists():
        manifest_path = root / "template.yaml"
    if not manifest_path.exists():
        raise TemplatePackageError("Template package must include manifest.yaml.")

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise TemplatePackageError("Template manifest must contain a YAML mapping.")

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise TemplatePackageError("Template manifest must define a non-empty name.")

    raw_files = data.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise TemplatePackageError("Template manifest must define at least one file mapping.")

    files: list[TemplatePackageFile] = []
    for raw_file in raw_files:
        if not isinstance(raw_file, dict):
            raise TemplatePackageError("Template file mappings must be YAML mappings.")
        template = raw_file.get("template")
        target = raw_file.get("target")
        if not isinstance(template, str) or not isinstance(target, str):
            raise TemplatePackageError("Template file mappings require template and target.")
        _assert_safe_relative(template, "Template path")
        _assert_safe_relative(target, "Target path")
        if not (root / template).exists():
            raise TemplatePackageError(f"Template file '{template}' does not exist in the package.")
        files.append(TemplatePackageFile(template=template, target=Path(target)))

    instructions = data.get("instructions", [])
    if not isinstance(instructions, list) or not instructions:
        raise TemplatePackageError("Template manifest must list at least one LLM instruction file.")
    for instruction in instructions:
        if not isinstance(instruction, str):
            raise TemplatePackageError("Instruction file paths must be strings.")
        _assert_safe_relative(instruction, "Instruction path")
        if not (root / instruction).exists():
            raise TemplatePackageError(f"Instruction file '{instruction}' does not exist in the package.")

    version = data.get("version")
    if version is not None:
        version = str(version)

    variables = _read_manifest_variables(data)

    return TemplatePackage(name=name, version=version, files=files, instructions=instructions, variables=variables)


def _read_manifest_variables(data: dict[str, Any]) -> list[TemplatePackageVariable]:
    raw_variables = data.get("variables", [])
    if raw_variables is None:
        return []
    if not isinstance(raw_variables, list):
        raise TemplatePackageError("Template manifest field 'variables' must be a list.")

    variables: list[TemplatePackageVariable] = []
    seen: set[str] = set()
    for raw_variable in raw_variables:
        if not isinstance(raw_variable, dict):
            raise TemplatePackageError("Template manifest variable entries must be mappings.")
        name = raw_variable.get("name")
        if not isinstance(name, str) or not name.strip():
            raise TemplatePackageError("Template manifest variables require a non-empty name.")
        if name in seen:
            raise TemplatePackageError(f"Template manifest variable '{name}' is duplicated.")
        if not name.replace("_", "").isalnum() or name[0].isdigit():
            raise TemplatePackageError(f"Template manifest variable '{name}' must be a simple identifier.")
        prompt = raw_variable.get("prompt", name.replace("_", " ").title())
        if not isinstance(prompt, str) or not prompt.strip():
            raise TemplatePackageError(f"Template manifest variable '{name}' prompt must be a non-empty string.")
        required = raw_variable.get("required", True)
        if not isinstance(required, bool):
            raise TemplatePackageError(f"Template manifest variable '{name}' required must be true or false.")
        variables.append(
            TemplatePackageVariable(
                name=name,
                prompt=prompt,
                default=raw_variable.get("default"),
                required=required,
            )
        )
        seen.add(name)
    return variables


def _render_package_files(root: Path, package: TemplatePackage, context: dict[str, Any]) -> list[RenderedFile]:
    from datetime import date
    
    today = date.today().isoformat()
    full_context = dict(context)
    full_context.setdefault("created_at", today)
    full_context.setdefault("updated_at", today)
    full_context.setdefault("timezone", "America/Sao_Paulo")
    full_context.setdefault("nnr", [
        "The official project memory lives under the memory root.",
        "Memory files must use stable section metadata and references.",
    ])
    full_context.setdefault("strategic_priority", [
        "Deliver a small, real MVP first.",
        "Favor deterministic file operations.",
    ])
    full_context.setdefault("memory_policy", [
        "Consolidators keep concise summaries only.",
        "Historical records must be marked obsolete instead of deleted.",
    ])

    environment = Environment(
        loader=FileSystemLoader(root),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    rendered: list[RenderedFile] = []
    for file in package.files:
        try:
            content = environment.get_template(file.template).render(**full_context)
        except TemplateError as exc:
            raise TemplateRenderError(f"failed to render template '{file.template}': {exc}") from exc
        rendered.append(RenderedFile(file.target, content))
    return rendered



def _prevent_unapproved_overwrites(target_root: Path, files: list[RenderedFile], *, force: bool) -> None:
    if force:
        return
    conflicting: list[str] = []
    for rendered in files:
        path = target_root / rendered.path
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            content = rendered.content
            if content and not content.endswith("\n"):
                content += "\n"
            if existing != content:
                conflicting.append(rendered.path.as_posix())
    if conflicting:
        joined = ", ".join(conflicting)
        raise TemplatePackageError(f"Refusing to overwrite existing files without --force: {joined}.")


def _prevent_existing_memory(target_root: Path, memory_root: str, *, force: bool) -> None:
    if force:
        return
    existing = []
    memory_path = target_root / memory_root
    config_path = target_root / ".mdb" / "config.yaml"
    if memory_path.exists():
        existing.append(memory_path.relative_to(target_root).as_posix())
    if config_path.exists():
        existing.append(config_path.relative_to(target_root).as_posix())
    if existing:
        raise TemplatePackageError(f"Refusing to initialize over existing memory without --force: {', '.join(existing)}.")


def _write_init_config(
    target_root: Path,
    *,
    memory_root: str,
    template_profile: str,
    package: TemplatePackage,
    context: dict[str, Any],
    force: bool,
    context_anchoring: dict[str, Any] | None = None,
) -> str:
    config_path = target_root / ".mdb" / "config.yaml"
    if config_path.exists() and not force:
        raise TemplatePackageError("Refusing to overwrite .mdb/config.yaml without --force.")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "memory_root": memory_root,
        "templates": {
            "profile": template_profile,
            "package": package.name,
            "version": package.version,
        },
        "project": {
            "name": context.get("project_name"),
            "owner": context.get("owner"),
            "language": context.get("language"),
            "timezone": context.get("timezone"),
        },
    }
    if context_anchoring:
        config["context_anchoring"] = context_anchoring
    config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return config_path.relative_to(target_root).as_posix()


def _verify_checksum_signature(root: Path) -> None:
    signature_path = root / SIGNATURE_FILE
    if not signature_path.exists():
        raise TemplatePackageError("Template package must include SIGNATURE.yaml.")

    signature = yaml.safe_load(signature_path.read_text(encoding="utf-8")) or {}
    if not isinstance(signature, dict):
        raise TemplatePackageError("SIGNATURE.yaml must contain a YAML mapping.")
    if signature.get("policy") != "checksum-only":
        raise TemplatePackageError("SIGNATURE.yaml policy must be 'checksum-only'.")
    if signature.get("algorithm") != "sha256":
        raise TemplatePackageError("SIGNATURE.yaml algorithm must be 'sha256'.")
    if signature.get("scope") != "file_contents_relative_paths_deterministic_order":
        raise TemplatePackageError("SIGNATURE.yaml scope is not supported.")

    raw_files = signature.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise TemplatePackageError("SIGNATURE.yaml must list signed files.")

    signed_paths: set[str] = set()
    normalized_files: list[dict[str, Any]] = []
    for item in raw_files:
        if not isinstance(item, dict):
            raise TemplatePackageError("SIGNATURE.yaml file entries must be mappings.")
        path = item.get("path")
        digest = item.get("sha256")
        size = item.get("size")
        if not isinstance(path, str) or not isinstance(digest, str) or not isinstance(size, int):
            raise TemplatePackageError("SIGNATURE.yaml file entries require path, sha256, and size.")
        _assert_safe_relative(path, "Signature path")
        if path == SIGNATURE_FILE:
            raise TemplatePackageError("SIGNATURE.yaml must not sign itself.")
        file_path = root / path
        if not file_path.exists() or not file_path.is_file():
            raise TemplatePackageError(f"Signed file '{path}' does not exist in the package.")
        content = file_path.read_bytes()
        if len(content) != size or sha256(content).hexdigest() != digest:
            raise TemplatePackageError(f"Checksum verification failed for '{path}'.")
        signed_paths.add(path)
        normalized_files.append({"path": path, "sha256": digest})

    package_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.relative_to(root).as_posix() != SIGNATURE_FILE
    }
    unsigned = sorted(package_files - signed_paths)
    if unsigned:
        raise TemplatePackageError(f"Template package contains unsigned files: {', '.join(unsigned)}.")
    missing = sorted(signed_paths - package_files)
    if missing:
        raise TemplatePackageError(f"SIGNATURE.yaml references missing files: {', '.join(missing)}.")
    if MANIFEST_FILE not in signed_paths:
        raise TemplatePackageError("SIGNATURE.yaml must sign manifest.yaml.")

    expected_payload = "\n".join(
        f"{item['path']} {item['sha256']}" for item in sorted(normalized_files, key=lambda value: value["path"])
    ).encode("utf-8")
    expected_digest = sha256(expected_payload).hexdigest()
    if signature.get("digest") != expected_digest:
        raise TemplatePackageError("SIGNATURE.yaml digest verification failed.")


def _assert_safe_relative(path: str, label: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise TemplatePackageError(f"{label} must be a safe relative path.")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def compute_next_id(sections, prefix: str, pattern: str) -> str:
    """
    Computes the next sequential ID by scanning the section URIs and metadata values.
    """
    import re
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}")

    values: list[tuple[int, str]] = []
    
    for section in sections:
        # Search URI
        for match in regex.finditer(section.uri):
            try:
                val = int(match.group(1))
                values.append((val, match.group(1)))
            except (IndexError, ValueError):
                pass
        # Search metadata
        metadata_str = str(section.metadata)
        for match in regex.finditer(metadata_str):
            try:
                val = int(match.group(1))
                values.append((val, match.group(1)))
            except (IndexError, ValueError):
                pass

    if not values:
        # Detect width from pattern
        match_w = re.search(r"\\d\{(\d+)(?:,\d+)?\}", pattern)
        if match_w:
            width = int(match_w.group(1))
        else:
            match_d = re.findall(r"\\d", pattern)
            width = len(match_d) if match_d else 3
        next_number = 1
    else:
        # Find maximum value
        max_val, max_str = max(values, key=lambda x: x[0])
        width = len(max_str)
        next_number = max_val + 1

    # Format output
    if prefix.endswith("-") or prefix.endswith("_") or prefix.endswith("/"):
        return f"{prefix}{next_number:0{width}d}"
    else:
        return f"{prefix}-{next_number:0{width}d}"


def resolve_template_package_path(
    package_path_or_url: str,
    *,
    checksum: str | None = None,
    no_cache: bool = False,
    repo_root: Path | None = None,
) -> Path:
    """Resolve a template package path from a local file or a remote URL (with checksum verification)."""
    import urllib.request
    import urllib.error
    import hashlib

    # Helper to calculate sha256
    def _sha256_of_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _sha256_of_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    # Clean expected checksum
    expected_hash = None
    if checksum:
        expected_hash = checksum.strip()
        if expected_hash.lower().startswith("sha256:"):
            expected_hash = expected_hash[7:]
        expected_hash = expected_hash.lower()

    is_url = package_path_or_url.startswith(("http://", "https://"))

    if is_url:
        if not expected_hash:
            raise TemplatePackageError("A checksum is required for remote template packages. Please specify --checksum <hash>.")

        # Cache location
        cache_dir = None
        if repo_root:
            cache_dir = Path(repo_root) / ".mdb" / "cache" / "templates"
        else:
            cache_dir = Path.cwd() / ".mdb" / "cache" / "templates"

        url_hash = hashlib.sha256(package_path_or_url.encode("utf-8")).hexdigest()
        cache_file = cache_dir / f"{url_hash}.zip"

        # Check cache
        if not no_cache and cache_file.exists():
            try:
                cached_hash = _sha256_of_file(cache_file)
                if cached_hash == expected_hash:
                    return cache_file
            except Exception:
                pass

        # Download remote package
        try:
            req = urllib.request.Request(
                package_path_or_url,
                headers={"User-Agent": "MdBind-CLI/0.1.13"},
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                content_bytes = response.read()
        except urllib.error.URLError as err:
            raise TemplatePackageError(f"Failed to download remote template package: {err}")
        except Exception as err:
            raise TemplatePackageError(f"Failed to download remote template package: {err}")

        # Check checksum
        downloaded_hash = _sha256_of_bytes(content_bytes)
        if downloaded_hash != expected_hash:
            raise TemplatePackageError(
                f"Checksum verification failed for remote template package.\n"
                f"Expected: {expected_hash}\n"
                f"Got:      {downloaded_hash}"
            )

        # Save to cache
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(content_bytes)
        except Exception:
            pass

        return cache_file

    else:
        local_path = Path(package_path_or_url)
        if not local_path.exists():
            raise TemplatePackageError(f"Template package path does not exist: {local_path}")
        if not local_path.is_file():
            raise TemplatePackageError(f"Template package path is not a file: {local_path}")

        # If checksum provided, verify it
        if expected_hash:
            try:
                local_hash = _sha256_of_file(local_path)
            except Exception as err:
                raise TemplatePackageError(f"Failed to compute checksum of local template package: {err}")
            if local_hash != expected_hash:
                raise TemplatePackageError(
                    f"Checksum verification failed for local template package.\n"
                    f"Expected: {expected_hash}\n"
                    f"Got:      {local_hash}"
                )

        return local_path

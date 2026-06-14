import json
import zipfile
import pytest
from pathlib import Path
from typer.testing import CliRunner
import yaml

from mdbind.cli import app
from mdbind.template_packages import (
    pack_template_package,
    init_from_template_package,
    inspect_template_package,
    TemplatePackageError,
    TemplatePackagePackError,
)

runner = CliRunner()

@pytest.fixture
def temp_workspace(tmp_path: Path):
    # Setup a mock template source directory
    src_dir = tmp_path / "template_src"
    src_dir.mkdir()
    
    manifest = {
        "name": "test-template",
        "version": "1.2.3",
        "description": "A test template package",
        "author": "Tester",
        "template_engine": "jinja2",
        "mdb_version": "0.1.0",
        "instructions": ["scrum/instructions/LLM.md"],
        "variables": [
            {"name": "project_name", "prompt": "Proj Name", "default": "hello-world", "required": True},
            {"name": "owner", "prompt": "Owner Name", "required": True},
        ],
        "files": [
            {"template": "scrum/CONSTITUTION.md.j2", "target": "scrum/CONSTITUTION.md"},
            {"template": "scrum/instructions/LLM.md", "target": "scrum/instructions/LLM.md"},
        ]
    }
    
    (src_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    
    scrum_dir = src_dir / "scrum"
    scrum_dir.mkdir()
    (scrum_dir / "CONSTITUTION.md.j2").write_text(
        "Project: {{ project_name }}\nOwner: {{ owner }}\nMemory root: {{ memory_root }}\n", 
        encoding="utf-8"
    )
    
    inst_dir = scrum_dir / "instructions"
    inst_dir.mkdir()
    (inst_dir / "LLM.md").write_text("Instructions for {{ project_name }}", encoding="utf-8")
    
    return src_dir

def test_pack_success(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    
    # Pack via function
    result = pack_template_package(temp_workspace, output_zip)
    assert result.output == output_zip.as_posix()
    assert result.manifest["name"] == "test-template"
    assert result.signature["policy"] == "checksum-only"
    
    assert output_zip.exists()
    
    # Check that zip is deterministic by packing again
    output_zip2 = tmp_path / "package2.zip"
    pack_template_package(temp_workspace, output_zip2)
    
    # Check byte-for-byte identity
    assert output_zip.read_bytes() == output_zip2.read_bytes()

def test_pack_cli_success(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "cli_package.zip"
    
    result = runner.invoke(app, ["pack", temp_workspace.as_posix(), "-o", output_zip.as_posix()])
    assert result.exit_code == 0
    assert "Successfully packed" in result.stdout
    assert output_zip.exists()

def test_pack_missing_manifest(tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    output_zip = tmp_path / "empty.zip"
    
    with pytest.raises(TemplatePackagePackError, match="must include manifest.yaml"):
        pack_template_package(empty_dir, output_zip)

def test_init_success(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    target_root = tmp_path / "target_proj"
    target_root.mkdir()
    
    context = {"project_name": "MyAwesomeProject", "owner": "Alice"}
    result = init_from_template_package(output_zip, target_root, context)
    
    assert result.package["name"] == "test-template"
    assert result.config_file == ".mdb/config.yaml"
    
    # Check rendered files
    const_file = target_root / "scrum" / "CONSTITUTION.md"
    assert const_file.exists()
    content = const_file.read_text(encoding="utf-8")
    assert "Project: MyAwesomeProject" in content
    assert "Owner: Alice" in content
    assert "Memory root: scrum" in content
    
    inst_file = target_root / "scrum" / "instructions" / "LLM.md"
    assert inst_file.exists()
    assert inst_file.read_text(encoding="utf-8") == "Instructions for MyAwesomeProject\n"
    
    # Check config file contents
    config_file = target_root / ".mdb" / "config.yaml"
    assert config_file.exists()
    config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert config_data["memory_root"] == "scrum"
    assert config_data["project"]["name"] == "MyAwesomeProject"
    assert config_data["project"]["owner"] == "Alice"

def test_init_cli_success_with_var(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    target_root = tmp_path / "target_proj_cli"
    target_root.mkdir()
    
    # Use CLI with --var options
    result = runner.invoke(app, [
        "init",
        "-t", output_zip.as_posix(),
        "-r", target_root.as_posix(),
        "--var", "project_name=CliProject",
        "--var", "owner=Bob",
    ])
    
    assert result.exit_code == 0
    assert "Successfully initialized workspace template" in result.stdout
    
    const_file = target_root / "scrum" / "CONSTITUTION.md"
    assert const_file.exists()
    content = const_file.read_text(encoding="utf-8")
    assert "Project: CliProject" in content
    assert "Owner: Bob" in content

def test_init_cli_success_with_context_file(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    target_root = tmp_path / "target_proj_context"
    target_root.mkdir()
    
    context_file = tmp_path / "ctx.yaml"
    ctx_data = {"project_name": "YamlProject", "owner": "Charlie"}
    context_file.write_text(yaml.safe_dump(ctx_data), encoding="utf-8")
    
    result = runner.invoke(app, [
        "init",
        "-t", output_zip.as_posix(),
        "-r", target_root.as_posix(),
        "--context", context_file.as_posix(),
    ])
    
    assert result.exit_code == 0
    
    const_file = target_root / "scrum" / "CONSTITUTION.md"
    assert const_file.exists()
    content = const_file.read_text(encoding="utf-8")
    assert "Project: YamlProject" in content
    assert "Owner: Charlie" in content

def test_init_fails_if_already_initialized(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    target_root = tmp_path / "target_proj"
    target_root.mkdir()
    
    # 1st init
    context = {"project_name": "P1", "owner": "Alice"}
    init_from_template_package(output_zip, target_root, context)
    
    # 2nd init should fail
    with pytest.raises(TemplatePackageError, match="Refusing to initialize over existing memory"):
        init_from_template_package(output_zip, target_root, context)
        
    # With --force it should succeed
    init_from_template_package(output_zip, target_root, context, force=True)

def test_init_fails_signature_verification_tampered_file(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    # Tamper with the zip file content
    tampered_zip = tmp_path / "tampered.zip"
    with zipfile.ZipFile(output_zip, "r") as r_zip:
        with zipfile.ZipFile(tampered_zip, "w") as w_zip:
            for item in r_zip.infolist():
                data = r_zip.read(item.filename)
                if item.filename == "scrum/CONSTITUTION.md.j2":
                    data = data + b"\n# Tampered text!"
                w_zip.writestr(item, data)
                
    target_root = tmp_path / "target_tampered"
    target_root.mkdir()
    
    context = {"project_name": "P1", "owner": "Alice"}
    with pytest.raises(TemplatePackageError, match="Checksum verification failed"):
        init_from_template_package(tampered_zip, target_root, context)

def test_init_fails_path_traversal(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    # Create a zip containing path traversal
    traversal_zip = tmp_path / "traversal.zip"
    with zipfile.ZipFile(output_zip, "r") as r_zip:
        with zipfile.ZipFile(traversal_zip, "w") as w_zip:
            for item in r_zip.infolist():
                w_zip.writestr(item, r_zip.read(item.filename))
            w_zip.writestr("../../evil.txt", b"evil")
            
    target_root = tmp_path / "target_traversal"
    target_root.mkdir()
    
    context = {"project_name": "P1", "owner": "Alice"}
    with pytest.raises(TemplatePackageError, match="Template package contains an unsafe path"):
        init_from_template_package(traversal_zip, target_root, context)


def test_init_real_templates(tmp_path: Path):
    templates_dir = Path(__file__).parent.parent / "templates"
    for name, expected_file, const_file in [
        ("kanban", "kanban/BOARD.md", "kanban/CONSTITUTION.md"),
        ("product", "product/PITCHES.md", "product/CONSTITUTION.md"),
        ("engineering", "engineering/ADR.md", "engineering/CONSTITUTION.md"),
        ("minimal", "minimal/README.md", "minimal/CONSTITUTION.md"),
    ]:
        template_src = templates_dir / name
        assert template_src.exists(), f"Template {name} does not exist at {template_src}"
        
        output_zip = tmp_path / f"{name}.zip"
        pack_template_package(template_src, output_zip)
        assert output_zip.exists()
        
        target_root = tmp_path / f"target_{name}"
        target_root.mkdir()
        
        context = {
            "project_name": f"Test {name}",
            "owner": "Test Owner",
        }
        
        # Test dynamic resolution of memory_root from manifest.yaml (memory_root is not passed)
        result = init_from_template_package(
            output_zip,
            target_root,
            context,
            template_profile="standard",
            hook_placement="none"
        )
        
        assert result.package["name"] == f"smd-{name}"
        assert result.memory_root == name
        
        expected_path = target_root / expected_file
        assert expected_path.exists()
        
        const_path = target_root / const_file
        assert const_path.exists()
        
        content = expected_path.read_text(encoding="utf-8")
        assert f"Test {name}" in content

        # Verify config.yaml
        config_path = target_root / ".mdb" / "config.yaml"
        assert config_path.exists()
        import yaml
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert config["memory_root"] == name


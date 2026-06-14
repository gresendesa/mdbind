import pytest
from pathlib import Path
from typer.testing import CliRunner
import yaml

from mdbind.cli import app
from mdbind.template_packages import (
    pack_template_package,
    init_from_template_package,
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


def test_init_session_hook_default(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    target_root = tmp_path / "target_proj_hooks"
    target_root.mkdir()
    
    # We pre-create AGENTS.md with some pre-existing content
    agents_file = target_root / "AGENTS.md"
    agents_file.write_text("Pre-existing agent info\nLine 2\n", encoding="utf-8")
    
    # Run init using CLI with non-interactive --hook-placement bottom
    result = runner.invoke(app, [
        "init",
        "-t", output_zip.as_posix(),
        "-r", target_root.as_posix(),
        "--var", "project_name=HookProj",
        "--var", "owner=Alice",
        "--hook-placement", "bottom"
    ])
    
    assert result.exit_code == 0
    assert "Hooked agent instruction files" in result.stdout
    assert "Generated secret phrase:" in result.stdout
    
    # Check that AGENTS.md contains the pre-existing content followed by the hook
    agents_content = agents_file.read_text(encoding="utf-8")
    assert agents_content.startswith("Pre-existing agent info\nLine 2")
    assert "<!-- mdbind-session-hook-start -->" in agents_content
    assert "<!-- mdbind-session-hook-end -->" in agents_content
    assert "[@include: Constitution](scrum/CONSTITUTION.md)" in agents_content
    
    # Retrieve secret phrase from config
    config_file = target_root / ".mdb" / "config.yaml"
    assert config_file.exists()
    config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    secret_phrase = config_data["context_anchoring"]["secret_phrase"]
    assert len(secret_phrase.split()) == 5
    assert secret_phrase in agents_content
    
    # Run check-session-hook and verify success
    check_result = runner.invoke(app, ["check-session-hook", "-r", target_root.as_posix()])
    assert check_result.exit_code == 0
    assert "OK: Hook in 'AGENTS.md' is active and valid." in check_result.stdout
    assert secret_phrase in check_result.stdout


def test_init_session_hook_placement_top(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)
    
    target_root = tmp_path / "target_proj_top"
    target_root.mkdir()
    
    agents_file = target_root / "AGENTS.md"
    agents_file.write_text("Some text here", encoding="utf-8")
    
    # Run init with --hook-placement top
    result = runner.invoke(app, [
        "init",
        "-t", output_zip.as_posix(),
        "-r", target_root.as_posix(),
        "--var", "project_name=TopProj",
        "--var", "owner=Bob",
        "--hook-placement", "top",
        "--hook-secret", "apple banana cherry date elderberry"
    ])
    
    assert result.exit_code == 0
    
    agents_content = agents_file.read_text(encoding="utf-8")
    assert agents_content.startswith("<!-- mdbind-session-hook-start -->")
    assert agents_content.endswith("Some text here")
    assert "apple banana cherry date elderberry" in agents_content


def test_check_session_hook_failures(temp_workspace: Path, tmp_path: Path):
    # Test on non-initialized workspace
    empty_root = tmp_path / "empty_dir"
    empty_root.mkdir()
    check_result = runner.invoke(app, ["check-session-hook", "-r", empty_root.as_posix()])
    assert check_result.exit_code == 1
    combined_output = check_result.stdout + (check_result.stderr or "")
    assert "Error: Workspace not initialized" in combined_output

    # Initialize workspace but modify hooked files to break the hook
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)

    target_root = tmp_path / "target_broken"
    target_root.mkdir()

    runner.invoke(app, [
        "init",
        "-t", output_zip.as_posix(),
        "-r", target_root.as_posix(),
        "--var", "project_name=BrokenProj",
        "--var", "owner=Charlie",
        "--hook-placement", "bottom"
    ])

    # Delete AGENTS.md
    (target_root / "AGENTS.md").unlink()

    check_result2 = runner.invoke(app, ["check-session-hook", "-r", target_root.as_posix()])
    assert check_result2.exit_code == 1
    combined_output2 = check_result2.stdout + (check_result2.stderr or "")
    assert "FAIL: Hooked file 'AGENTS.md' does not exist." in combined_output2


def test_session_hook_commands(temp_workspace: Path, tmp_path: Path):
    output_zip = tmp_path / "package.zip"
    pack_template_package(temp_workspace, output_zip)

    target_root = tmp_path / "target_commands"
    target_root.mkdir()

    # Init workspace without hook first
    runner.invoke(app, [
        "init",
        "-t", output_zip.as_posix(),
        "-r", target_root.as_posix(),
        "--var", "project_name=CmdProj",
        "--var", "owner=Dave",
        "--hook-placement", "none"
    ])

    # Ensure config exists but has no hooks
    config_file = target_root / ".mdb" / "config.yaml"
    assert config_file.exists()
    config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert "context_anchoring" not in config_data or "hooked_files" not in config_data["context_anchoring"] or not config_data["context_anchoring"]["hooked_files"]

    # 1. Inject default hook
    result = runner.invoke(app, [
        "session-hook", "inject",
        "-r", target_root.as_posix(),
        "-p", "bottom",
        "-s", "one two three four five"
    ])
    assert result.exit_code == 0
    assert "Success: Session hooks injected/updated successfully." in result.stdout
    assert "Injected: AGENTS.md" in result.stdout

    # Check file exists and has hook
    agents_file = target_root / "AGENTS.md"
    assert agents_file.exists()
    assert "one two three four five" in agents_file.read_text(encoding="utf-8")

    # Check config is updated
    config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert config_data["context_anchoring"]["secret_phrase"] == "one two three four five"
    assert "AGENTS.md" in config_data["context_anchoring"]["hooked_files"]

    # 2. Inject custom file hook
    custom_rules = target_root / ".customrules"
    custom_rules.write_text("Hello\n", encoding="utf-8")
    result = runner.invoke(app, [
        "session-hook", "inject",
        "-r", target_root.as_posix(),
        "-f", ".customrules",
        "-p", "top",
        "-s", "apple banana orange grape pear"
    ])
    assert result.exit_code == 0
    assert "Injected: .customrules" in result.stdout
    assert "apple banana orange grape pear" in custom_rules.read_text(encoding="utf-8")

    # Check config updated
    config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert config_data["context_anchoring"]["secret_phrase"] == "apple banana orange grape pear"
    assert ".customrules" in config_data["context_anchoring"]["hooked_files"]

    # Inject invalid 4-word phrase
    result_invalid = runner.invoke(app, [
        "session-hook", "inject",
        "-r", target_root.as_posix(),
        "-s", "one two three four"
    ])
    assert result_invalid.exit_code == 1
    assert "Error: The secret phrase must consist of exactly 5 words." in (result_invalid.stdout + (result_invalid.stderr or ""))

    # 3. Remove custom file hook (should restore file to original content since "Hello\n" was present)
    result = runner.invoke(app, [
        "session-hook", "remove",
        "-r", target_root.as_posix(),
        "-f", ".customrules"
    ])
    assert result.exit_code == 0
    assert "Success: Session hooks removed successfully." in result.stdout
    assert "Cleaned: .customrules" in result.stdout
    assert custom_rules.read_text(encoding="utf-8").strip() == "Hello"

    # Check config has removed custom file from hooked_files
    config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert ".customrules" not in config_data["context_anchoring"]["hooked_files"]

    # 4. Remove default hook (AGENTS.md has ONLY the hook, so it should be deleted!)
    result = runner.invoke(app, [
        "session-hook", "remove",
        "-r", target_root.as_posix()
    ])
    assert result.exit_code == 0
    assert "Success: Session hooks removed successfully." in result.stdout
    assert "Cleaned: AGENTS.md" in result.stdout
    assert not agents_file.exists()

    # Check config hooked_files is empty
    config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert not config_data["context_anchoring"].get("hooked_files")

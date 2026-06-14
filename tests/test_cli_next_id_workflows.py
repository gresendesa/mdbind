import subprocess
from pathlib import Path
import pytest
import yaml
from typer.testing import CliRunner

from mdbind.cli import app
from mdbind.template_packages import compute_next_id
from mdbind.models import ParsedSection, RawSection

runner = CliRunner()


class MockSection:
    def __init__(self, uri: str, section_name: str, status: str):
        self.uri = uri
        self.metadata = {
            "id": uri.split("#")[-1],
            "section": section_name,
            "status": status
        }


def test_compute_next_id_basic():
    sections = [
        MockSection("backlog.md#B-001", "backlog.item.B-001", "done"),
        MockSection("backlog.md#B-002", "backlog.item.B-002", "doing"),
        MockSection("backlog.md#B-015", "backlog.item.B-015", "todo"),
    ]
    # Expect B-016 (padded to 3 since max matched group '015' is length 3)
    res = compute_next_id(sections, "B", r"\bB-(\d{3})\b")
    assert res == "B-016"

    # Expect B-16 if pattern has \d+ and max matched group '015' was length 3 (width inherited from max matched string)
    res2 = compute_next_id(sections, "B", r"\bB-(\d+)\b")
    assert res2 == "B-016"


def test_compute_next_id_no_matches():
    sections = []
    # Expect B-001 from prefix and pattern default width (width=3 from \d{3})
    res = compute_next_id(sections, "B", r"\bB-(\d{3})\b")
    assert res == "B-001"

    # Expect B-01 from pattern default width (width=2 from \d{2})
    res2 = compute_next_id(sections, "B-", r"\bB-(\d{2})\b")
    assert res2 == "B-01"


def test_compute_next_id_sprint_prefix():
    sections = [
        MockSection("sprint.md#SPR-2026-01", "sprint.SPR-2026-01", "done"),
        MockSection("sprint.md#SPR-2026-19", "sprint.SPR-2026-19", "done"),
    ]
    # Expect SPR-2026-20
    res = compute_next_id(sections, "SPR-2026-", r"\bSPR-2026-(\d{2})\b")
    assert res == "SPR-2026-20"


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    # Initialize git repo
    subprocess.run(["git", "init", "-b", "main"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=str(tmp_path), check=True)
    return tmp_path


def test_workflow_validation_cli(temp_git_repo: Path):
    # Create configuration .mdb/config.yaml
    mdb_dir = temp_git_repo / ".mdb"
    mdb_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "workflows": [
            {
                "name": "backlog_item",
                "section_pattern": "^backlog\\.item\\.B-\\d{3}$",
                "allowed_statuses": ["todo", "doing", "done"],
                "allowed_transitions": [
                    {"from": "todo", "to": ["doing"]},
                    {"from": "doing", "to": ["done"]}
                ]
            }
        ]
    }
    (mdb_dir / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    # Create backlog file
    backlog_file = temp_git_repo / "backlog.md"
    backlog_content = """# Backlog

## B-001: First item
```yaml
section: backlog.item.B-001
id: B-001
status: todo
```
Some description.
"""
    backlog_file.write_text(backlog_content, encoding="utf-8")

    # Create CONSTITUTION.md to pass template conformity checks
    constitution_file = temp_git_repo / "CONSTITUTION.md"
    constitution_content = """# Constitution

## Rules
```yaml
section: constitution
status: active
```
[@ref: backlog](backlog.md#backlog.item.B-001)
"""
    constitution_file.write_text(constitution_content, encoding="utf-8")

    # Commit initial state
    subprocess.run(["git", "add", "."], cwd=str(temp_git_repo), check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(temp_git_repo), check=True)

    # 1. First validation (without since) should pass
    result = runner.invoke(app, ["validate", "-r", temp_git_repo.as_posix()])
    assert result.exit_code == 0
    assert "OK" in result.stdout

    # 2. Modify status to doing (valid transition)
    backlog_content_doing = backlog_content.replace("status: todo", "status: doing")
    backlog_file.write_text(backlog_content_doing, encoding="utf-8")

    # Validation since HEAD should pass
    result = runner.invoke(app, ["validate", "-r", temp_git_repo.as_posix(), "--since", "HEAD"])
    assert result.exit_code == 0

    # Commit the transition to doing
    subprocess.run(["git", "add", "."], cwd=str(temp_git_repo), check=True)
    subprocess.run(["git", "commit", "-m", "move to doing"], cwd=str(temp_git_repo), check=True)

    # 3. Modify status to todo (invalid transition from doing -> todo)
    backlog_content_todo = backlog_content_doing.replace("status: doing", "status: todo")
    backlog_file.write_text(backlog_content_todo, encoding="utf-8")

    # Validation since HEAD (which has "doing") should fail
    result = runner.invoke(app, ["validate", "-r", temp_git_repo.as_posix(), "--since", "HEAD"])
    assert result.exit_code == 1
    assert "workflow_transition_error" in result.stdout or "Error" in result.stdout

    # 4. Modify status to an unallowed status (e.g. "invalid_status")
    backlog_content_invalid = backlog_content_doing.replace("status: doing", "status: invalid_status")
    backlog_file.write_text(backlog_content_invalid, encoding="utf-8")

    # Validation should fail even without --since due to allowed_statuses constraint
    result = runner.invoke(app, ["validate", "-r", temp_git_repo.as_posix()])
    assert result.exit_code == 1
    assert "workflow_status_error" in result.stdout or "Error" in result.stdout

import io
import json
import hashlib
import zipfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
import yaml

from mdbind.cli import app
from mdbind.template_packages import resolve_template_package_path, pack_template_package

runner = CliRunner()

@pytest.fixture
def mock_template_zip(tmp_path: Path):
    src_dir = tmp_path / "template_src"
    src_dir.mkdir()
    
    manifest = {
        "name": "web-template",
        "version": "1.0.0",
        "description": "A web template",
        "author": "WebTester",
        "template_engine": "jinja2",
        "mdb_version": "0.1.0",
        "instructions": ["scrum/instructions/LLM.md"],
        "variables": [
            {"name": "project_name", "prompt": "Proj Name", "default": "web-proj", "required": True},
        ],
        "files": [
            {"template": "scrum/CONSTITUTION.md.j2", "target": "scrum/CONSTITUTION.md"},
            {"template": "scrum/instructions/LLM.md", "target": "scrum/instructions/LLM.md"},
        ]
    }
    
    (src_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    
    scrum_dir = src_dir / "scrum"
    scrum_dir.mkdir()
    (scrum_dir / "CONSTITUTION.md.j2").write_text("Project: {{ project_name }}\n", encoding="utf-8")
    
    inst_dir = scrum_dir / "instructions"
    inst_dir.mkdir()
    (inst_dir / "LLM.md").write_text("Instructions for {{ project_name }}", encoding="utf-8")
    
    output_zip = tmp_path / "web_package.zip"
    pack_template_package(src_dir, output_zip)
    return output_zip.read_bytes()


class TestWebSchemas:
    @patch("urllib.request.urlopen")
    def test_web_schema_success(self, mock_urlopen, tmp_path):
        schema_content = {
            "type": "object",
            "required": ["id", "schema", "status"],
            "properties": {
                "id": {"type": "string"},
                "schema": {"type": "string"},
                "status": {"enum": ["todo", "doing", "done"]},
            }
        }
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(schema_content).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n"
            "```yaml\n"
            "section: a\n"
            "schema: https://example.com/section.schema.json\n"
            "status: done\n"
            "```\n",
            encoding="utf-8",
        )

        const = tmp_path / "CONSTITUTION.md"
        const.write_text(
            "# Constitution\n\n"
            "```yaml\n"
            "section: constitution\n"
            "```\n\n"
            "[@ref: a](doc.md#a)\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["summary"]["errors"] == 0
        assert mock_urlopen.call_count == 1

        # Second validation should use cached schema, so call count remains 1
        result2 = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        assert result2.exit_code == 0
        assert mock_urlopen.call_count == 1

        # Bypassing cache should increment call count
        result3 = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json", "--no-cache"])
        assert result3.exit_code == 0
        assert mock_urlopen.call_count == 2

    @patch("urllib.request.urlopen")
    def test_web_schema_invalid_json(self, mock_urlopen, tmp_path):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not a valid json mapping"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n"
            "```yaml\n"
            "section: a\n"
            "schema: https://example.com/invalid.schema.json\n"
            "status: done\n"
            "```\n",
            encoding="utf-8",
        )

        const = tmp_path / "CONSTITUTION.md"
        const.write_text(
            "# Constitution\n\n"
            "```yaml\n"
            "section: constitution\n"
            "```\n\n"
            "[@ref: a](doc.md#a)\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        error = data["errors"][0]
        assert error["type"] == "schema_invalid"
        assert "mapping" in error["detail"] or "invalid" in error["detail"]


class TestWebTemplates:
    def test_web_template_missing_checksum_fails(self):
        result = runner.invoke(app, [
            "init",
            "--template", "https://example.com/template.zip",
            "--root", "tmp_init"
        ])
        assert result.exit_code == 1
        assert "checksum is required" in result.output

    @patch("urllib.request.urlopen")
    def test_web_template_success(self, mock_urlopen, mock_template_zip, tmp_path):
        expected_hash = hashlib.sha256(mock_template_zip).hexdigest()
        
        mock_response = MagicMock()
        mock_response.read.return_value = mock_template_zip
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        target_dir = tmp_path / "target_proj"

        result = runner.invoke(app, [
            "init",
            "--template", "https://example.com/template.zip",
            "--root", str(target_dir),
            "--checksum", expected_hash,
            "--var", "project_name=RemoteApp",
            "--var", "owner=PO"
        ])
        assert result.exit_code == 0
        assert "Successfully initialized workspace template" in result.output
        assert (target_dir / "scrum" / "CONSTITUTION.md").exists()
        assert "Project: RemoteApp" in (target_dir / "scrum" / "CONSTITUTION.md").read_text(encoding="utf-8")
        assert mock_urlopen.call_count == 1

        # Calling again with cache enabled should not trigger urlopen
        result2 = runner.invoke(app, [
            "init",
            "--template", "https://example.com/template.zip",
            "--root", str(target_dir),
            "--checksum", expected_hash,
            "--var", "project_name=RemoteApp",
            "--var", "owner=PO",
            "--force"
        ])
        assert result2.exit_code == 0
        assert mock_urlopen.call_count == 1

        # Calling with --no-cache should download again
        result3 = runner.invoke(app, [
            "init",
            "--template", "https://example.com/template.zip",
            "--root", str(target_dir),
            "--checksum", expected_hash,
            "--var", "project_name=RemoteApp",
            "--var", "owner=PO",
            "--no-cache",
            "--force"
        ])
        assert result3.exit_code == 0
        assert mock_urlopen.call_count == 2

    @patch("urllib.request.urlopen")
    def test_web_template_checksum_mismatch_fails(self, mock_urlopen, mock_template_zip, tmp_path):
        mock_response = MagicMock()
        mock_response.read.return_value = mock_template_zip
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        target_dir = tmp_path / "target_proj_mismatch"

        result = runner.invoke(app, [
            "init",
            "--template", "https://example.com/template.zip",
            "--root", str(target_dir),
            "--checksum", "wrongchecksumhexvalue",
            "--var", "project_name=RemoteApp",
            "--var", "owner=PO"
        ])
        assert result.exit_code == 1
        assert "Checksum verification failed" in result.output

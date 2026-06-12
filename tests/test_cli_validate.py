"""
Tests for the CLI 'mdgraph validate' command (B-015).
"""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mdbind.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _uri(filename: str, section_id: str) -> str:
    return str((FIXTURES / filename).resolve()) + "#" + section_id


class TestValidateClean:
    def test_validate_clean_repo_exits_zero(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\nContent.\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path)])
        assert result.exit_code == 0
        assert "no issues found" in result.output.lower() or "OK" in result.output

    def test_validate_clean_repo_json(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\nContent.\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["summary"]["errors"] == 0
        assert data["summary"]["warnings"] == 0
        assert data["summary"]["total_sections"] == 1

    def test_validate_json_schema_keys(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text("# S\n\n```yaml\nsection: s\n```\n", encoding="utf-8")
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        assert "errors" in data
        assert "warnings" in data
        assert "summary" in data
        assert "total_sections" in data["summary"]
        assert "total_edges" in data["summary"]


class TestValidateBrokenRef:
    def test_broken_include_detected(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\n"
            "[@include: label](doc.md#nonexistent)\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path)])
        assert result.exit_code == 1

    def test_broken_include_in_json(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\n"
            "[@include: label](doc.md#nonexistent)\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["summary"]["errors"] >= 1
        types = [e["type"] for e in data["errors"]]
        assert "broken_include" in types

    def test_broken_ref_detected(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\n"
            "[@ref: label](doc.md#ghost)\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        types = [e["type"] for e in data["errors"]]
        assert "broken_ref" in types


class TestValidateCycle:
    def test_include_cycle_detected(self, tmp_path):
        md = tmp_path / "doc.md"
        # A includes B, B includes A
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\n"
            f"[@include: b](doc.md#b)\n\n"
            "# Section B\n\n```yaml\nsection: b\n```\n\n"
            f"[@include: a](doc.md#a)\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        types = [e["type"] for e in data["errors"]]
        assert "cycle" in types

    def test_self_cycle_detected(self, tmp_path):
        md = tmp_path / "doc.md"
        abs_path = md.resolve()
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\n"
            f"[@include: self]({abs_path}#a)\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        types = [e["type"] for e in data["errors"]]
        assert "cycle" in types or data["summary"]["errors"] >= 1


class TestValidateSummary:
    def test_summary_counts_edges(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\n"
            "# Section B\n\n```yaml\nsection: b\n```\n\n"
            f"[@ref: a](doc.md#a)\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        assert data["summary"]["total_sections"] == 2
        assert data["summary"]["total_edges"] == 1

    def test_multiple_errors_reported(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\n```\n\n"
            "[@include: x](doc.md#x)\n"
            "[@ref: y](doc.md#y)\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        assert data["summary"]["errors"] >= 2


class TestValidateSchema:
    def _write_schema(self, tmp_path, name="section.schema.json", content=None):
        schema_dir = tmp_path / "scrum" / "schema"
        schema_dir.mkdir(parents=True)
        schema = schema_dir / name
        schema.write_text(
            content
            or json.dumps({
                "type": "object",
                "required": ["id", "schema", "status"],
                "properties": {
                    "id": {"type": "string"},
                    "schema": {"type": "string"},
                    "status": {"enum": ["todo", "doing", "done"]},
                    "owner": {"type": "string"},
                },
                "additionalProperties": True,
            }),
            encoding="utf-8",
        )
        return schema

    def test_section_without_schema_keeps_current_validation_behavior(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text("# Section A\n\n```yaml\nsection: a\nstatus: freeform\n```\n", encoding="utf-8")

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["summary"]["errors"] == 0

    def test_local_json_schema_valid_metadata_passes(self, tmp_path):
        self._write_schema(tmp_path)
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n"
            "```yaml\n"
            "section: a\n"
            "schema: scrum/schema/section.schema.json\n"
            "status: done\n"
            "```\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["summary"]["errors"] == 0

    def test_local_json_schema_invalid_metadata_fails_with_additive_fields(self, tmp_path):
        self._write_schema(tmp_path)
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n"
            "```yaml\n"
            "section: a\n"
            "schema: scrum/schema/section.schema.json\n"
            "status: blocked\n"
            "```\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        error = data["errors"][0]
        assert error["type"] == "schema_validation_error"
        assert error["uri"].endswith("#a")
        assert error["schema"] == "scrum/schema/section.schema.json"
        assert error["schema_path"].endswith("scrum/schema/section.schema.json")
        assert error["path"] == "status"
        assert "status" in error["detail"] or "one of" in error["detail"]

    def test_local_yaml_schema_validates(self, tmp_path):
        self._write_schema(
            tmp_path,
            name="section.schema.yaml",
            content=(
                "type: object\n"
                "required: [id, schema, priority]\n"
                "properties:\n"
                "  id:\n"
                "    type: string\n"
                "  schema:\n"
                "    type: string\n"
                "  priority:\n"
                "    type: integer\n"
            ),
        )
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n"
            "```yaml\n"
            "section: a\n"
            "schema: scrum/schema/section.schema.yaml\n"
            "priority: 2\n"
            "```\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["summary"]["errors"] == 0

    def test_missing_schema_file_is_deterministic_error(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\nschema: scrum/schema/missing.json\n```\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        error = data["errors"][0]
        assert error["type"] == "schema_not_found"
        assert error["schema"] == "scrum/schema/missing.json"
        assert "not found" in error["detail"]

    def test_invalid_schema_document_is_deterministic_error(self, tmp_path):
        self._write_schema(tmp_path, content="- not\n- a\n- mapping\n")
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n"
            "```yaml\n"
            "section: a\n"
            "schema: scrum/schema/section.schema.json\n"
            "status: done\n"
            "```\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        error = data["errors"][0]
        assert error["type"] == "schema_invalid"
        assert "mapping" in error["detail"] or "invalid schema" in error["detail"]

    def test_web_uri_schema_is_not_resolved_in_this_sprint(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Section A\n\n```yaml\nsection: a\nschema: https://example.com/schema.json\n```\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        error = data["errors"][0]
        assert error["type"] == "schema_unsupported_uri"
        assert error["schema"] == "https://example.com/schema.json"
        assert "not supported" in error["detail"]

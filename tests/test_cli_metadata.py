import json

import yaml
from typer.testing import CliRunner

from mdbind.cli import app


runner = CliRunner()


def _write_doc(tmp_path):
    source = tmp_path / "doc.md"
    source.write_text(
        "# Alpha\n\n"
        "```yaml\n"
        "section: alpha\n"
        "status: draft\n"
        "owner:\n"
        "  name: Alice\n"
        "  team: Docs\n"
        "review:\n"
        "  checklist:\n"
        "    manual: false\n"
        "settings:\n"
        "  retries: 1\n"
        "```\n\n"
        "Body text must stay exactly here.\n\n"
        "[@ref: Beta](doc.md#beta)\n\n"
        "# Beta\n\n"
        "```yaml\n"
        "section: beta\n"
        "status: ready\n"
        "```\n\n"
        "Beta body.\n",
        encoding="utf-8",
    )
    return source


def _uri(source, section_id="alpha"):
    return str(source.resolve()) + "#" + section_id


def _metadata(source, section_id="alpha"):
    result = runner.invoke(app, ["metadata", "get", _uri(source, section_id), "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)["value"]


def test_metadata_get_returns_full_metadata_object(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "get", _uri(source), "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["value"]["section"] == "alpha"
    assert data["value"]["owner"]["name"] == "Alice"


def test_metadata_get_returns_nested_dotted_value(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "get", _uri(source), "owner.name", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["path"] == "owner.name"
    assert data["value"] == "Alice"


def test_metadata_update_changes_flat_scalar_attribute(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "update", _uri(source), "status", '"done"', "--json"])

    assert result.exit_code == 0
    assert _metadata(source)["status"] == "done"


def test_metadata_update_changes_nested_scalar_attribute_by_dotted_path(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(
        app,
        ["metadata", "update", _uri(source), "review.checklist.manual", "true", "--json"],
    )

    assert result.exit_code == 0
    assert _metadata(source)["review"]["checklist"]["manual"] is True


def test_metadata_update_changes_nested_object_value(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(
        app,
        [
            "metadata",
            "update",
            _uri(source),
            "owner",
            '{"name":"Bob","contact":{"email":"bob@example.com"}}',
            "--json",
        ],
    )

    assert result.exit_code == 0
    metadata = _metadata(source)
    assert metadata["owner"] == {
        "name": "Bob",
        "contact": {"email": "bob@example.com"},
    }
    persisted = yaml.safe_load(source.read_text(encoding="utf-8").split("```yaml\n", 1)[1].split("```", 1)[0])
    assert persisted["owner"]["contact"]["email"] == "bob@example.com"


def test_metadata_update_adds_nested_path_and_preserves_body(tmp_path):
    source = _write_doc(tmp_path)
    before = source.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["metadata", "update", _uri(source), "release.window.start", '"2026-06-12"', "--json"],
    )

    assert result.exit_code == 0
    text = source.read_text(encoding="utf-8")
    assert "Body text must stay exactly here." in text
    assert "[@ref: Beta](doc.md#beta)" in text
    assert before.split("Body text must stay exactly here.", 1)[1] == text.split("Body text must stay exactly here.", 1)[1]
    assert _metadata(source)["release"]["window"]["start"] == "2026-06-12"


def test_metadata_unset_removes_top_level_key(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "unset", _uri(source), "status", "--json"])

    assert result.exit_code == 0
    assert "status" not in _metadata(source)


def test_metadata_unset_removes_nested_key_only(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "unset", _uri(source), "owner.team", "--json"])

    assert result.exit_code == 0
    metadata = _metadata(source)
    assert metadata["owner"] == {"name": "Alice"}


def test_metadata_errors_when_section_is_missing(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "get", _uri(source, "missing"), "--json"])

    assert result.exit_code == 1
    assert "section 'missing' not found" in result.output


def test_metadata_update_errors_when_intermediate_value_is_not_mapping(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "update", _uri(source), "status.label", '"x"', "--json"])

    assert result.exit_code == 1
    assert "not a mapping" in result.output


def test_metadata_unset_errors_when_path_is_missing(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "unset", _uri(source), "owner.missing", "--json"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_metadata_update_rejects_section_key_changes(tmp_path):
    source = _write_doc(tmp_path)

    result = runner.invoke(app, ["metadata", "update", _uri(source), "section", '"renamed"', "--json"])

    assert result.exit_code == 1
    assert "read-only" in result.output

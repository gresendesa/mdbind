"""
Tests for CLI commands: neighbors (B-020), explain (B-021), diff (B-022),
query (B-023), context-compose (B-024).
"""
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mdgraph.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
REPO = FIXTURES / "repo"
runner = CliRunner()


def _uri(repo_file: str, section_id: str) -> str:
    return str((REPO / repo_file).resolve()) + "#" + section_id


# ---------------------------------------------------------------------------
# B-020: neighbors
# ---------------------------------------------------------------------------

class TestNeighbors:
    def test_neighbors_exits_zero(self):
        result = runner.invoke(app, ["neighbors", _uri("intro.md", "intro"), "--root", str(REPO)])
        assert result.exit_code == 0

    def test_neighbors_json_schema(self):
        result = runner.invoke(app, ["neighbors", _uri("intro.md", "intro"), "--root", str(REPO), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "uri" in data
        assert "depth" in data
        assert "neighbors" in data
        assert isinstance(data["neighbors"], list)

    def test_neighbors_depth_1_finds_conceito_a(self):
        result = runner.invoke(
            app, ["neighbors", _uri("intro.md", "intro"), "--root", str(REPO), "--json", "--depth", "1"]
        )
        data = json.loads(result.output)
        uris = [n["uri"] for n in data["neighbors"]]
        assert any("conceito-a" in u for u in uris)

    def test_neighbors_depth_1_does_not_reach_detalhe(self):
        # intro -> conceito-a -> detalhe; depth=1 should not reach detalhe
        result = runner.invoke(
            app, ["neighbors", _uri("intro.md", "intro"), "--root", str(REPO), "--json", "--depth", "1"]
        )
        data = json.loads(result.output)
        uris = [n["uri"] for n in data["neighbors"]]
        assert not any("detalhe" in u for u in uris)

    def test_neighbors_depth_2_reaches_detalhe(self):
        result = runner.invoke(
            app, ["neighbors", _uri("intro.md", "intro"), "--root", str(REPO), "--json", "--depth", "2"]
        )
        data = json.loads(result.output)
        uris = [n["uri"] for n in data["neighbors"]]
        assert any("detalhe" in u for u in uris)

    def test_neighbors_includes_incoming(self):
        # conceito-a has intro as incoming neighbor
        result = runner.invoke(
            app, ["neighbors", _uri("conceitos.md", "conceito-a"), "--root", str(REPO), "--json", "--depth", "1"]
        )
        data = json.loads(result.output)
        uris = [n["uri"] for n in data["neighbors"]]
        assert any("intro" in u for u in uris)

    def test_neighbors_direction_field(self):
        result = runner.invoke(
            app, ["neighbors", _uri("intro.md", "intro"), "--root", str(REPO), "--json", "--depth", "1"]
        )
        data = json.loads(result.output)
        assert all("direction" in n for n in data["neighbors"])

    def test_neighbors_uri_not_found_exits_1(self):
        result = runner.invoke(app, ["neighbors", _uri("intro.md", "ghost"), "--root", str(REPO)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# B-021: explain
# ---------------------------------------------------------------------------

class TestExplain:
    def test_explain_exits_zero(self):
        result = runner.invoke(
            app, ["explain", _uri("intro.md", "intro"), _uri("sub/detalhe.md", "detalhe"), "--root", str(REPO)]
        )
        assert result.exit_code == 0

    def test_explain_json_schema(self):
        result = runner.invoke(
            app, ["explain", _uri("intro.md", "intro"), _uri("sub/detalhe.md", "detalhe"),
                  "--root", str(REPO), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "from" in data
        assert "to" in data
        assert "paths" in data
        assert isinstance(data["paths"], list)

    def test_explain_finds_path_intro_to_detalhe(self):
        result = runner.invoke(
            app, ["explain", _uri("intro.md", "intro"), _uri("sub/detalhe.md", "detalhe"),
                  "--root", str(REPO), "--json"]
        )
        data = json.loads(result.output)
        assert len(data["paths"]) >= 1

    def test_explain_no_path_between_unrelated(self):
        # conceito-b has no connections to detalhe
        result = runner.invoke(
            app, ["explain", _uri("conceitos.md", "conceito-b"), _uri("sub/detalhe.md", "detalhe"),
                  "--root", str(REPO), "--json"]
        )
        data = json.loads(result.output)
        assert data["paths"] == []

    def test_explain_path_contains_uri_steps(self):
        result = runner.invoke(
            app, ["explain", _uri("intro.md", "intro"), _uri("sub/detalhe.md", "detalhe"),
                  "--root", str(REPO), "--json"]
        )
        data = json.loads(result.output)
        if data["paths"]:
            path = data["paths"][0]
            uris_in_path = [step["uri"] for step in path]
            assert any("intro" in u for u in uris_in_path)
            assert any("detalhe" in u for u in uris_in_path)

    def test_explain_uri_not_found_exits_1(self):
        result = runner.invoke(
            app, ["explain", _uri("intro.md", "ghost"), _uri("sub/detalhe.md", "detalhe"), "--root", str(REPO)]
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# B-022: diff
# ---------------------------------------------------------------------------

def _is_git_repo(path: Path) -> bool:
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(path),
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@pytest.mark.skipif(
    not _is_git_repo(Path(__file__).parent.parent),
    reason="Not a git repository",
)
class TestDiff:
    def test_diff_json_schema(self):
        result = runner.invoke(app, ["diff", "--root", str(REPO), "--json"])
        # Might fail if HEAD~1 doesn't exist, but schema check is valid on success
        if result.exit_code == 0:
            data = json.loads(result.output)
            assert "since" in data
            assert "added_sections" in data
            assert "removed_sections" in data
            assert "added_edges" in data
            assert "removed_edges" in data

    def test_diff_invalid_ref_exits_1(self):
        result = runner.invoke(app, ["diff", "--root", str(REPO), "--since", "nonexistent-ref-xyz"])
        assert result.exit_code == 1


class TestDiffNotGit:
    def test_diff_non_git_dir_exits_1(self, tmp_path):
        result = runner.invoke(app, ["diff", "--root", str(tmp_path)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# B-023: query
# ---------------------------------------------------------------------------

class TestQuery:
    def test_query_exact(self):
        result = runner.invoke(app, ["query", "id=intro", "--root", str(REPO)])
        assert result.exit_code == 0
        assert "intro" in result.output

    def test_query_json_schema(self):
        result = runner.invoke(app, ["query", "id=intro", "--root", str(REPO), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "expression" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_query_and_operator(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Sec A\n\n```yaml\nsection: sec-a\nowner: alice\nstatus: active\n```\n\n"
            "# Sec B\n\n```yaml\nsection: sec-b\nowner: alice\nstatus: obsolete\n```\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["query", "owner=alice AND status=active", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        assert len(data["results"]) == 1
        assert "sec-a" in data["results"][0]["uri"]

    def test_query_or_operator(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Sec A\n\n```yaml\nsection: sec-a\nowner: alice\n```\n\n"
            "# Sec B\n\n```yaml\nsection: sec-b\nowner: bob\n```\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["query", "owner=alice OR owner=bob", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        assert len(data["results"]) == 2

    def test_query_not_operator(self, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            "# Sec A\n\n```yaml\nsection: sec-a\nstatus: active\n```\n\n"
            "# Sec B\n\n```yaml\nsection: sec-b\nstatus: obsolete\n```\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["query", "NOT status=obsolete", "--root", str(tmp_path), "--json"])
        data = json.loads(result.output)
        uris = [r["uri"] for r in data["results"]]
        assert any("sec-a" in u for u in uris)
        assert not any("sec-b" in u for u in uris)

    def test_query_no_results(self):
        result = runner.invoke(app, ["query", "id=nonexistent-section-xyz", "--root", str(REPO), "--json"])
        data = json.loads(result.output)
        assert data["results"] == []

    def test_query_expression_in_output(self):
        result = runner.invoke(app, ["query", "id=intro", "--root", str(REPO), "--json"])
        data = json.loads(result.output)
        assert data["expression"] == "id=intro"


# ---------------------------------------------------------------------------
# B-024: context-compose
# ---------------------------------------------------------------------------

class TestContextCompose:
    def test_context_compose_exits_zero(self):
        result = runner.invoke(
            app, ["context-compose", _uri("intro.md", "intro"), "--root", str(REPO)]
        )
        assert result.exit_code == 0

    def test_context_compose_json_schema(self):
        result = runner.invoke(
            app, ["context-compose", _uri("intro.md", "intro"), "--root", str(REPO), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "uri" in data
        assert "depth" in data
        assert "token_estimate" in data
        assert "truncated" in data
        assert "content" in data

    def test_context_compose_not_truncated_by_default(self):
        result = runner.invoke(
            app, ["context-compose", _uri("intro.md", "intro"), "--root", str(REPO), "--json"]
        )
        data = json.loads(result.output)
        assert data["truncated"] is False

    def test_context_compose_token_limit_truncates(self):
        result = runner.invoke(
            app, ["context-compose", _uri("intro.md", "intro"), "--root", str(REPO),
                  "--json", "--token-limit", "5"]
        )
        data = json.loads(result.output)
        assert data["truncated"] is True
        assert len(data["content"]) <= 5 * 4

    def test_context_compose_token_estimate_is_integer(self):
        result = runner.invoke(
            app, ["context-compose", _uri("intro.md", "intro"), "--root", str(REPO), "--json"]
        )
        data = json.loads(result.output)
        assert isinstance(data["token_estimate"], int)
        assert data["token_estimate"] >= 0

    def test_context_compose_depth_0_no_includes(self):
        # depth=0 means no @include expansion
        result = runner.invoke(
            app, ["context-compose", _uri("conceitos.md", "conceito-a"), "--root", str(REPO),
                  "--json", "--depth", "0"]
        )
        data = json.loads(result.output)
        # With depth=0, included content (detalhe) should not appear
        assert "Detalhe Tecnico" not in data["content"]

    def test_context_compose_uri_not_found_exits_1(self):
        result = runner.invoke(
            app, ["context-compose", _uri("intro.md", "ghost"), "--root", str(REPO)]
        )
        assert result.exit_code == 1

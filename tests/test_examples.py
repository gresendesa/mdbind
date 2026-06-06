"""
Testes de smoke para o diretorio de exemplos (B-010).
Verifica que os exemplos indexam sem erro e os comandos basicos funcionam.
"""
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mdgraph.cli import app
from mdgraph.index import index_repository

EXAMPLES = Path(__file__).parent.parent / "examples" / "wiki"
runner = CliRunner()


def _uri(rel_path: str, section_id: str) -> str:
    return str((EXAMPLES / rel_path).resolve()) + "#" + section_id


class TestExamplesIndex:
    def setup_method(self):
        self.graph = index_repository(EXAMPLES)

    def test_indexa_sem_erro(self):
        assert len(self.graph.index.sections) >= 4

    def test_secoes_esperadas_presentes(self):
        ids = {s.metadata["id"] for s in self.graph.index.sections.values()}
        assert {"intro", "basico", "avancado", "instalacao"}.issubset(ids)

    def test_aresta_intro_para_instalacao(self):
        intro_uri = str((EXAMPLES / "intro.md").resolve()) + "#intro"
        instalacao_uri = str((EXAMPLES / "guia/instalacao.md").resolve()) + "#instalacao"
        assert instalacao_uri in self.graph.outgoing_edges[intro_uri]

    def test_aresta_instalacao_para_avancado(self):
        instalacao_uri = str((EXAMPLES / "guia/instalacao.md").resolve()) + "#instalacao"
        avancado_uri = str((EXAMPLES / "conceitos/avancado.md").resolve()) + "#avancado"
        assert avancado_uri in self.graph.outgoing_edges[instalacao_uri]


class TestExamplesCli:
    def test_get_intro(self):
        result = runner.invoke(app, ["get", _uri("intro.md", "intro")])
        assert result.exit_code == 0
        assert "Introduction" in result.output or "intro" in result.output.lower()

    def test_get_basico(self):
        result = runner.invoke(app, ["get", _uri("conceitos/basico.md", "basico")])
        assert result.exit_code == 0
        assert "basico" in result.output.lower()

    def test_tree_instalacao(self):
        result = runner.invoke(app, [
            "tree", _uri("guia/instalacao.md", "instalacao"),
            "--root", str(EXAMPLES),
        ])
        assert result.exit_code == 0
        assert "instalacao" in result.output.lower()

    def test_tree_refs_basico(self):
        result = runner.invoke(app, [
            "tree", _uri("conceitos/basico.md", "basico"),
            "--root", str(EXAMPLES),
            "--refs",
        ])
        assert result.exit_code == 0
        assert "basico" in result.output.lower()

    def test_compose_intro_expande_includes(self):
        result = runner.invoke(app, [
            "compose", _uri("intro.md", "intro"),
            "--root", str(EXAMPLES),
        ])
        assert result.exit_code == 0
        # compose of intro must include instalacao and avancado content
        assert "Installation Guide" in result.output or "instalacao" in result.output.lower()
        assert "Prerequisites" in result.output

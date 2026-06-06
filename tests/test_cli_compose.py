"""
Testes do comando CLI 'mdgraph compose' (B-007).
"""
import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mdgraph.cli import app
from mdgraph.composer import compose
from mdgraph.index import index_repository

FIXTURES = Path(__file__).parent / "fixtures"
CYCLES = FIXTURES / "cycles"
runner = CliRunner()


def _uri(filename: str, section_id: str) -> str:
    return str((CYCLES / filename).resolve()) + "#" + section_id


def _make_graph_with_phantom_include():
    from mdgraph.models import ParsedSection, RawSection, SectionGraph, SectionIndex
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Temp\n\n```yaml\nsection: temp\n```\n\n[@include: y](nao-existe.md#y)\n")
        tmp_path = f.name
    raw = RawSection(heading_level=1, heading_text="Temp",
                     token_start=0, token_end=6,
                     source_start_line=1, source_end_line=7)
    section = ParsedSection(raw=raw, uri="tmp#temp", file_path=tmp_path,
                             metadata={"id": "temp"})
    idx = SectionIndex()
    idx.add(section)
    g = SectionGraph(index=idx)
    return g, tmp_path


class TestComposeBasico:
    def test_saida_contem_raiz(self):
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES)])
        assert result.exit_code == 0
        assert "Documento Raiz" in result.output or "raiz" in result.output.lower()

    def test_include_expande_filho(self):
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES)])
        assert result.exit_code == 0
        assert "Conteudo do filho incluido" in result.output

    def test_texto_apos_include_presente(self):
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES)])
        assert result.exit_code == 0
        assert "Texto apos o include" in result.output


class TestComposeStrict:
    def test_placeholder_html_sem_strict(self):
        from mdgraph.composer import compose as do_compose
        g, tmp_path = _make_graph_with_phantom_include()
        try:
            warnings = []
            result = do_compose("tmp#temp", g, strict=False, warnings=warnings)
            assert "mdgraph:unresolved" in result
            assert len(warnings) > 0
        finally:
            os.unlink(tmp_path)

    def test_strict_uri_ausente_levanta_erro(self):
        from mdgraph.composer import compose as do_compose
        g, tmp_path = _make_graph_with_phantom_include()
        try:
            with pytest.raises(ValueError, match="URI nao encontrada"):
                do_compose("tmp#temp", g, strict=True)
        finally:
            os.unlink(tmp_path)


class TestComposeDeduplicate:
    def test_sem_dedup_materializa_filho(self):
        graph = index_repository(CYCLES)
        root_uri = str((CYCLES / "compose_root.md").resolve()) + "#raiz"
        result = compose(root_uri, graph, deduplicate=False)
        assert "Conteudo do filho incluido" in result

    def test_com_dedup_segundo_include_vira_ref(self):
        from mdgraph.composer import compose as do_compose
        from mdgraph.models import (ParsedSection, RawSection,
                                    SectionGraph, SectionIndex)
        import tempfile, os

        # Arquivo filho real (para _raw_lines funcionar)
        child_path = str((CYCLES / "compose_child.md").resolve())

        # Arquivo raiz temporario com dois @include para o mesmo filho (caminho absoluto)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Raiz Dup\n\n```yaml\nsection: raiz-dup\n```\n\n"
                    f"[@include: filho]({child_path}#filho)\n\n"
                    f"[@include: filho]({child_path}#filho)\n")
            tmp_root = f.name

        try:
            # Montar URIs absolutas
            child_uri = child_path + "#filho"
            root_uri = str(Path(tmp_root).resolve()) + "#raiz-dup"

            child_raw = RawSection(heading_level=1, heading_text="Filho",
                                   token_start=0, token_end=4,
                                   source_start_line=1, source_end_line=5)
            child = ParsedSection(raw=child_raw, uri=child_uri,
                                  file_path=child_path,
                                  metadata={"id": "filho"})

            root_raw = RawSection(heading_level=1, heading_text="Raiz Dup",
                                  token_start=0, token_end=8,
                                  source_start_line=1, source_end_line=9)
            root = ParsedSection(raw=root_raw, uri=root_uri,
                                 file_path=tmp_root,
                                 metadata={"id": "raiz-dup"})

            idx = SectionIndex()
            idx.add(root)
            idx.add(child)
            g = SectionGraph(index=idx)
            g.add_edge(root_uri, child_uri)

            result = do_compose(root_uri, g, deduplicate=True)
            assert "@ref(" in result
        finally:
            os.unlink(tmp_root)


class TestComposeHeadingNormalization:
    """
    Testa que o root sempre vira heading level 1 e que
    secoes incluidas sao relativizadas corretamente.

    Bug original: _adjust_heading concatenava '#' * offset ao heading
    existente em vez de substituir o nivel. Exemplo:
      '## Secao' com offset=2 virava '#### Secao' (2+2=4 '#')
      em vez de '#### Secao' por substituicao, ou para o root:
      '## Root' devia virar '# Root', mas o offset 0 mantinha '## Root'.
    """

    def _make_two_level_graph(self):
        """Dois nos no mesmo nivel (level 2) com include entre eles."""
        from mdgraph.models import (ParsedSection, RawSection,
                                    SectionGraph, SectionIndex)
        import tempfile, os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                         delete=False, dir="/tmp") as f:
            f.write("## Filho\n\n```yaml\nsection: filho-h2\n```\n\nConteudo do filho h2.\n")
            child_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                         delete=False, dir="/tmp") as f:
            f.write(f"## Raiz\n\n```yaml\nsection: raiz-h2\n```\n\n"
                    f"[@include: filho]({child_path}#filho-h2)\n")
            root_path = f.name

        root_uri = root_path + "#raiz-h2"
        child_uri = child_path + "#filho-h2"

        child_raw = RawSection(heading_level=2, heading_text="Filho",
                               token_start=0, token_end=4,
                               source_start_line=1, source_end_line=7)
        child = ParsedSection(raw=child_raw, uri=child_uri,
                              file_path=child_path, metadata={"id": "filho-h2"})

        root_raw = RawSection(heading_level=2, heading_text="Raiz",
                              token_start=0, token_end=6,
                              source_start_line=1, source_end_line=7)
        root = ParsedSection(raw=root_raw, uri=root_uri,
                             file_path=root_path, metadata={"id": "raiz-h2"})

        idx = SectionIndex()
        idx.add(root)
        idx.add(child)
        g = SectionGraph(index=idx)
        g.add_edge(root_uri, child_uri)
        return g, root_uri, child_uri, root_path, child_path

    def test_root_nivel2_vira_nivel1(self):
        from mdgraph.composer import compose as do_compose
        import os
        g, root_uri, _, root_path, child_path = self._make_two_level_graph()
        try:
            result = do_compose(root_uri, g)
            first_line = result.splitlines()[0]
            # root '## Raiz' deve virar '# Raiz'
            assert first_line == "# Raiz", f"Esperado '# Raiz', obtido '{first_line}'"
        finally:
            os.unlink(root_path)
            os.unlink(child_path)

    def test_filho_mesmo_nivel_vira_nivel2(self):
        """Filho no mesmo nivel do root (ambos ##) deve virar ## no compose."""
        from mdgraph.composer import compose as do_compose
        import os
        g, root_uri, _, root_path, child_path = self._make_two_level_graph()
        try:
            result = do_compose(root_uri, g)
            lines = result.splitlines()
            heading_lines = [l for l in lines if l.startswith("#")]
            # root vira #, filho vira ##
            assert heading_lines[0] == "# Raiz"
            assert heading_lines[1] == "## Filho", f"Esperado '## Filho', obtido '{heading_lines[1]}'"
        finally:
            os.unlink(root_path)
            os.unlink(child_path)

    def test_root_nivel1_permanece_nivel1(self):
        """Root ja em nivel 1 nao deve ser alterado."""
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES)])
        assert result.exit_code == 0
        first_heading = [l for l in result.output.splitlines() if l.startswith("#")][0]
        assert first_heading.startswith("# ") and not first_heading.startswith("## ")


class TestComposeDepth:
    def test_depth_0_nao_expande_includes(self):
        # Com --depth 0, @include nao deve ser expandido
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES), "--depth", "0"])
        assert result.exit_code == 0
        assert "Conteudo do filho incluido" not in result.output

    def test_depth_1_expande_filho_direto(self):
        # Com --depth 1, o filho direto deve ser expandido
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES), "--depth", "1"])
        assert result.exit_code == 0
        assert "Conteudo do filho incluido" in result.output

    def test_depth_none_expande_tudo(self):
        # Sem --depth, comportamento atual: expande tudo
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES)])
        assert result.exit_code == 0
        assert "Conteudo do filho incluido" in result.output

    def test_depth_0_preserva_conteudo_proprio(self):
        # Com --depth 0, o conteudo do no raiz deve estar presente
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES), "--depth", "0"])
        assert result.exit_code == 0
        assert "Introducao do documento" in result.output
        assert "Texto apos o include" in result.output


class TestComposeJson:
    def test_json_valido(self):
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "uri" in data
        assert "content" in data

    def test_json_contem_conteudo(self):
        result = runner.invoke(app, ["compose", _uri("compose_root.md", "raiz"),
                                     "--root", str(CYCLES), "--json"])
        data = json.loads(result.output)
        assert "Documento Raiz" in data["content"] or "raiz" in data["content"].lower()


class TestComposeErrosCli:
    def test_uri_sem_fragmento_exit_1(self):
        result = runner.invoke(app, ["compose", str(CYCLES / "compose_root.md"),
                                     "--root", str(CYCLES)])
        assert result.exit_code == 1

    def test_arquivo_inexistente_exit_1(self):
        result = runner.invoke(app, ["compose", "/nao/existe.md#id",
                                     "--root", str(CYCLES)])
        assert result.exit_code == 1

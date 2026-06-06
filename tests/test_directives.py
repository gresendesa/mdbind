"""
Testes de tokenizacao de diretivas (B-003).
"""
from pathlib import Path

import pytest

from mdgraph.directives import _resolve_uri, extract_directives
from mdgraph.parser import parse_file, parse_text

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# _resolve_uri
# ---------------------------------------------------------------------------

class TestResolveUri:
    def test_caminho_absoluto_preservado(self):
        result = _resolve_uri("/abs/path.md#id", "/qualquer/origem.md")
        assert result == "/abs/path.md#id"

    def test_caminho_relativo_mesmo_dir(self):
        result = _resolve_uri("outro.md#id", "/repo/docs/origem.md")
        assert result.endswith("outro.md#id")
        assert "docs" in result

    def test_caminho_relativo_subindo(self):
        result = _resolve_uri("../base.md#intro", "/repo/docs/origem.md")
        assert result.endswith("base.md#intro")
        # deve ter subido um nivel
        assert "docs" not in result or result.endswith("base.md#intro")

    def test_apenas_fragmento(self):
        result = _resolve_uri("#id-local", "/repo/doc.md")
        assert result == "/repo/doc.md#id-local"

    def test_sem_fragmento(self):
        result = _resolve_uri("outro.md", "/repo/doc.md")
        assert result.endswith("outro.md")
        assert "#" not in result


# ---------------------------------------------------------------------------
# extract_directives (via parse_file / parse_text)
# ---------------------------------------------------------------------------

class TestDirectivaRef:
    def test_ref_detectada(self):
        sections = parse_file(FIXTURES / "with_ref.md")
        assert len(sections) == 1
        directives = sections[0].directives
        assert len(directives) == 1
        assert directives[0].type == "ref"

    def test_ref_uri_resolvida(self):
        sections = parse_file(FIXTURES / "with_ref.md")
        uri = sections[0].directives[0].target_uri
        # deve conter "outro.md" e o fragmento
        assert "outro.md" in uri
        assert uri.endswith("#alvo")


class TestDirectivaInclude:
    def test_include_detectada(self):
        sections = parse_file(FIXTURES / "with_include.md")
        assert len(sections) == 1
        directives = sections[0].directives
        assert len(directives) == 1
        assert directives[0].type == "include"

    def test_include_uri_relativa_resolvida(self):
        sections = parse_file(FIXTURES / "with_include.md")
        uri = sections[0].directives[0].target_uri
        assert "base.md" in uri
        assert uri.endswith("#intro")


class TestMultiplasDirectivas:
    def setup_method(self):
        self.sections = parse_file(FIXTURES / "multi_directives.md")

    def test_tres_diretivas(self):
        assert len(self.sections[0].directives) == 3

    def test_ordem_de_ocorrencia(self):
        tipos = [d.type for d in self.sections[0].directives]
        assert tipos == ["ref", "include", "query"]

    def test_query_reconhecida(self):
        query_d = self.sections[0].directives[2]
        assert query_d.type == "query"
        assert "tag=foo" in query_d.target_uri


class TestSemDirectivas:
    def test_lista_vazia(self):
        sections = parse_file(FIXTURES / "simple.md")
        assert sections[0].directives == []


class TestDirectivasEmTextoInline:
    def test_inline_no_meio_do_texto(self):
        md = "# X\n\n```yaml\nsection: x\n```\n\nTexto [@ref: z](y.md#z) mais texto.\n"
        sections = parse_text(md, file_path="/repo/doc.md")
        assert len(sections[0].directives) == 1
        assert sections[0].directives[0].type == "ref"
        assert sections[0].directives[0].target_uri.endswith("y.md#z")

    def test_label_preservado(self):
        md = "# X\n\n```yaml\nsection: x\n```\n\n[@ref: Meu Label](y.md#z)\n"
        sections = parse_text(md, file_path="/repo/doc.md")
        assert sections[0].directives[0].label == "Meu Label"

    def test_label_vazio_vira_none(self):
        md = "# X\n\n```yaml\nsection: x\n```\n\n[@ref](y.md#z)\n"
        sections = parse_text(md, file_path="/repo/doc.md")
        assert sections[0].directives[0].label is None

    def test_diretivas_nao_vazam_para_subsecao(self):
        md = (
            "# Pai\n\n```yaml\nsection: pai\n```\n\n"
            "[@ref: x](a.md#x)\n\n"
            "## Filho\n\n```yaml\nsection: filho\n```\n\n"
            "[@include: y](b.md#y)\n"
        )
        sections = parse_text(md, file_path="/repo/doc.md")
        pai = next(s for s in sections if s.metadata["id"] == "pai")
        filho = next(s for s in sections if s.metadata["id"] == "filho")
        # ref pertence ao pai, include pertence ao filho
        assert len(pai.directives) == 1
        assert pai.directives[0].type == "ref"
        assert len(filho.directives) == 1
        assert filho.directives[0].type == "include"

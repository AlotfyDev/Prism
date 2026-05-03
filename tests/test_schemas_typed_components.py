"""Tests for 15 typed physical component schemas (P2.6 typed components)."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    BlockquoteComponent,
    CodeBlockComponent,
    DiagramComponent,
    EmphasisComponent,
    EmphasisType,
    FigureComponent,
    FootnoteComponent,
    HeadingComponent,
    HtmlBlockComponent,
    HtmlInlineComponent,
    InlineCodeComponent,
    LinkComponent,
    LinkType,
    ListComponent,
    MetadataComponent,
    ParagraphComponent,
    TableComponent,
)

# =============================================================================
# HeadingComponent Tests
# =============================================================================


class TestHeadingComponent:
    def test_valid_minimal(self):
        comp = HeadingComponent(
            component_id="heading:h1",
            layer_type=LayerType.HEADING,
            raw_content="# Hello World",
            level=1,
            text="Hello World",
            char_start=0,
            char_end=13,
        )
        assert comp.level == 1
        assert comp.text == "Hello World"
        assert comp.anchor_id is None

    def test_valid_with_anchor_id(self):
        comp = HeadingComponent(
            component_id="heading:h2",
            layer_type=LayerType.HEADING,
            raw_content="## Section Title",
            level=2,
            text="Section Title",
            anchor_id="section-title",
            char_start=0,
            char_end=17,
        )
        assert comp.anchor_id == "section-title"

    def test_valid_all_levels(self):
        for lvl in range(1, 7):
            raw = "#" * lvl + " Text"
            comp = HeadingComponent(
                component_id=f"heading:h{lvl}",
                layer_type=LayerType.HEADING,
                raw_content=raw,
                level=lvl,
                text="Text",
                char_start=0,
                char_end=len(raw),
            )
            assert comp.level == lvl

    def test_invalid_level_zero(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            HeadingComponent(
                component_id="heading:h0",
                layer_type=LayerType.HEADING,
                raw_content="Text",
                level=0,
                text="Text",
                char_start=0,
                char_end=4,
            )

    def test_invalid_level_seven(self):
        with pytest.raises(ValidationError, match="less than or equal to 6"):
            HeadingComponent(
                component_id="heading:h7",
                layer_type=LayerType.HEADING,
                raw_content="####### Text",
                level=7,
                text="Text",
                char_start=0,
                char_end=12,
            )

    def test_invalid_empty_text(self):
        with pytest.raises(ValidationError):
            HeadingComponent(
                component_id="heading:h1",
                layer_type=LayerType.HEADING,
                raw_content="# ",
                level=1,
                text="",
                char_start=0,
                char_end=2,
            )

    def test_id_mismatch_rejected(self):
        with pytest.raises(ValidationError, match="prefix"):
            HeadingComponent(
                component_id="paragraph:h1",
                layer_type=LayerType.HEADING,
                raw_content="# Text",
                level=1,
                text="Text",
                char_start=0,
                char_end=6,
            )
        assert comp.level == 1
        assert comp.text == "Hello World"
        assert comp.anchor_id is None

    def test_valid_with_anchor_id(self):
        comp = HeadingComponent(
            component_id="heading:h2",
            layer_type=LayerType.HEADING,
            raw_content="## Section Title",
            char_start=0,
            char_end=16,
            level=2,
            text="Section Title",
            anchor_id="section-title",
        )
        assert comp.anchor_id == "section-title"

    def test_valid_all_levels(self):
        for lvl in range(1, 7):
            comp = HeadingComponent(
                component_id=f"heading:h{lvl}",
                layer_type=LayerType.HEADING,
                raw_content="#" * lvl + " Text",
                char_start=0,
                char_end=lvl + 5,
                level=lvl,
                text="Text",
            )
            assert comp.level == lvl

    def test_invalid_level_zero(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            HeadingComponent(
                component_id="heading:h0",
                layer_type=LayerType.HEADING,
                raw_content="Text",
                char_start=0,
                char_end=4,
                level=0,
                text="Text",
            )

    def test_invalid_level_seven(self):
        with pytest.raises(ValidationError, match="less than or equal to 6"):
            HeadingComponent(
                component_id="heading:h7",
                layer_type=LayerType.HEADING,
                raw_content="####### Text",
                char_start=0,
                char_end=12,
                level=7,
                text="Text",
            )

    def test_invalid_empty_text(self):
        with pytest.raises(ValidationError):
            HeadingComponent(
                component_id="heading:h1",
                layer_type=LayerType.HEADING,
                raw_content="# ",
                char_start=0,
                char_end=2,
                level=1,
                text="",
            )

    def test_id_mismatch_rejected(self):
        with pytest.raises(ValidationError, match="prefix"):
            HeadingComponent(
                component_id="paragraph:h1",
                layer_type=LayerType.HEADING,
                raw_content="# Text",
                char_start=0,
                char_end=6,
                level=1,
                text="Text",
            )


# =============================================================================
# ParagraphComponent Tests
# =============================================================================


class TestParagraphComponent:
    def test_valid_minimal(self):
        comp = ParagraphComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="This is a paragraph.",
            char_start=0,
            char_end=20,
        )
        assert comp.raw_content == "This is a paragraph."
        assert comp.token_span is None
        assert comp.parent_id is None
        assert comp.children == []
        assert comp.attributes == {}

    def test_valid_with_word_count(self):
        comp = ParagraphComponent(
            component_id="paragraph:p2",
            layer_type=LayerType.PARAGRAPH,
            raw_content="One two three.",
            word_count=3,
            char_start=0,
            char_end=14,
        )
        assert comp.word_count == 3

    def test_invalid_empty_content(self):
        with pytest.raises(ValidationError, match="at least 1 character"):
            ParagraphComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="",
                char_start=0,
                char_end=0,
            )
        assert comp.raw_content == "This is a paragraph."
        assert comp.token_span is None
        assert comp.parent_id is None
        assert comp.children == []
        assert comp.attributes == {}

    def test_valid_with_word_count(self):
        comp = ParagraphComponent(
            component_id="paragraph:p2",
            layer_type=LayerType.PARAGRAPH,
            raw_content="One two three.",
            char_start=0,
            char_end=15,
            word_count=3,
        )
        assert comp.word_count == 3

    def test_invalid_empty_content(self):
        with pytest.raises(ValidationError, match="at least 1 character"):
            ParagraphComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="",
                char_start=0,
                char_end=0,
            )


# =============================================================================
# CodeBlockComponent Tests
# =============================================================================


class TestCodeBlockComponent:
    def test_valid_minimal(self):
        comp = CodeBlockComponent(
            component_id="code_block:c1",
            layer_type=LayerType.CODE_BLOCK,
            raw_content="```python\nprint('hello')\n```",
            char_start=0,
            char_end=28,
        )
        assert comp.language is None
        assert comp.has_lines is False

    def test_valid_with_language(self):
        comp = CodeBlockComponent(
            component_id="code_block:c2",
            layer_type=LayerType.CODE_BLOCK,
            raw_content="```javascript\nconsole.log('hi');\n```",
            language="javascript",
            char_start=0,
            char_end=36,
        )
        assert comp.language == "javascript"

    def test_valid_with_lines(self):
        comp = CodeBlockComponent(
            component_id="code_block:c3",
            layer_type=LayerType.CODE_BLOCK,
            raw_content="```\nline1\nline2\nline3\n```",
            has_lines=True,
            char_start=0,
            char_end=26,
        )
        assert comp.has_lines is True

    def test_valid_common_languages(self):
        for lang in ["python", "javascript", "bash", "rust", "go", "java", "c", "cpp"]:
            raw = "```" + lang + "\ncode\n```"
            comp = CodeBlockComponent(
                component_id="code_block:c",
                layer_type=LayerType.CODE_BLOCK,
                raw_content=raw,
                language=lang,
                char_start=0,
                char_end=len(raw),
            )
            assert comp.language == lang


# =============================================================================
# DiagramComponent Tests
# =============================================================================


class TestDiagramComponent:
    def test_valid_mermaid(self):
        comp = DiagramComponent(
            component_id="diagram:d1",
            layer_type=LayerType.DIAGRAM,
            raw_content="```mermaid\ngraph TD\nA --> B\n```",
            diagram_type="mermaid",
            char_start=0,
            char_end=32,
        )
        assert comp.diagram_type == "mermaid"
        assert comp.title is None

    def test_valid_graphviz(self):
        comp = DiagramComponent(
            component_id="diagram:d2",
            layer_type=LayerType.DIAGRAM,
            raw_content="```graphviz\ndigraph G { A -> B }\n```",
            diagram_type="graphviz",
            title="Architecture",
            char_start=0,
            char_end=37,
        )
        assert comp.diagram_type == "graphviz"
        assert comp.title == "Architecture"

    def test_invalid_empty_diagram_type(self):
        with pytest.raises(ValidationError):
            DiagramComponent(
                component_id="diagram:d1",
                layer_type=LayerType.DIAGRAM,
                raw_content="```mermaid\n```\n",
                diagram_type="",
                char_start=0,
                char_end=15,
            )
        assert comp.diagram_type == "mermaid"
        assert comp.title is None

    def test_valid_graphviz(self):
        comp = DiagramComponent(
            component_id="diagram:d2",
            layer_type=LayerType.DIAGRAM,
            raw_content="```graphviz\ndigraph G { A -> B }\n```",
            char_start=0,
            char_end=35,
            diagram_type="graphviz",
            title="Architecture",
        )
        assert comp.diagram_type == "graphviz"
        assert comp.title == "Architecture"

    def test_invalid_empty_diagram_type(self):
        with pytest.raises(ValidationError):
            DiagramComponent(
                component_id="diagram:d1",
                layer_type=LayerType.DIAGRAM,
                raw_content="```mermaid\n```\n",
                char_start=0,
                char_end=15,
                diagram_type="",
            )


# =============================================================================
# FootnoteComponent Tests
# =============================================================================


class TestFootnoteComponent:
    def test_valid_minimal(self):
        comp = FootnoteComponent(
            component_id="footnote:fn1",
            layer_type=LayerType.FOOTNOTE,
            raw_content="[^1]: This is a footnote.",
            footnote_id="1",
            char_start=0,
            char_end=26,
        )
        assert comp.footnote_id == "1"
        assert comp.has_url is False

    def test_valid_with_url(self):
        comp = FootnoteComponent(
            component_id="footnote:fn2",
            layer_type=LayerType.FOOTNOTE,
            raw_content="[^2]: See https://example.com",
            footnote_id="2",
            has_url=True,
            char_start=0,
            char_end=30,
        )
        assert comp.has_url is True

    def test_invalid_empty_footnote_id(self):
        with pytest.raises(ValidationError):
            FootnoteComponent(
                component_id="footnote:fn1",
                layer_type=LayerType.FOOTNOTE,
                raw_content="[^]: empty",
                footnote_id="",
                char_start=0,
                char_end=10,
            )
        assert comp.footnote_id == "1"
        assert comp.has_url is False

    def test_valid_with_url(self):
        comp = FootnoteComponent(
            component_id="footnote:fn2",
            layer_type=LayerType.FOOTNOTE,
            raw_content="[^2]: See https://example.com",
            char_start=0,
            char_end=31,
            footnote_id="2",
            has_url=True,
        )
        assert comp.has_url is True

    def test_invalid_empty_footnote_id(self):
        with pytest.raises(ValidationError):
            FootnoteComponent(
                component_id="footnote:fn1",
                layer_type=LayerType.FOOTNOTE,
                raw_content="[^]: empty",
                char_start=0,
                char_end=10,
                footnote_id="",
            )


# =============================================================================
# MetadataComponent Tests
# =============================================================================


class TestMetadataComponent:
    def test_valid_yaml(self):
        comp = MetadataComponent(
            component_id="metadata:m1",
            layer_type=LayerType.METADATA,
            raw_content="---\ntitle: Test\n---",
            format="yaml",
            char_start=0,
            char_end=20,
        )
        assert comp.format == "yaml"

    def test_valid_toml(self):
        comp = MetadataComponent(
            component_id="metadata:m2",
            layer_type=LayerType.METADATA,
            raw_content="+++\ntitle = \"Test\"\n+++",
            format="toml",
            char_start=0,
            char_end=22,
        )
        assert comp.format == "toml"

    def test_valid_with_keys(self):
        comp = MetadataComponent(
            component_id="metadata:m3",
            layer_type=LayerType.METADATA,
            raw_content="---\ntitle: Test\nauthor: Alice\n---",
            format="yaml",
            keys=["title", "author"],
            char_start=0,
            char_end=35,
        )
        assert comp.keys == ["title", "author"]

    def test_valid_empty_keys(self):
        comp = MetadataComponent(
            component_id="metadata:m4",
            layer_type=LayerType.METADATA,
            raw_content="---\n---",
            format="yaml",
            char_start=0,
            char_end=7,
        )
        assert comp.keys == []


# =============================================================================
# FigureComponent Tests
# =============================================================================


class TestFigureComponent:
    def test_valid_minimal(self):
        comp = FigureComponent(
            component_id="figure:f1",
            layer_type=LayerType.FIGURE,
            raw_content="![Alt text](image.png)",
            image_url="image.png",
            alt_text="Alt text",
            char_start=0,
            char_end=21,
        )
        assert comp.image_url == "image.png"
        assert comp.alt_text == "Alt text"

    def test_valid_with_dimensions(self):
        comp = FigureComponent(
            component_id="figure:f2",
            layer_type=LayerType.FIGURE,
            raw_content='![Logo](logo.png =200x100)',
            image_url="logo.png",
            alt_text="Logo",
            width=200,
            height=100,
            char_start=0,
            char_end=26,
        )
        assert comp.width == 200
        assert comp.height == 100

    def test_valid_empty_alt_text(self):
        comp = FigureComponent(
            component_id="figure:f3",
            layer_type=LayerType.FIGURE,
            raw_content="![](image.png)",
            image_url="image.png",
            alt_text="",
            char_start=0,
            char_end=14,
        )
        assert comp.alt_text == ""

    def test_invalid_empty_image_url(self):
        with pytest.raises(ValidationError):
            FigureComponent(
                component_id="figure:f4",
                layer_type=LayerType.FIGURE,
                raw_content="![]()",
                image_url="",
                alt_text="test",
                char_start=0,
                char_end=4,
            )
        assert comp.image_url == "image.png"
        assert comp.alt_text == "Alt text"

    def test_valid_with_dimensions(self):
        comp = FigureComponent(
            component_id="figure:f2",
            layer_type=LayerType.FIGURE,
            raw_content='![Logo](logo.png =200x100)',
            char_start=0,
            char_end=28,
            image_url="logo.png",
            alt_text="Logo",
            width=200,
            height=100,
        )
        assert comp.width == 200
        assert comp.height == 100

    def test_valid_empty_alt_text(self):
        comp = FigureComponent(
            component_id="figure:f3",
            layer_type=LayerType.FIGURE,
            raw_content="![](image.png)",
            char_start=0,
            char_end=14,
            image_url="image.png",
            alt_text="",
        )
        assert comp.alt_text == ""

    def test_invalid_empty_image_url(self):
        with pytest.raises(ValidationError):
            FigureComponent(
                component_id="figure:f4",
                layer_type=LayerType.FIGURE,
                raw_content="![]()",
                char_start=0,
                char_end=5,
                image_url="",
                alt_text="test",
            )


# =============================================================================
# BlockquoteComponent Tests
# =============================================================================


class TestBlockquoteComponent:
    def test_valid_minimal(self):
        comp = BlockquoteComponent(
            component_id="blockquote:bq1",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content="> This is a quote.",
            char_start=0,
            char_end=17,
        )
        assert comp.quote_level == 1
        assert comp.attribution is None

    def test_valid_nested(self):
        comp = BlockquoteComponent(
            component_id="blockquote:bq2",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content=">> Nested quote.",
            quote_level=2,
            char_start=0,
            char_end=14,
        )
        assert comp.quote_level == 2

    def test_valid_with_attribution(self):
        comp = BlockquoteComponent(
            component_id="blockquote:bq3",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content="> To be or not to be.\n> — Shakespeare",
            attribution="Shakespeare",
            char_start=0,
            char_end=37,
        )
        assert comp.attribution == "Shakespeare"

    def test_invalid_quote_level_zero(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            BlockquoteComponent(
                component_id="blockquote:bq4",
                layer_type=LayerType.BLOCKQUOTE,
                raw_content="Text",
                quote_level=0,
                char_start=0,
                char_end=4,
            )
        assert comp.quote_level == 1
        assert comp.attribution is None

    def test_valid_nested(self):
        comp = BlockquoteComponent(
            component_id="blockquote:bq2",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content=">> Nested quote.",
            char_start=0,
            char_end=17,
            quote_level=2,
        )
        assert comp.quote_level == 2

    def test_valid_with_attribution(self):
        comp = BlockquoteComponent(
            component_id="blockquote:bq3",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content="> To be or not to be.\n> — Shakespeare",
            char_start=0,
            char_end=41,
            attribution="Shakespeare",
        )
        assert comp.attribution == "Shakespeare"

    def test_invalid_quote_level_zero(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            BlockquoteComponent(
                component_id="blockquote:bq4",
                layer_type=LayerType.BLOCKQUOTE,
                raw_content="Text",
                char_start=0,
                char_end=4,
                quote_level=0,
            )


# =============================================================================
# InlineCodeComponent Tests
# =============================================================================


class TestInlineCodeComponent:
    def test_valid_minimal(self):
        comp = InlineCodeComponent(
            component_id="inline_code:ic1",
            layer_type=LayerType.INLINE_CODE,
            raw_content="`print()`",
            content="print()",
            char_start=0,
            char_end=9,
        )
        assert comp.content == "print()"
        assert comp.language_hint is None

    def test_valid_with_language_hint(self):
        comp = InlineCodeComponent(
            component_id="inline_code:ic2",
            layer_type=LayerType.INLINE_CODE,
            raw_content="`npm install`",
            content="npm install",
            language_hint="bash",
            char_start=0,
            char_end=13,
        )
        assert comp.language_hint == "bash"

    def test_valid_with_syntax_category(self):
        comp = InlineCodeComponent(
            component_id="inline_code:ic3",
            layer_type=LayerType.INLINE_CODE,
            raw_content="`my_function()`",
            content="my_function()",
            syntax_category="function",
            char_start=0,
            char_end=15,
        )
        assert comp.syntax_category == "function"

    def test_invalid_empty_content(self):
        with pytest.raises(ValidationError):
            InlineCodeComponent(
                component_id="inline_code:ic4",
                layer_type=LayerType.INLINE_CODE,
                raw_content="``",
                content="",
                char_start=0,
                char_end=2,
            )
        assert comp.content == "print()"
        assert comp.language_hint is None

    def test_valid_with_language_hint(self):
        comp = InlineCodeComponent(
            component_id="inline_code:ic2",
            layer_type=LayerType.INLINE_CODE,
            raw_content="`npm install`",
            char_start=0,
            char_end=15,
            content="npm install",
            language_hint="bash",
        )
        assert comp.language_hint == "bash"

    def test_valid_with_syntax_category(self):
        comp = InlineCodeComponent(
            component_id="inline_code:ic3",
            layer_type=LayerType.INLINE_CODE,
            raw_content="`my_function()`",
            char_start=0,
            char_end=17,
            content="my_function()",
            syntax_category="function",
        )
        assert comp.syntax_category == "function"

    def test_invalid_empty_content(self):
        with pytest.raises(ValidationError):
            InlineCodeComponent(
                component_id="inline_code:ic4",
                layer_type=LayerType.INLINE_CODE,
                raw_content="``",
                char_start=0,
                char_end=2,
                content="",
            )


# =============================================================================
# EmphasisComponent Tests
# =============================================================================


class TestEmphasisComponent:
    def test_valid_bold(self):
        comp = EmphasisComponent(
            component_id="emphasis:e1",
            layer_type=LayerType.EMPHASIS,
            raw_content="**important**",
            emphasis_type=EmphasisType.BOLD,
            marker="**",
            char_start=0,
            char_end=13,
        )
        assert comp.emphasis_type == EmphasisType.BOLD
        assert comp.marker == "**"

    def test_valid_italic_asterisk(self):
        comp = EmphasisComponent(
            component_id="emphasis:e2",
            layer_type=LayerType.EMPHASIS,
            raw_content="*italic*",
            emphasis_type=EmphasisType.ITALIC,
            marker="*",
            char_start=0,
            char_end=8,
        )
        assert comp.emphasis_type == EmphasisType.ITALIC
        assert comp.marker == "*"

    def test_valid_italic_underscore(self):
        comp = EmphasisComponent(
            component_id="emphasis:e3",
            layer_type=LayerType.EMPHASIS,
            raw_content="_italic_",
            emphasis_type=EmphasisType.ITALIC,
            marker="_",
            char_start=0,
            char_end=8,
        )
        assert comp.marker == "_"

    def test_valid_bold_underscore(self):
        comp = EmphasisComponent(
            component_id="emphasis:e4",
            layer_type=LayerType.EMPHASIS,
            raw_content="__bold__",
            emphasis_type=EmphasisType.BOLD,
            marker="__",
            char_start=0,
            char_end=8,
        )
        assert comp.emphasis_type == EmphasisType.BOLD
        assert comp.marker == "__"

    def test_valid_strikethrough(self):
        comp = EmphasisComponent(
            component_id="emphasis:e5",
            layer_type=LayerType.EMPHASIS,
            raw_content="~~deprecated~~",
            emphasis_type=EmphasisType.STRIKETHROUGH,
            marker="~~",
            char_start=0,
            char_end=14,
        )
        assert comp.emphasis_type == EmphasisType.STRIKETHROUGH

    def test_valid_bold_italic(self):
        comp = EmphasisComponent(
            component_id="emphasis:e6",
            layer_type=LayerType.EMPHASIS,
            raw_content="***bold italic***",
            emphasis_type=EmphasisType.BOLD_ITALIC,
            marker="***",
            char_start=0,
            char_end=17,
        )
        assert comp.emphasis_type == EmphasisType.BOLD_ITALIC

    def test_invalid_empty_marker(self):
        with pytest.raises(ValidationError):
            EmphasisComponent(
                component_id="emphasis:e7",
                layer_type=LayerType.EMPHASIS,
                raw_content="text",
                emphasis_type=EmphasisType.BOLD,
                marker="",
                char_start=0,
                char_end=4,
            )
        assert comp.emphasis_type == EmphasisType.BOLD
        assert comp.marker == "**"

    def test_valid_italic_asterisk(self):
        comp = EmphasisComponent(
            component_id="emphasis:e2",
            layer_type=LayerType.EMPHASIS,
            raw_content="*italic*",
            char_start=0,
            char_end=9,
            emphasis_type=EmphasisType.ITALIC,
            marker="*",
        )
        assert comp.emphasis_type == EmphasisType.ITALIC
        assert comp.marker == "*"

    def test_valid_italic_underscore(self):
        comp = EmphasisComponent(
            component_id="emphasis:e3",
            layer_type=LayerType.EMPHASIS,
            raw_content="_italic_",
            char_start=0,
            char_end=9,
            emphasis_type=EmphasisType.ITALIC,
            marker="_",
        )
        assert comp.marker == "_"

    def test_valid_bold_underscore(self):
        comp = EmphasisComponent(
            component_id="emphasis:e4",
            layer_type=LayerType.EMPHASIS,
            raw_content="__bold__",
            char_start=0,
            char_end=9,
            emphasis_type=EmphasisType.BOLD,
            marker="__",
        )
        assert comp.emphasis_type == EmphasisType.BOLD
        assert comp.marker == "__"

    def test_valid_strikethrough(self):
        comp = EmphasisComponent(
            component_id="emphasis:e5",
            layer_type=LayerType.EMPHASIS,
            raw_content="~~deprecated~~",
            char_start=0,
            char_end=15,
            emphasis_type=EmphasisType.STRIKETHROUGH,
            marker="~~",
        )
        assert comp.emphasis_type == EmphasisType.STRIKETHROUGH

    def test_valid_bold_italic(self):
        comp = EmphasisComponent(
            component_id="emphasis:e6",
            layer_type=LayerType.EMPHASIS,
            raw_content="***bold italic***",
            char_start=0,
            char_end=18,
            emphasis_type=EmphasisType.BOLD_ITALIC,
            marker="***",
        )
        assert comp.emphasis_type == EmphasisType.BOLD_ITALIC

    def test_invalid_empty_marker(self):
        with pytest.raises(ValidationError):
            EmphasisComponent(
                component_id="emphasis:e7",
                layer_type=LayerType.EMPHASIS,
                raw_content="text",
                char_start=0,
                char_end=4,
                emphasis_type=EmphasisType.BOLD,
                marker="",
            )


# =============================================================================
# LinkComponent Tests
# =============================================================================


class TestLinkComponent:
    def test_valid_inline_link(self):
        comp = LinkComponent(
            component_id="link:l1",
            layer_type=LayerType.LINK,
            raw_content="[Markdown Guide](https://markdownguide.org)",
            char_start=0,
            char_end=48,
            link_type=LinkType.INLINE,
            text="Markdown Guide",
            url="https://markdownguide.org",
        )
        assert comp.link_type == LinkType.INLINE
        assert comp.text == "Markdown Guide"
        assert comp.url == "https://markdownguide.org"

    def test_valid_reference_link(self):
        comp = LinkComponent(
            component_id="link:l2",
            layer_type=LayerType.LINK,
            raw_content="[ref][my-ref]",
            char_start=0,
            char_end=15,
            link_type=LinkType.REFERENCE,
            text="ref",
            url="my-ref",
        )
        assert comp.link_type == LinkType.REFERENCE

    def test_valid_image_link(self):
        comp = LinkComponent(
            component_id="link:l3",
            layer_type=LayerType.LINK,
            raw_content="![Logo](logo.png)",
            char_start=0,
            char_end=22,
            link_type=LinkType.IMAGE,
            text="Logo",
            url="logo.png",
        )
        assert comp.link_type == LinkType.IMAGE

    def test_valid_auto_link(self):
        comp = LinkComponent(
            component_id="link:l4",
            layer_type=LayerType.LINK,
            raw_content="<https://example.com>",
            char_start=0,
            char_end=23,
            link_type=LinkType.AUTO,
            text="https://example.com",
            url="https://example.com",
        )
        assert comp.link_type == LinkType.AUTO

    def test_valid_external_detection(self):
        comp = LinkComponent(
            component_id="link:l5",
            layer_type=LayerType.LINK,
            raw_content="[Google](https://google.com)",
            char_start=0,
            char_end=32,
            link_type=LinkType.INLINE,
            text="Google",
            url="https://google.com",
            is_external=True,
            domain="google.com",
        )
        assert comp.is_external is True
        assert comp.domain == "google.com"

    def test_valid_internal_link(self):
        comp = LinkComponent(
            component_id="link:l6",
            layer_type=LayerType.LINK,
            raw_content="[Section](#section)",
            char_start=0,
            char_end=21,
            link_type=LinkType.INLINE,
            text="Section",
            url="#section",
            is_external=False,
        )
        assert comp.is_external is False

    def test_invalid_empty_url(self):
        with pytest.raises(ValidationError):
            LinkComponent(
                component_id="link:l7",
                layer_type=LayerType.LINK,
                raw_content="[text]()",
                char_start=0,
                char_end=9,
                link_type=LinkType.INLINE,
                text="text",
                url="",
            )


# =============================================================================
# HtmlBlockComponent Tests
# =============================================================================


class TestHtmlBlockComponent:
    def test_valid_div(self):
        comp = HtmlBlockComponent(
            component_id="html_block:hb1",
            layer_type=LayerType.HTML_BLOCK,
            raw_content="<div class='container'>Content</div>",
            char_start=0,
            char_end=38,
            tag_name="div",
        )
        assert comp.tag_name == "div"
        assert comp.attributes == {}

    def test_valid_with_attributes(self):
        comp = HtmlBlockComponent(
            component_id="html_block:hb2",
            layer_type=LayerType.HTML_BLOCK,
            raw_content='<iframe src="https://example.com" width="560"></iframe>',
            char_start=0,
            char_end=60,
            tag_name="iframe",
            attributes={"src": "https://example.com", "width": "560"},
        )
        assert comp.attributes["src"] == "https://example.com"

    def test_valid_semantic_tag(self):
        comp = HtmlBlockComponent(
            component_id="html_block:hb3",
            layer_type=LayerType.HTML_BLOCK,
            raw_content="<article>...</article>",
            char_start=0,
            char_end=23,
            tag_name="article",
            is_semantic=True,
        )
        assert comp.is_semantic is True

    def test_valid_comment_block(self):
        comp = HtmlBlockComponent(
            component_id="html_block:hb4",
            layer_type=LayerType.HTML_BLOCK,
            raw_content="<!-- This is a comment -->",
            char_start=0,
            char_end=27,
            tag_name="!--",
        )
        assert comp.tag_name == "!--"

    def test_invalid_empty_tag(self):
        with pytest.raises(ValidationError):
            HtmlBlockComponent(
                component_id="html_block:hb5",
                layer_type=LayerType.HTML_BLOCK,
                raw_content="<></>",
                char_start=0,
                char_end=5,
                tag_name="",
            )


# =============================================================================
# HtmlInlineComponent Tests
# =============================================================================


class TestHtmlInlineComponent:
    def test_valid_span(self):
        comp = HtmlInlineComponent(
            component_id="html_inline:hi1",
            layer_type=LayerType.HTML_INLINE,
            raw_content="<span class='highlight'>text</span>",
            char_start=0,
            char_end=43,
            tag_name="span",
        )
        assert comp.tag_name == "span"

    def test_valid_with_attributes(self):
        comp = HtmlInlineComponent(
            component_id="html_inline:hi2",
            layer_type=LayerType.HTML_INLINE,
            raw_content='<abbr title="HyperText Markup Language">HTML</abbr>',
            char_start=0,
            char_end=65,
            tag_name="abbr",
            attributes={"title": "HyperText Markup Language"},
        )
        assert comp.attributes["title"] == "HyperText Markup Language"

    def test_valid_self_closing(self):
        comp = HtmlInlineComponent(
            component_id="html_inline:hi3",
            layer_type=LayerType.HTML_INLINE,
            raw_content='<br />',
            char_start=0,
            char_end=7,
            tag_name="br",
            is_self_closing=True,
        )
        assert comp.is_self_closing is True

    def test_invalid_empty_tag(self):
        with pytest.raises(ValidationError):
            HtmlInlineComponent(
                component_id="html_inline:hi4",
                layer_type=LayerType.HTML_INLINE,
                raw_content="<></>",
                char_start=0,
                char_end=5,
                tag_name="",
            )


# =============================================================================
# Existing Components (Table, List) — Verify they still work
# =============================================================================


class TestExistingTypedComponents:
    def test_table_component_still_valid(self):
        from prism.schemas.physical import CellPosition, TableCell, TableRow

        comp = TableComponent(
            component_id="table:t1",
            layer_type=LayerType.TABLE,
            raw_content="| A | B |\n| 1 | 2 |",
            char_start=0,
            char_end=20,
            rows=[
                TableRow(
                    row_index=0,
                    cells=[
                        TableCell(position=CellPosition(row=0, col=0, is_header=True)),
                        TableCell(position=CellPosition(row=0, col=1, is_header=True)),
                    ],
                ),
                TableRow(
                    row_index=1,
                    cells=[
                        TableCell(position=CellPosition(row=1, col=0)),
                        TableCell(position=CellPosition(row=1, col=1)),
                    ],
                ),
            ],
            has_header=True,
        )
        assert comp.num_cols == 2
        assert comp.has_header is True

    def test_list_component_still_valid(self):
        from prism.schemas.physical import ListItem, ListStyle

        comp = ListComponent(
            component_id="list:l1",
            layer_type=LayerType.LIST,
            raw_content="- Item 1\n- Item 2",
            char_start=0,
            char_end=20,
            items=[
                ListItem(item_index=0),
                ListItem(item_index=1),
            ],
            style=ListStyle.UNORDERED,
        )
        assert comp.style == ListStyle.UNORDERED
        assert len(comp.items) == 2


# =============================================================================
# All LayerTypes Typed — One per LayerType
# =============================================================================


class TestAllLayerTypesHaveTypedComponents:
    def test_heading_component_has_correct_layer_type(self):
        comp = HeadingComponent(
            component_id="heading:h1",
            layer_type=LayerType.HEADING,
            raw_content="# Title",
            level=1,
            text="Title",
            char_start=0,
            char_end=7,
        )
        assert comp.layer_type == LayerType.HEADING

    def test_paragraph_component_has_correct_layer_type(self):
        comp = ParagraphComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Text",
            char_start=0,
            char_end=4,
        )
        assert comp.layer_type == LayerType.PARAGRAPH

    def test_list_component_has_correct_layer_type(self):
        comp = ListComponent(
            component_id="list:l1",
            layer_type=LayerType.LIST,
            raw_content="- item",
            char_start=0,
            char_end=6,
        )
        assert comp.layer_type == LayerType.LIST

    def test_table_component_has_correct_layer_type(self):
        comp = TableComponent(
            component_id="table:t1",
            layer_type=LayerType.TABLE,
            raw_content="| A |",
            char_start=0,
            char_end=5,
        )
        assert comp.layer_type == LayerType.TABLE

    def test_diagram_component_has_correct_layer_type(self):
        comp = DiagramComponent(
            component_id="diagram:d1",
            layer_type=LayerType.DIAGRAM,
            raw_content="```mermaid\n```\n",
            diagram_type="mermaid",
            char_start=0,
            char_end=15,
        )
        assert comp.layer_type == LayerType.DIAGRAM

    def test_code_block_component_has_correct_layer_type(self):
        comp = CodeBlockComponent(
            component_id="code_block:c1",
            layer_type=LayerType.CODE_BLOCK,
            raw_content="```python\n```",
            char_start=0,
            char_end=14,
        )
        assert comp.layer_type == LayerType.CODE_BLOCK

    def test_footnote_component_has_correct_layer_type(self):
        comp = FootnoteComponent(
            component_id="footnote:fn1",
            layer_type=LayerType.FOOTNOTE,
            raw_content="[^1]: note",
            footnote_id="1",
            char_start=0,
            char_end=10,
        )
        assert comp.layer_type == LayerType.FOOTNOTE

    def test_metadata_component_has_correct_layer_type(self):
        comp = MetadataComponent(
            component_id="metadata:m1",
            layer_type=LayerType.METADATA,
            raw_content="---\n---",
            format="yaml",
            char_start=0,
            char_end=7,
        )
        assert comp.layer_type == LayerType.METADATA

    def test_figure_component_has_correct_layer_type(self):
        comp = FigureComponent(
            component_id="figure:f1",
            layer_type=LayerType.FIGURE,
            raw_content="![alt](img.png)",
            image_url="img.png",
            alt_text="alt",
            char_start=0,
            char_end=16,
        )
        assert comp.layer_type == LayerType.FIGURE

    def test_blockquote_component_has_correct_layer_type(self):
        comp = BlockquoteComponent(
            component_id="blockquote:bq1",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content="> quote",
            char_start=0,
            char_end=7,
        )
        assert comp.layer_type == LayerType.BLOCKQUOTE

    def test_inline_code_component_has_correct_layer_type(self):
        comp = InlineCodeComponent(
            component_id="inline_code:ic1",
            layer_type=LayerType.INLINE_CODE,
            raw_content="`code`",
            content="code",
            char_start=0,
            char_end=6,
        )
        assert comp.layer_type == LayerType.INLINE_CODE

    def test_emphasis_component_has_correct_layer_type(self):
        comp = EmphasisComponent(
            component_id="emphasis:e1",
            layer_type=LayerType.EMPHASIS,
            raw_content="**bold**",
            emphasis_type=EmphasisType.BOLD,
            marker="**",
            char_start=0,
            char_end=8,
        )
        assert comp.layer_type == LayerType.EMPHASIS

    def test_link_component_has_correct_layer_type(self):
        comp = LinkComponent(
            component_id="link:l1",
            layer_type=LayerType.LINK,
            raw_content="[text](url)",
            link_type=LinkType.INLINE,
            text="text",
            url="url",
            char_start=0,
            char_end=11,
        )
        assert comp.layer_type == LayerType.LINK

    def test_html_block_component_has_correct_layer_type(self):
        comp = HtmlBlockComponent(
            component_id="html_block:hb1",
            layer_type=LayerType.HTML_BLOCK,
            raw_content="<div></div>",
            tag_name="div",
            char_start=0,
            char_end=11,
        )
        assert comp.layer_type == LayerType.HTML_BLOCK

    def test_html_inline_component_has_correct_layer_type(self):
        comp = HtmlInlineComponent(
            component_id="html_inline:hi1",
            layer_type=LayerType.HTML_INLINE,
            raw_content="<span></span>",
            tag_name="span",
            char_start=0,
            char_end=13,
        )
        assert comp.layer_type == LayerType.HTML_INLINE

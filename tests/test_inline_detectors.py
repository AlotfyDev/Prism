"""Tests for 5 new inline layer detectors (P2.6)."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.layers.specific_detectors import (
    RegexEmphasisDetector as EmphasisDetector,
    UnifiedHTMLBlockDetector as HTMLBlockDetector,
    UnifiedHTMLInlineDetector as HTMLInlineDetector,
    RegexInlineCodeDetector as InlineCodeDetector,
    UnifiedLinkDetector as LinkDetector,
)


def _make_inline_node(raw: str, char_start: int = 0, char_end: int | None = None) -> MarkdownNode:
    """Create an INLINE MarkdownNode for testing."""
    return MarkdownNode(
        node_type=NodeType.INLINE,
        raw_content=raw,
        char_start=char_start,
        char_end=char_end or (char_start + len(raw)),
    )


def _make_paragraph_node(raw: str, char_start: int = 0) -> MarkdownNode:
    """Create a PARAGRAPH MarkdownNode for testing."""
    return MarkdownNode(
        node_type=NodeType.PARAGRAPH,
        raw_content=raw,
        char_start=char_start,
        char_end=char_start + len(raw),
    )


# =============================================================================
# InlineCodeDetector Tests
# =============================================================================


class TestInlineCodeDetector:
    def test_detect_single_backtick(self):
        detector = InlineCodeDetector()
        source = "Use `code` here"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].layer_type == LayerType.INLINE_CODE
        assert results[0].raw_content == "`code`"
        assert results[0].attributes["content"] == "code"

    def test_detect_double_backtick(self):
        detector = InlineCodeDetector()
        source = "Use ``code with `backtick`` here"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].raw_content == "``code with `backtick``"
        assert results[0].attributes["content"] == "code with `backtick"

    def test_detect_multiple_inline_codes(self):
        detector = InlineCodeDetector()
        source = "Use `foo` and `bar`"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 2
        assert results[0].attributes["content"] == "foo"
        assert results[1].attributes["content"] == "bar"

    def test_no_match_without_backticks(self):
        detector = InlineCodeDetector()
        source = "No code here"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 0

    def test_char_offsets_correct(self):
        detector = InlineCodeDetector()
        source = "prefix `code` suffix"
        nodes = [_make_paragraph_node(source, char_start=7)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].char_start == 7 + 7  # "prefix " = 7 chars
        assert results[0].char_end == 7 + 7 + 6  # "`code`" = 6 chars


# =============================================================================
# EmphasisDetector Tests
# =============================================================================


class TestEmphasisDetector:
    def test_detect_bold(self):
        detector = EmphasisDetector()
        source = "This is **bold** text"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].raw_content == "**bold**"
        assert results[0].attributes["emphasis_type"] == "bold"
        assert results[0].attributes["text"] == "bold"

    def test_detect_italic(self):
        detector = EmphasisDetector()
        source = "This is *italic* text"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].raw_content == "*italic*"
        assert results[0].attributes["emphasis_type"] == "italic"

    def test_detect_strikethrough(self):
        detector = EmphasisDetector()
        source = "This is ~~deleted~~ text"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].raw_content == "~~deleted~~"
        assert results[0].attributes["emphasis_type"] == "strikethrough"

    def test_detect_bold_italic(self):
        detector = EmphasisDetector()
        source = "This is ***bold italic*** text"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) >= 1
        # The bold_italic pattern should match first
        bold_italic_results = [
            r for r in results if r.attributes.get("emphasis_type") == "bold_italic"
        ]
        assert len(bold_italic_results) == 1
        assert bold_italic_results[0].attributes["text"] == "bold italic"

    def test_no_match_without_emphasis(self):
        detector = EmphasisDetector()
        source = "Plain text here"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 0


# =============================================================================
# LinkDetector Tests
# =============================================================================


class TestLinkDetector:
    def test_detect_inline_link(self):
        detector = LinkDetector()
        source = "Visit [Example](https://example.com) now"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].raw_content == "[Example](https://example.com)"
        assert results[0].attributes["link_type"] == "inline"
        assert results[0].attributes["text"] == "Example"
        assert results[0].attributes["url"] == "https://example.com"

    def test_detect_auto_link(self):
        detector = LinkDetector()
        source = "Go to <https://auto.com> now"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].raw_content == "<https://auto.com>"
        assert results[0].attributes["link_type"] == "auto"
        assert results[0].attributes["url"] == "https://auto.com"

    def test_detect_multiple_links(self):
        detector = LinkDetector()
        source = "[A](https://a.com) and [B](https://b.com)"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 2
        assert results[0].attributes["text"] == "A"
        assert results[1].attributes["text"] == "B"

    def test_no_match_without_links(self):
        detector = LinkDetector()
        source = "No links here"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 0

    def test_image_not_detected_as_link(self):
        detector = LinkDetector()
        source = "![alt](image.png)"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        # Image links should not be detected as regular links
        assert len(results) == 0


# =============================================================================
# HTMLBlockDetector Tests
# =============================================================================


class TestHTMLBlockDetector:
    def test_detect_div_block(self):
        detector = HTMLBlockDetector()
        source = "<div>content</div>"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].raw_content == "<div>content</div>"
        assert results[0].attributes["tag_name"] == "div"
        assert results[0].attributes["is_semantic"] == "True"

    def test_detect_non_semantic_tag(self):
        detector = HTMLBlockDetector()
        source = "<table>data</table>"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].attributes["tag_name"] == "table"
        assert results[0].attributes["is_semantic"] == "False"

    def test_no_match_without_html(self):
        detector = HTMLBlockDetector()
        source = "Plain text"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 0


# =============================================================================
# HTMLInlineDetector Tests
# =============================================================================


class TestHTMLInlineDetector:
    def test_detect_span(self):
        detector = HTMLInlineDetector()
        source = "Text <span class='highlight'>highlighted</span> more"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        spans = [r for r in results if r.attributes.get("tag_name") == "span"]
        # Detects both opening and closing tags
        assert len(spans) == 2
        assert spans[0].attributes["is_self_closing"] == "False"
        assert spans[1].raw_content == "</span>"

    def test_detect_self_closing(self):
        detector = HTMLInlineDetector()
        source = "Line break <br/> here"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        brs = [r for r in results if r.attributes.get("tag_name") == "br"]
        assert len(brs) == 1
        assert brs[0].attributes["is_self_closing"] == "True"

    def test_block_tags_excluded(self):
        detector = HTMLInlineDetector()
        source = "Text <div>block</div> here"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        divs = [r for r in results if r.attributes.get("tag_name") == "div"]
        assert len(divs) == 0

    def test_detect_multiple_inline_tags(self):
        detector = HTMLInlineDetector()
        source = "<b>bold</b> and <i>italic</i>"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        # Each opening and closing tag is detected separately
        assert len(results) == 4
        tags = {r.attributes["tag_name"] for r in results}
        assert tags == {"b", "i"}

    def test_no_match_without_html(self):
        detector = HTMLInlineDetector()
        source = "Plain text"
        nodes = [_make_paragraph_node(source)]
        results = detector.detect(nodes, source)
        assert len(results) == 0

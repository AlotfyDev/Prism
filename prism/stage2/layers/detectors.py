"""Detector contracts for Stage 2a (detection phase).

Architecture overview:

    LayerDetector (ABC)          ← Root interface for all detectors
    ├── HeadingDetector (ABC)    ← Contract #1
    ├── ParagraphDetector (ABC)  ← Contract #2
    ├── TableDetector (ABC)      ← Contract #3
    ├── ListDetector (ABC)       ← Contract #4
    ├── CodeBlockDetector (ABC)  ← Contract #5
    ├── BlockquoteDetector (ABC) ← Contract #6
    ├── MetadataDetector (ABC)   ← Contract #7 (+ detect_from_source)
    ├── FootnoteDetector (ABC)   ← Contract #8 (+ detect_from_source)
    ├── DiagramDetector (ABC)    ← Contract #9 (+ _is_diagram_content)
    ├── FigureDetector (ABC)     ← Contract #10
    ├── InlineCodeDetector (ABC) ← Contract #11
    ├── EmphasisDetector (ABC)   ← Contract #12
    ├── LinkDetector (ABC)       ← Contract #13
    ├── HTMLBlockDetector (ABC)  ← Contract #14
    └── HTMLInlineDetector (ABC) ← Contract #15

Each contract defines:
  - ``layer_type`` property: the specific LayerType this detector identifies
  - ``detect()`` abstract method: the detection entry point
  - Optional additional abstract methods for contract-specific behavior

Concrete implementations inherit from their respective contract and
implement the required methods. This enables interchangeable implementations
(AST-based, regex-based, ML-based, external library-based) while maintaining
a consistent interface for the LayerClassifier.
"""

import re
from abc import ABC, abstractmethod
from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import LayerInstance, MarkdownNode, NodeType


# =============================================================================
# UTILITY FUNCTIONS — shared by concrete implementations
# =============================================================================


def _compute_line_number(char_offset: int, lines: list[str]) -> int:
    """Convert character offset to 0-indexed line number."""
    offset = 0
    for i, line in enumerate(lines):
        if offset + len(line) >= char_offset:
            return i
        offset += len(line) + 1
    return len(lines) - 1


def _line_number_at(char_offset: int, source_text: str) -> int:
    """Compute 0-indexed line number at a character offset."""
    return source_text[:char_offset].count("\n")


def _build_instance(
    layer_type: LayerType,
    raw_content: str,
    char_start: int,
    char_end: int,
    source_text: str,
    depth: int,
    sibling_index: int,
    attributes: dict[str, str] | None = None,
) -> LayerInstance:
    """Create a LayerInstance with computed line numbers."""
    lines = source_text.split("\n")
    line_start = _compute_line_number(char_start, lines)
    line_end = _compute_line_number(min(char_end - 1, len(source_text) - 1), lines)
    return LayerInstance(
        layer_type=layer_type,
        char_start=char_start,
        char_end=char_end,
        line_start=line_start,
        line_end=line_end + 1 if line_end >= line_start else line_start + 1,
        raw_content=raw_content,
        depth=depth,
        sibling_index=sibling_index,
        attributes=attributes or {},
    )


def _walk_ast(
    nodes: list[MarkdownNode],
    predicate,
    layer_type: LayerType,
    source_text: str,
    depth: int = 0,
    sibling_offset: dict[int, int] | None = None,
) -> list[LayerInstance]:
    """Walk AST tree, applying predicate to each node.

    Args:
        nodes: Current level of nodes to scan.
        predicate: Callable(MarkdownNode) -> Optional[dict].
            Returns attribute dict if node matches, None to skip.
        layer_type: The LayerType for produced instances.
        source_text: Original Markdown source for line computation.
        depth: Current nesting depth.
        sibling_offset: Tracker for sibling indices at each depth.

    Returns:
        List of LayerInstance objects for matching nodes.
    """
    if sibling_offset is None:
        sibling_offset = {}

    results: list[LayerInstance] = []
    lines = source_text.split("\n")

    if depth not in sibling_offset:
        sibling_offset[depth] = 0

    for node in nodes:
        attrs = predicate(node)
        if attrs is not None:
            char_start = node.char_start if node.char_start is not None else 0
            char_end = node.char_end if node.char_end is not None else char_start + 1

            results.append(
                _build_instance(
                    layer_type=layer_type,
                    raw_content=node.raw_content,
                    char_start=char_start,
                    char_end=char_end,
                    source_text=source_text,
                    depth=depth,
                    sibling_index=sibling_offset[depth],
                    attributes=attrs,
                )
            )
            sibling_offset[depth] += 1

        if node.children:
            child_depth = depth + 1
            child_sib = dict(sibling_offset)
            results.extend(
                _walk_ast(
                    node.children,
                    predicate,
                    layer_type,
                    source_text,
                    depth=child_depth,
                    sibling_offset=child_sib,
                )
            )

    return results


def _scan_inline_nodes(
    nodes: list[MarkdownNode],
    patterns: list[tuple[str, re.Pattern, callable]],
    layer_type: LayerType,
    source_text: str,
    target_node_types: tuple[NodeType, ...],
) -> list[LayerInstance]:
    """Scan INLINE and PARAGRAPH nodes with regex patterns.

    Args:
        nodes: Root-level MarkdownNode objects.
        patterns: List of (name, compiled_regex, extractor) tuples.
            Extractor is callable(Match) -> dict[str, str] | None.
        layer_type: The LayerType for produced instances.
        source_text: Original Markdown source for line computation.
        target_node_types: Node types to scan for patterns.

    Returns:
        List of LayerInstance objects for regex matches.
    """
    results: list[LayerInstance] = []
    sibling_idx = [0]

    def _scan(node: MarkdownNode, depth: int):
        if node.node_type in target_node_types:
            base_start = node.char_start if node.char_start is not None else 0
            for name, pattern, extractor in patterns:
                for match in pattern.finditer(node.raw_content):
                    attrs = extractor(match)
                    if attrs is None:
                        continue
                    full = match.group(0)
                    rel_start = match.start()
                    rel_end = match.end()
                    char_start = base_start + rel_start
                    char_end = base_start + rel_end

                    results.append(
                        _build_instance(
                            layer_type=layer_type,
                            raw_content=full,
                            char_start=char_start,
                            char_end=char_end,
                            source_text=source_text,
                            depth=depth,
                            sibling_index=sibling_idx[0],
                            attributes=attrs,
                        )
                    )
                    sibling_idx[0] += 1
        for child in node.children:
            _scan(child, depth + 1)

    for node in nodes:
        _scan(node, 0)
    return results


# =============================================================================
# ROOT INTERFACE
# =============================================================================


class LayerDetector(ABC):
    """Root interface for all layer detectors.

    Every detector, regardless of its implementation strategy (AST traversal,
    regex scanning, ML inference, external library), must conform to this
    contract. The classifier orchestrates detectors polymorphically via this
    interface, enabling workflow construction without coupling to any specific
    processing unit.
    """

    @property
    @abstractmethod
    def layer_type(self) -> LayerType:
        """The LayerType this detector identifies."""

    @abstractmethod
    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        """Detect layer instances from Markdown AST and/or source text.

        Args:
            nodes: Root-level MarkdownNode objects from the parser.
            source_text: Original Markdown source for char offset computation.

        Returns:
            List of LayerInstance objects for this detector's layer type.
        """


# =============================================================================
# CONTRACT: HeadingDetector
# =============================================================================


class HeadingDetector(LayerDetector):
    """Contract for heading detectors.

    Detects headings (``#``, ``##``, etc.) and produces instances with
    a ``level`` attribute (str, "1" through "6").

    Expected attributes on LayerInstance:
      - ``level``: heading level as string ("1"-"6")

    Possible implementations:
      - AST-based: match NodeType.HEADING nodes
      - Regex-based: scan for ``^#{1,6}`` patterns in source
      - ML-based: classify lines as headings
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HEADING


# =============================================================================
# CONTRACT: ParagraphDetector
# =============================================================================


class ParagraphDetector(LayerDetector):
    """Contract for paragraph detectors.

    Detects paragraphs (contiguous text blocks) and produces instances
    with no special attributes (empty dict).

    Expected attributes on LayerInstance:
      - none (empty attributes dict)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.PARAGRAPH


# =============================================================================
# CONTRACT: TableDetector
# =============================================================================


class TableDetector(LayerDetector):
    """Contract for table detectors.

    Detects GFM tables (pipe-delimited) and produces instances with no
    special attributes. Table structure (rows, cells) is parsed separately.

    Expected attributes on LayerInstance:
      - none (empty attributes dict)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.TABLE


# =============================================================================
# CONTRACT: ListDetector
# =============================================================================


class ListDetector(LayerDetector):
    """Contract for list detectors.

    Detects ordered (numbered) and unordered (bulleted) lists and produces
    instances with a ``style`` attribute.

    Expected attributes on LayerInstance:
      - ``style``: "ordered" or "unordered"
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.LIST


# =============================================================================
# CONTRACT: CodeBlockDetector
# =============================================================================


class CodeBlockDetector(LayerDetector):
    """Contract for code block detectors.

    Detects fenced code blocks (triple-backtick or indented) and produces
    instances with a ``language`` attribute. Must filter out diagram
    languages (mermaid, graphviz, plantuml) — those belong to DiagramDetector.

    Expected attributes on LayerInstance:
      - ``language``: programming language identifier (may be empty string)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.CODE_BLOCK


# =============================================================================
# CONTRACT: BlockquoteDetector
# =============================================================================


class BlockquoteDetector(LayerDetector):
    """Contract for blockquote detectors.

    Detects blockquotes (``>``-prefixed lines) and produces instances
    with no special attributes.

    Expected attributes on LayerInstance:
      - none (empty attributes dict)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.BLOCKQUOTE


# =============================================================================
# CONTRACT: MetadataDetector
# =============================================================================


class MetadataDetector(LayerDetector):
    """Contract for metadata/front-matter detectors.

    Detects YAML/TOML front matter delimited by ``---`` markers.
    If the AST does not contain a METADATA node, the implementation
    must fallback to scanning raw source text.

    Expected attributes on LayerInstance:
      - none (empty attributes dict)

    Additional contract methods:
      - detect_from_source(): fallback detection from raw text
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.METADATA

    @abstractmethod
    def detect_from_source(self, source_text: str) -> list[LayerInstance]:
        """Fallback: detect front matter from raw source text.

        Args:
            source_text: Full Markdown document text.

        Returns:
            List of LayerInstance objects for detected front matter,
            or empty list if none found.
        """


# =============================================================================
# CONTRACT: FootnoteDetector
# =============================================================================


class FootnoteDetector(LayerDetector):
    """Contract for footnote detectors.

    Detects footnote definitions (``[^label]: text``). If the AST does
    not contain FOOTNOTE nodes, the implementation must fallback to
    scanning raw source text.

    Expected attributes on LayerInstance:
      - ``label``: footnote identifier string

    Additional contract methods:
      - detect_from_source(): fallback detection from raw text
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FOOTNOTE

    @abstractmethod
    def detect_from_source(self, source_text: str) -> list[LayerInstance]:
        """Fallback: detect footnote definitions from raw source text.

        Args:
            source_text: Full Markdown document text.

        Returns:
            List of LayerInstance objects for detected footnotes,
            or empty list if none found.
        """


# =============================================================================
# CONTRACT: DiagramDetector
# =============================================================================


class DiagramDetector(LayerDetector):
    """Contract for diagram detectors.

    Detects diagrams embedded in code blocks (mermaid, graphviz, plantuml).
    Detection may use language identifiers or content heuristics.

    Expected attributes on LayerInstance:
      - ``diagram_type``: "mermaid", "graphviz", "plantuml", or "ascii"

    Additional contract methods:
      - _is_diagram_content(): heuristic check for diagram-like content
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.DIAGRAM

    @abstractmethod
    def _is_diagram_content(self, content: str) -> Optional[str]:
        """Heuristic: check if code block content looks like a diagram.

        Args:
            content: Raw code block content.

        Returns:
            Diagram type string if detected, None otherwise.
        """


# =============================================================================
# CONTRACT: FigureDetector
# =============================================================================


class FigureDetector(LayerDetector):
    """Contract for figure/image detectors.

    Detects Markdown image syntax (``![alt](src)``) within inline content.
    Unlike other AST-based detectors, this scans for regex patterns within
    nodes rather than matching node types directly.

    Expected attributes on LayerInstance:
      - ``caption``: alt text from image syntax
      - ``src``: URL or path from image syntax
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FIGURE


# =============================================================================
# CONTRACT: InlineCodeDetector
# =============================================================================


class InlineCodeDetector(LayerDetector):
    """Contract for inline code detectors.

    Detects inline code spans: single-backtick (`` `code` ``) and
    double-backtick (`` ``code`` ``) forms.

    Expected attributes on LayerInstance:
      - ``content``: code text without backticks
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.INLINE_CODE


# =============================================================================
# CONTRACT: EmphasisDetector
# =============================================================================


class EmphasisDetector(LayerDetector):
    """Contract for emphasis detectors.

    Detects emphasis markers: ``**bold**``, ``*italic*``,
    ``~~strikethrough~~``, ``***bold italic***``.

    Expected attributes on LayerInstance:
      - ``emphasis_type``: "bold", "italic", "strikethrough", "bold_italic"
      - ``marker``: the markdown marker used ("**", "*", "~~", "***")
      - ``text``: the emphasized text content
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.EMPHASIS


# =============================================================================
# CONTRACT: LinkDetector
# =============================================================================


class LinkDetector(LayerDetector):
    """Contract for link detectors.

    Detects inline links (``[text](url)``) and auto-links (``<url>``).
    Must NOT detect image links (``![alt](src)``) — those belong to FigureDetector.

    Expected attributes on LayerInstance:
      - ``link_type``: "inline" or "auto"
      - ``text``: link text
      - ``url``: target URL
      - ``is_external``: "True" if URL starts with http(s), else "False"
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.LINK


# =============================================================================
# CONTRACT: HTMLBlockDetector
# =============================================================================


class HTMLBlockDetector(LayerDetector):
    """Contract for HTML block detectors.

    Detects block-level HTML tags (``<div>``, ``<section>``, ``<table>``, etc.)
    that span one or more lines.

    Expected attributes on LayerInstance:
      - ``tag_name``: HTML tag name (lowercase)
      - ``is_semantic``: "True" if tag is semantic HTML5 element, else "False"
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HTML_BLOCK


# =============================================================================
# CONTRACT: HTMLInlineDetector
# =============================================================================


class HTMLInlineDetector(LayerDetector):
    """Contract for inline HTML detectors.

    Detects inline HTML tags (``<span>``, ``<br/>``, ``<b>``, etc.)
    embedded within text. Must NOT detect block-level tags.

    Expected attributes on LayerInstance:
      - ``tag_name``: HTML tag name (lowercase)
      - ``is_self_closing``: "True" if tag is self-closing
      - Additional attributes from HTML attributes (e.g., ``class``, ``id``)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HTML_INLINE


# =============================================================================
# CONTRACT: HRDetector
# =============================================================================


class HRDetector(LayerDetector):
    """Contract for horizontal rule detectors.

    Detects horizontal rules (thematic breaks) from Markdown AST nodes.
    Horizontal rules use 3+ identical characters: ``---``, ``***``, ``___``.

    Expected attributes on LayerInstance:
      - ``style``: "dash", "star", or "underscore"
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HORIZONTAL_RULE


# =============================================================================
# CONTRACT: IndentedCodeBlockDetector
# =============================================================================


class IndentedCodeBlockDetector(LayerDetector):
    """Contract for indented code block detectors.

    Detects indented code blocks (4+ spaces or 1+ tab) from Markdown AST nodes.
    Indented code blocks have no language specification and are treated as
    raw preformatted text per CommonMark spec.

    Expected attributes on LayerInstance:
      - ``line_count``: number of lines in the code block
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.INDENTED_CODE_BLOCK


# =============================================================================
# CONTRACT: FootnoteRefDetector
# =============================================================================


class FootnoteRefDetector(LayerDetector):
    """Contract for footnote reference detectors.

    Detects inline footnote references (``[^id]``) within paragraph/inline text.
    These are the markers that link to footnote definitions at the end of the document.

    Expected attributes on LayerInstance:
      - ``ref_id``: footnote reference identifier string
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FOOTNOTE_REF

"""Concrete layer detectors for Stage 2a (detection phase).

Each concrete class inherits from its contract (defined in ``detectors.py``)
and implements the ``detect()`` method. Contracts define WHAT each detector
must produce; concrete classes define HOW they produce it.

Detection strategies:
- AST-based: match NodeType in the MarkdownItParser AST tree (5 detectors)
- Hybrid: AST first, then fallback to raw text regex scanning (2 detectors)
- Heuristic: language identifier + content pattern matching (2 detectors)
- Inline scanner: regex finditer on INLINE/PARAGRAPH node content (4 detectors)
- Compositional: Prism AST + native parsers (6 detectors)

Naming convention: concrete classes are prefixed with their strategy
(e.g., ``ASTHeadingDetector``, ``UnifiedCodeBlockDetector``) to avoid
name collisions with the contract classes in ``detectors.py``.
"""

import re
from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import LayerInstance, MarkdownNode, NodeType

from prism.stage2.layers.detectors import (
    LayerDetector,
    HeadingDetector,
    ParagraphDetector,
    TableDetector,
    ListDetector,
    CodeBlockDetector,
    BlockquoteDetector,
    MetadataDetector,
    FootnoteDetector,
    FootnoteRefDetector,
    DiagramDetector,
    FigureDetector,
    InlineCodeDetector,
    EmphasisDetector,
    LinkDetector,
    HTMLBlockDetector,
    HTMLInlineDetector,
    HRDetector,
    IndentedCodeBlockDetector,
    _walk_ast,
    _build_instance,
    _scan_inline_nodes,
    _line_number_at,
)


# =============================================================================
# HTML block boundary parser (CommonMark-compliant)
# =============================================================================

# Type 1: <script>, <pre>, <style> — case-insensitive, whitespace attrs allowed
_HTML_BLOCK_OPEN_1 = re.compile(
    r"^<(?i:script|pre|style)(\s|>|$)", re.IGNORECASE
)
_HTML_BLOCK_CLOSE_1 = re.compile(
    r"</(?i:script|pre|style)\s*>", re.IGNORECASE
)

# Type 2: HTML comments <!-- ... -->
_HTML_BLOCK_OPEN_2 = re.compile(r"^<!--")
_HTML_BLOCK_CLOSE_2 = re.compile(r"-->\s*$")

# Type 3: <? ... ?> (processing instructions)
_HTML_BLOCK_OPEN_3 = re.compile(r"^<\?")
_HTML_BLOCK_CLOSE_3 = re.compile(r"\?>\s*$")

# Type 4: <! ... > (declarations except CDATA)
_HTML_BLOCK_OPEN_4 = re.compile(r"^<![A-Za-z]")
_HTML_BLOCK_CLOSE_4 = re.compile(r">\s*$")

# Type 5: <![CDATA[ ... ]]>
_HTML_BLOCK_OPEN_5 = re.compile(r"^<!\[CDATA\[")
_HTML_BLOCK_CLOSE_5 = re.compile(r"\]\]>\s*$")

# Type 6: Block-level HTML elements (opening tag at line start)
_BLOCK_HTML_TAGS = frozenset({
    "address", "article", "aside", "base", "basefont", "blockquote", "body",
    "caption", "center", "col", "colgroup", "dd", "details", "dialog", "dir",
    "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
    "frame", "frameset", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header",
    "hr", "html", "iframe", "legend", "li", "link", "main", "menu", "menuitem",
    "nav", "noframes", "ol", "optgroup", "option", "p", "param", "search",
    "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead",
    "title", "tr", "track", "ul",
})
_HTML_BLOCK_OPEN_6 = re.compile(
    r"^<(" + "|".join(_BLOCK_HTML_TAGS) + r")(\s|>|$)",
    re.IGNORECASE
)
_HTML_BLOCK_CLOSE_6 = re.compile(
    r"^</(" + "|".join(_BLOCK_HTML_TAGS) + r")\s*>",
    re.IGNORECASE
)


def _find_html_blocks(source_text: str) -> list[tuple[int, int, str]]:
    """Find all HTML blocks in source text.

    Returns list of (char_start, char_end, content) tuples.
    Follows CommonMark spec for 7 types of HTML blocks.
    """
    lines = source_text.split("\n")
    n_lines = len(lines)
    results: list[tuple[int, int, str]] = []

    # Precompute char offsets for each line
    char_offsets: list[int] = []
    offset = 0
    for line in lines:
        char_offsets.append(offset)
        offset += len(line) + 1

    pos = 0
    while pos < n_lines:
        line = lines[pos].strip()
        if not line:
            pos += 1
            continue

        block_type = _classify_html_block_start(line)
        if block_type is None:
            pos += 1
            continue

        start_pos = pos
        block_lines: list[str] = []

        if block_type <= 5:
            # Types 1-5: scan until closing condition
            while pos < n_lines:
                block_lines.append(lines[pos])
                pos += 1
                if _matches_close_condition(block_type, lines[pos - 1]):
                    break
        else:
            # Type 6: scan until blank line or closing tag
            while pos < n_lines:
                block_lines.append(lines[pos])
                pos += 1
                next_line = lines[pos].strip() if pos < n_lines else ""
                if not next_line:
                    break
                if _HTML_BLOCK_CLOSE_6.match(next_line):
                    block_lines.append(lines[pos])
                    pos += 1
                    break

        content = "\n".join(block_lines)
        char_start = char_offsets[start_pos]
        char_end = char_start + len(content)
        results.append((char_start, char_end, content))

    return results


def _classify_html_block_start(line: str) -> int | None:
    """Classify which HTML block type (1-7) starts at this line, or None."""
    if _HTML_BLOCK_OPEN_1.match(line):
        return 1
    if _HTML_BLOCK_OPEN_2.match(line):
        return 2
    if _HTML_BLOCK_OPEN_3.match(line):
        return 3
    if _HTML_BLOCK_OPEN_5.match(line):
        return 5
    if _HTML_BLOCK_OPEN_4.match(line):
        return 4
    if _HTML_BLOCK_OPEN_6.match(line):
        return 6
    # Type 7: any other line starting with < that looks like HTML
    if line.startswith("<") and re.match(r"^</?[a-zA-Z]", line):
        return 7
    return None


def _matches_close_condition(block_type: int, line: str) -> bool:
    """Check if line matches the closing condition for a given block type."""
    if block_type == 1:
        return bool(_HTML_BLOCK_CLOSE_1.search(line))
    if block_type == 2:
        return bool(_HTML_BLOCK_CLOSE_2.search(line))
    if block_type == 3:
        return bool(_HTML_BLOCK_CLOSE_3.search(line))
    if block_type == 4:
        return bool(_HTML_BLOCK_CLOSE_4.search(line))
    if block_type == 5:
        return bool(_HTML_BLOCK_CLOSE_5.search(line))
    if block_type == 6:
        return bool(_HTML_BLOCK_CLOSE_6.match(line.strip()))
    return False


# =============================================================================
# BATCH 1: Simple AST-based detectors (5)
# =============================================================================


class ASTHeadingDetector(HeadingDetector):
    """AST-based implementation: matches NodeType.HEADING nodes."""

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.HEADING:
                level = node.level if node.level is not None else 1
                heading_style = node.attributes.get("heading_style", "atx")
                return {"level": str(level), "heading_style": heading_style}
            return None

        return _walk_ast(nodes, predicate, LayerType.HEADING, source_text)


class ASTParagraphDetector(ParagraphDetector):
    """AST-based implementation: matches NodeType.PARAGRAPH nodes."""

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.PARAGRAPH:
                return {}
            return None

        return _walk_ast(nodes, predicate, LayerType.PARAGRAPH, source_text)


class ASTTableDetector(TableDetector):
    """AST-based implementation: matches NodeType.TABLE nodes."""

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.TABLE:
                return {}
            return None

        return _walk_ast(nodes, predicate, LayerType.TABLE, source_text)


class ASTBlockquoteDetector(BlockquoteDetector):
    """AST-based implementation: matches NodeType.BLOCKQUOTE nodes."""

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.BLOCKQUOTE:
                return {}
            return None

        return _walk_ast(nodes, predicate, LayerType.BLOCKQUOTE, source_text)


# =============================================================================
# BATCH 2: Hybrid AST detectors (2) — AST first, raw text fallback
# =============================================================================


class HybridMetadataDetector(MetadataDetector):
    """Hybrid implementation: AST first, then raw text regex fallback."""

    FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.METADATA:
                return {}
            return None

        ast_results = _walk_ast(nodes, predicate, LayerType.METADATA, source_text)
        if ast_results:
            return ast_results

        return self.detect_from_source(source_text)

    def detect_from_source(self, source_text: str) -> list[LayerInstance]:
        match = self.FRONT_MATTER_RE.match(source_text)
        if match:
            content = match.group(0)
            return [
                _build_instance(
                    layer_type=LayerType.METADATA,
                    raw_content=content.strip(),
                    char_start=0,
                    char_end=len(content),
                    source_text=source_text,
                    depth=0,
                    sibling_index=0,
                )
            ]
        return []


class UnifiedFootnoteDetector(FootnoteDetector):
    """Compositional: Prism AST/raw + native reference tracking.

    Detects footnote definitions via AST or raw text, AND tracks footnote
    references ``[^id]`` within inline text using native regex scanning.
    """

    FOOTNOTE_DEF_RE = re.compile(
        r"^\[\^([^\]]+)\]:\s*(.+)$",
        re.MULTILINE,
    )

    FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\]")

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        # Definitions: AST first
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.FOOTNOTE:
                label = node.attributes.get("label", "")
                return {"label": label}
            return None

        def_results = _walk_ast(nodes, predicate, LayerType.FOOTNOTE, source_text)
        if def_results:
            definitions = def_results
        else:
            definitions = self._detect_definitions(source_text)

        # References: scan inline text
        references = self._detect_references(source_text)
        ref_labels = {r["id"] for r in references}

        # Enrich definitions with reference info
        for inst in definitions:
            label = inst.attributes.get("label", "")
            inst.attributes["has_references"] = str(label in ref_labels)
            inst.attributes["reference_count"] = str(
                sum(1 for r in references if r["id"] == label)
            )

        return definitions

    def detect_from_source(self, source_text: str) -> list[LayerInstance]:
        return self._detect_definitions(source_text)

    def _detect_definitions(self, source_text: str) -> list[LayerInstance]:
        results: list[LayerInstance] = []
        for match in self.FOOTNOTE_DEF_RE.finditer(source_text):
            label = match.group(1)
            content = match.group(0)
            char_start = match.start()
            char_end = match.end()

            results.append(
                _build_instance(
                    layer_type=LayerType.FOOTNOTE,
                    raw_content=content.strip(),
                    char_start=char_start,
                    char_end=char_end,
                    source_text=source_text,
                    depth=0,
                    sibling_index=len(results),
                    attributes={"label": label},
                )
            )
        return results

    def _detect_references(self, source_text: str) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for match in self.FOOTNOTE_REF_RE.finditer(source_text):
            results.append({
                "id": match.group(1),
                "char_start": match.start(),
                "char_end": match.end(),
            })
        return results


# =============================================================================
# BATCH 2b: Heuristic AST detectors (2)
# =============================================================================


class _DiagramContentHeuristic:
    """Shared heuristic for detecting diagram-like code content."""

    DIAGRAM_LANGUAGES = frozenset({"mermaid", "graphviz", "plantuml", "dot"})

    DIAGRAM_KEYWORDS = [
        "graph ", "digraph ", "flowchart ", "sequenceDiagram",
        "gantt", "pie ", "classDiagram", "stateDiagram",
        "erDiagram", "journey", "gitGraph",
    ]

    @classmethod
    def is_diagram_content(cls, content: str) -> Optional[str]:
        """Check if code block content looks like a diagram."""
        first_line = content.strip().split("\n")[0].lower()
        for kw in cls.DIAGRAM_KEYWORDS:
            if first_line.startswith(kw):
                return "mermaid"
        return None


class HeuristicDiagramDetector(DiagramDetector):
    """Heuristic implementation: language identifier + content pattern matching."""

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.CODE_BLOCK:
                language = node.attributes.get("language", "").lower()
                if language in _DiagramContentHeuristic.DIAGRAM_LANGUAGES:
                    return {"diagram_type": language}
                if not language:
                    detected = self._is_diagram_content(node.raw_content)
                    if detected:
                        return {"diagram_type": detected}
            return None

        return _walk_ast(nodes, predicate, LayerType.DIAGRAM, source_text)

    def _is_diagram_content(self, content: str) -> Optional[str]:
        return _DiagramContentHeuristic.is_diagram_content(content)


class RegexFigureDetector(FigureDetector):
    """Regex-scanning implementation: scans inline nodes for image syntax."""

    IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        results: list[LayerInstance] = []
        sibling_idx = [0]

        def _scan_node(node: MarkdownNode, depth: int):
            if node.node_type == NodeType.INLINE:
                base_start = node.char_start if node.char_start is not None else 0
                for match in self.IMAGE_RE.finditer(node.raw_content):
                    caption = match.group(1)
                    src = match.group(2)
                    full = match.group(0)
                    rel_start = match.start()
                    rel_end = match.end()
                    char_start = base_start + rel_start
                    char_end = base_start + rel_end

                    results.append(
                        _build_instance(
                            layer_type=LayerType.FIGURE,
                            raw_content=full,
                            char_start=char_start,
                            char_end=char_end,
                            source_text=source_text,
                            depth=depth,
                            sibling_index=sibling_idx[0],
                            attributes={"caption": caption, "src": src},
                        )
                    )
                    sibling_idx[0] += 1
            for child in node.children:
                _scan_node(child, depth + 1)

        for node in nodes:
            _scan_node(node, 0)
        return results


# =============================================================================
# BATCH 3: Inline regex-scanning detectors (4)
# =============================================================================


class RegexInlineCodeDetector(InlineCodeDetector):
    """Regex implementation: scans for `code` and ``code`` patterns."""

    INLINE_CODE_RE = re.compile(r"``(.+?)``|`([^`]+)`")

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def extractor(match: re.Match) -> dict[str, str]:
            content = match.group(1) if match.group(1) is not None else match.group(2)
            return {"content": content}

        return _scan_inline_nodes(
            nodes=nodes,
            patterns=[("inline_code", self.INLINE_CODE_RE, extractor)],
            layer_type=LayerType.INLINE_CODE,
            source_text=source_text,
            target_node_types=(NodeType.INLINE, NodeType.PARAGRAPH),
        )


class RegexEmphasisDetector(EmphasisDetector):
    """Regex implementation: scans for bold, italic, strikethrough patterns."""

    EMPHASIS_PATTERNS = [
        ("bold_italic", re.compile(r"\*\*\*(.+?)\*\*\*")),
        ("bold", re.compile(r"\*\*(.+?)\*\*")),
        ("italic", re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")),
        ("strikethrough", re.compile(r"~~(.+?)~~")),
    ]

    _MARKER_MAP = {
        "bold_italic": "***",
        "bold": "**",
        "italic": "*",
        "strikethrough": "~~",
    }

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def make_extractor(emph_type: str):
            def extractor(match: re.Match) -> dict[str, str]:
                return {
                    "emphasis_type": emph_type,
                    "marker": self._MARKER_MAP[emph_type],
                    "text": match.group(1),
                }
            return extractor

        patterns = [
            (name, pattern, make_extractor(name))
            for name, pattern in self.EMPHASIS_PATTERNS
        ]

        return _scan_inline_nodes(
            nodes=nodes,
            patterns=patterns,
            layer_type=LayerType.EMPHASIS,
            source_text=source_text,
            target_node_types=(NodeType.INLINE, NodeType.PARAGRAPH),
        )


class UnifiedLinkDetector(LinkDetector):
    """Compositional: Prism inline/auto + native reference links.

    Detects:
    - Inline links: ``[text](url)`` (Prism regex)
    - Auto-links: ``<url>`` (Prism regex)
    - Reference links: ``[text][ref]`` + ``[ref]: url`` (native regex)
    """

    INLINE_LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
    AUTO_LINK_RE = re.compile(r"<(https?://[^>]+)>")
    REFERENCE_LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\[([^\]]*)\]")
    REFERENCE_DEF_RE = re.compile(r"^\[([^\]]+)\]:\s+(.*?)\s*$", re.MULTILINE)

    _SELF_LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\[\s*\]")

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        # Parse reference definitions
        ref_defs: dict[str, str] = {}
        for match in self.REFERENCE_DEF_RE.finditer(source_text):
            ref_id = match.group(1).lower()
            url = match.group(2).strip()
            ref_defs[ref_id] = url

        # Inline links
        def inline_extractor(match: re.Match) -> dict[str, str]:
            text = match.group(1)
            url = match.group(2)
            return {
                "link_type": "inline",
                "text": text,
                "url": url,
                "is_external": str(url.startswith("http")),
                "domain": self._extract_domain(url),
            }

        results_inline = _scan_inline_nodes(
            nodes=nodes,
            patterns=[("inline_link", self.INLINE_LINK_RE, inline_extractor)],
            layer_type=LayerType.LINK,
            source_text=source_text,
            target_node_types=(NodeType.INLINE, NodeType.PARAGRAPH),
        )

        # Auto-links
        def auto_extractor(match: re.Match) -> dict[str, str]:
            url = match.group(1)
            return {
                "link_type": "auto",
                "text": url,
                "url": url,
                "is_external": "True",
                "domain": self._extract_domain(url),
            }

        results_auto = _scan_inline_nodes(
            nodes=nodes,
            patterns=[("auto_link", self.AUTO_LINK_RE, auto_extractor)],
            layer_type=LayerType.LINK,
            source_text=source_text,
            target_node_types=(NodeType.INLINE, NodeType.PARAGRAPH),
        )

        # Reference links (Prism regex + native ref_defs parsing)
        results_ref = self._detect_reference_links(nodes, source_text, ref_defs)

        return results_inline + results_auto + results_ref

    def _detect_reference_links(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
        ref_defs: dict[str, str],
    ) -> list[LayerInstance]:
        results: list[LayerInstance] = []
        sibling_idx = [0]

        if not ref_defs:
            return results

        def _scan(node: MarkdownNode, depth: int):
            if node.node_type in (NodeType.INLINE, NodeType.PARAGRAPH):
                base_start = node.char_start if node.char_start is not None else 0

                # [text][ref]
                for match in self.REFERENCE_LINK_RE.finditer(node.raw_content):
                    text = match.group(1)
                    ref_id = match.group(2).lower() if match.group(2) else text.lower()
                    if ref_id in ref_defs:
                        url = ref_defs[ref_id]
                        full = match.group(0)
                        char_start = base_start + match.start()
                        char_end = base_start + match.end()

                        results.append(
                            _build_instance(
                                layer_type=LayerType.LINK,
                                raw_content=full,
                                char_start=char_start,
                                char_end=char_end,
                                source_text=source_text,
                                depth=depth,
                                sibling_index=sibling_idx[0],
                                attributes={
                                    "link_type": "reference",
                                    "text": text,
                                    "url": url,
                                    "is_external": str(url.startswith("http")),
                                    "domain": self._extract_domain(url),
                                    "ref_id": ref_id,
                                },
                            )
                        )
                        sibling_idx[0] += 1

                # [text][] (collapsed reference)
                for match in self._SELF_LINK_RE.finditer(node.raw_content):
                    text = match.group(1)
                    ref_id = text.lower()
                    if ref_id in ref_defs:
                        url = ref_defs[ref_id]
                        full = match.group(0)
                        char_start = base_start + match.start()
                        char_end = base_start + match.end()

                        results.append(
                            _build_instance(
                                layer_type=LayerType.LINK,
                                raw_content=full,
                                char_start=char_start,
                                char_end=char_end,
                                source_text=source_text,
                                depth=depth,
                                sibling_index=sibling_idx[0],
                                attributes={
                                    "link_type": "reference",
                                    "text": text,
                                    "url": url,
                                    "is_external": str(url.startswith("http")),
                                    "domain": self._extract_domain(url),
                                    "ref_id": ref_id,
                                },
                            )
                        )
                        sibling_idx[0] += 1

            for child in node.children:
                _scan(child, depth + 1)

        for node in nodes:
            _scan(node, 0)
        return results

    @staticmethod
    def _extract_domain(url: str) -> str:
        if "://" in url:
            return url.split("://")[1].split("/")[0].split(":")[0]
        return ""


class UnifiedHTMLBlockDetector(HTMLBlockDetector):
    """Compositional: Prism-native HTML block parser + Prism tag extraction.

    Uses a CommonMark-compliant HTML block parser (7 block types) for
    accurate boundary detection (blank-line termination, HTML comments,
    CDATA, processing instructions), then applies Prism logic for
    tag_name, is_semantic, and attributes extraction.
    """

    _SEMANTIC_TAGS = frozenset({
        "div", "section", "article", "aside", "nav",
        "header", "footer", "main", "figure", "figcaption",
        "details", "summary",
    })

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        html_blocks = _find_html_blocks(source_text)
        if not html_blocks:
            return []

        results: list[LayerInstance] = []
        for char_start, char_end, content in html_blocks:
            tag_name = ""
            tag_match = re.match(r"<(/?)(\w+)", content, re.IGNORECASE)
            if tag_match:
                tag_name = tag_match.group(2).lower()

            is_semantic = tag_name in self._SEMANTIC_TAGS

            attrs: dict[str, str] = {
                "tag_name": tag_name,
                "is_semantic": str(is_semantic),
            }
            for attr_match in re.finditer(r'(\w+)=(["\'])(.*?)\2', content):
                attrs[attr_match.group(1)] = attr_match.group(3)

            results.append(
                _build_instance(
                    layer_type=LayerType.HTML_BLOCK,
                    raw_content=content.strip(),
                    char_start=char_start,
                    char_end=char_end,
                    source_text=source_text,
                    depth=0,
                    sibling_index=len(results),
                    attributes=attrs,
                )
            )

        return results


class UnifiedHTMLInlineDetector(HTMLInlineDetector):
    """Compositional: Prism regex scanning + block-tag filtering.

    Detects inline HTML elements via regex on INLINE/PARAGRAPH node content,
    filtering out block-level tags (which belong to HTML_BLOCK).
    """

    HTML_INLINE_RE = re.compile(r"<(\w+)(\s[^>]*)?/?>|</(\w+)>")

    _BLOCK_TAGS = frozenset({
        "div", "section", "article", "aside", "nav",
        "header", "footer", "main", "table", "form",
        "ul", "ol", "li", "p", "blockquote", "pre",
        "details", "summary", "figure", "figcaption",
    })

    _SELF_CLOSING = frozenset({"br", "hr", "img", "input", "meta", "link"})

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        return self._detect_with_regex(nodes, source_text)

    def _detect_with_regex(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        results: list[LayerInstance] = []
        sibling_idx = [0]
        seen_spans: set[tuple[int, int]] = set()

        def _scan(node: MarkdownNode, depth: int):
            if node.node_type in (NodeType.INLINE, NodeType.PARAGRAPH):
                base_start = node.char_start if node.char_start is not None else 0
                for match in self.HTML_INLINE_RE.finditer(node.raw_content):
                    rel_start = match.start()
                    rel_end = match.end()
                    span_key = (base_start + rel_start, base_start + rel_end)
                    if span_key in seen_spans:
                        continue
                    seen_spans.add(span_key)

                    full = match.group(0)
                    tag_name = (match.group(1) or match.group(3) or "").lower()

                    if tag_name in self._BLOCK_TAGS:
                        continue

                    is_self_closing = (
                        full.endswith("/>") or tag_name in self._SELF_CLOSING
                    )

                    attr_str = match.group(2) or ""
                    attrs: dict[str, str] = {
                        "tag_name": tag_name,
                        "is_self_closing": str(is_self_closing),
                    }
                    if attr_str:
                        for attr_match in re.finditer(
                            r'(\w+)=(["\'])(.*?)\2', attr_str
                        ):
                            attrs[attr_match.group(1)] = attr_match.group(3)

                    char_start = base_start + rel_start
                    char_end = base_start + rel_end

                    results.append(
                        _build_instance(
                            layer_type=LayerType.HTML_INLINE,
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
# BATCH 4: Compositional detectors (2) — Prism AST + native indented code
# =============================================================================


class UnifiedCodeBlockDetector(CodeBlockDetector):
    """Compositional: Prism AST fenced code + native indented code parser.

    Fenced code blocks (```) are detected via Prism AST — more accurate
    boundary detection and language extraction.

    Indented code blocks (4 spaces/tabs) are detected via a native
    Prism parser that handles the 4-space/tab indentation rule.

    Diagram languages (mermaid, graphviz, plantuml) are filtered out —
    those belong to DiagramDetector.
    """

    _DIAGRAM_LANGUAGES = frozenset({"mermaid", "graphviz", "plantuml"})

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        # Fenced code via Prism AST
        fenced = self._detect_fenced(nodes, source_text)

        # Indented code via native parser
        indented = self._detect_indented(source_text)

        return fenced + indented

    def _detect_fenced(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.CODE_BLOCK:
                language = node.attributes.get("language", "")
                if language.lower() in self._DIAGRAM_LANGUAGES:
                    return None
                return {"language": language, "code_type": "fenced"}
            return None

        return _walk_ast(nodes, predicate, LayerType.CODE_BLOCK, source_text)

    def _detect_indented(self, source_text: str) -> list[LayerInstance]:
        """Detect indented code blocks (4 spaces or tabs) via native parser."""
        lines = source_text.split("\n")
        n_lines = len(lines)

        # Precompute char offsets
        char_offsets: list[int] = []
        offset = 0
        for line in lines:
            char_offsets.append(offset)
            offset += len(line) + 1

        results: list[LayerInstance] = []
        pos = 0
        while pos < n_lines:
            line = lines[pos]
            if not (line.startswith("    ") or line.startswith("\t")):
                pos += 1
                continue

            # Found indented code block start
            start_pos = pos
            code_lines: list[str] = []
            while pos < n_lines:
                cur = lines[pos]
                if cur.startswith("    "):
                    code_lines.append(cur[4:])
                    pos += 1
                elif cur.startswith("\t"):
                    code_lines.append(cur[1:])
                    pos += 1
                elif not cur.strip():
                    # Blank line may continue or end block
                    # Peek: if next line is also indented, include blank
                    if pos + 1 < n_lines and (
                        lines[pos + 1].startswith("    ")
                        or lines[pos + 1].startswith("\t")
                    ):
                        code_lines.append("")
                        pos += 1
                    else:
                        break
                else:
                    break

            if code_lines:
                # Strip trailing blank lines
                while code_lines and not code_lines[-1].strip():
                    code_lines.pop()

                if code_lines:
                    content = "\n".join(code_lines)
                    char_start = char_offsets[start_pos]
                    char_end = char_start + len(content)

                    results.append(
                        _build_instance(
                            layer_type=LayerType.CODE_BLOCK,
                            raw_content=content,
                            char_start=char_start,
                            char_end=char_end,
                            source_text=source_text,
                            depth=0,
                            sibling_index=len(results),
                            attributes={
                                "language": "",
                                "code_type": "indented",
                            },
                        )
                    )

        return results


class HybridListDetector(ListDetector):
    """Compositional: Prism AST lists + task items detection.

    Detects ordered and unordered lists via Prism AST. Additionally scans
    list items for task list syntax ``- [ ]`` / ``- [x]``.

    If ANY list item has task syntax → the entire list is classified as TASK_LIST.
    Otherwise → classified as LIST.

    This enables Stage 3 to semantically analyze task lists differently
    (action items, completion state, dependencies).
    """

    _TASK_ITEM_RE = re.compile(
        r"^\s*(?:[*\-+]|\d+\.)\s+\[\s*([xX ])\s*\]\s+(.*)$",
        re.MULTILINE,
    )

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.LIST:
                style = node.attributes.get("style", "unordered")
                return {"style": style}
            return None

        results = _walk_ast(nodes, predicate, LayerType.LIST, source_text)

        # Classify each list: TASK_LIST if any task items, else LIST
        classified: list[LayerInstance] = []
        for inst in results:
            raw = inst.raw_content
            task_matches = list(self._TASK_ITEM_RE.finditer(raw))

            if task_matches:
                inst.layer_type = LayerType.TASK_LIST
                inst.attributes["style"] = inst.attributes.get("style", "unordered")
                inst.attributes["task_count"] = str(len(task_matches))
                checked = sum(1 for m in task_matches if m.group(1).lower() == "x")
                inst.attributes["checked_count"] = str(checked)

                task_items_json = self._serialize_task_items(task_matches)
                inst.attributes["task_items"] = task_items_json

            classified.append(inst)

        return classified

    @staticmethod
    def _serialize_task_items(matches: list[re.Match]) -> str:
        """Serialize task items to JSON for downstream parsing."""
        import json

        items = []
        for i, m in enumerate(matches):
            items.append({
                "index": i,
                "checked": m.group(1).lower() == "x",
                "text": m.group(2).strip(),
                "char_start": m.start(),
                "char_end": m.end(),
            })
        return json.dumps(items)


# =============================================================================
# AST-based Horizontal Rule Detector
# =============================================================================


class ASTHRDetector(HRDetector):
    """AST-based implementation: matches NodeType.HR nodes."""

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.HR:
                markup = node.attributes.get("markup", "---")
                if markup.startswith("*"):
                    style = "star"
                elif markup.startswith("_"):
                    style = "underscore"
                else:
                    style = "dash"
                return {"style": style}
            return None

        return _walk_ast(nodes, predicate, LayerType.HORIZONTAL_RULE, source_text)


# =============================================================================
# AST-based Indented Code Block Detector
# =============================================================================


class ASTIndentedCodeBlockDetector(IndentedCodeBlockDetector):
    """AST-based implementation: matches NodeType.INDENTED_CODE_BLOCK nodes."""

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict[str, str]]:
            if node.node_type == NodeType.INDENTED_CODE_BLOCK:
                content = node.raw_content.rstrip("\n")
                line_count = content.count("\n") + 1 if content else 0
                return {"line_count": str(line_count)}
            return None

        return _walk_ast(nodes, predicate, LayerType.INDENTED_CODE_BLOCK, source_text)


# =============================================================================
# Regex-based Footnote Reference Detector
# =============================================================================


class RegexFootnoteRefDetector(FootnoteRefDetector):
    """Regex-based implementation: scans inline nodes for [^id] references."""

    FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\]")

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        return _scan_inline_nodes(
            nodes,
            [
                (
                    "footnote_ref",
                    self.FOOTNOTE_REF_RE,
                    lambda m: {"ref_id": m.group(1)},
                ),
            ],
            LayerType.FOOTNOTE_REF,
            source_text,
            (NodeType.INLINE,),
        )

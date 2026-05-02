"""Concrete layer detectors for Stage 2a (detection phase).

Each detector walks the AST from MarkdownItParser and identifies
LayerInstance objects for its specific layer type.

Detection methods:
- 6 via direct AST node matching (heading, paragraph, table, list, code_block, blockquote)
- 2 via pattern scanning (metadata=front matter, footnote=footnote refs)
- 2 via classifier rules (diagram=mermaid code, figure=images in inline)
"""

import re
from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import LayerInstance, MarkdownNode, NodeType

from prism.stage2.layers.detectors import LayerDetector


class HeadingDetector(LayerDetector):
    """Detect headings from AST heading nodes."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HEADING

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.HEADING:
                level = node.level if node.level is not None else 1
                return {"level": str(level)}
            return None

        return self._walk(nodes, predicate, source_text)


class ParagraphDetector(LayerDetector):
    """Detect paragraphs from AST paragraph nodes."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.PARAGRAPH

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.PARAGRAPH:
                return {}
            return None

        return self._walk(nodes, predicate, source_text)


class TableDetector(LayerDetector):
    """Detect tables from AST table nodes."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.TABLE

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.TABLE:
                return {}
            return None

        return self._walk(nodes, predicate, source_text)


class ListDetector(LayerDetector):
    """Detect lists from AST list nodes (ordered and unordered)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.LIST

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.LIST:
                style = node.attributes.get("style", "unordered")
                return {"style": style}
            return None

        return self._walk(nodes, predicate, source_text)


class CodeBlockDetector(LayerDetector):
    """Detect code blocks from AST fence/code_block nodes."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.CODE_BLOCK

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.CODE_BLOCK:
                language = node.attributes.get("language", "")
                # Don't detect as code_block if it's a mermaid diagram
                if language.lower() in ("mermaid", "graphviz", "plantuml"):
                    return None
                return {"language": language}
            return None

        return self._walk(nodes, predicate, source_text)


class BlockquoteDetector(LayerDetector):
    """Detect blockquotes from AST blockquote nodes."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.BLOCKQUOTE

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.BLOCKQUOTE:
                return {}
            return None

        return self._walk(nodes, predicate, source_text)


class MetadataDetector(LayerDetector):
    """Detect YAML front matter at document start.

    Front matter is delimited by --- markers:
        ---
        title: My Doc
        author: Me
        ---

    The parser may or may not produce a METADATA node depending on
    plugin configuration. This detector handles both cases by scanning
    the raw source text.
    """

    FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    @property
    def layer_type(self) -> LayerType:
        return LayerType.METADATA

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        # Check if parser already detected it as a METADATA node
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.METADATA:
                return {}
            return None

        ast_results = self._walk(nodes, predicate, source_text)
        if ast_results:
            return ast_results

        # Fall back to raw text scanning
        match = self.FRONT_MATTER_RE.match(source_text)
        if match:
            content = match.group(0)
            return [
                LayerInstance(
                    layer_type=self.layer_type,
                    char_start=0,
                    char_end=len(content),
                    line_start=0,
                    line_end=content.count("\n"),
                    raw_content=content.strip(),
                    depth=0,
                    sibling_index=0,
                )
            ]

        return []


class FootnoteDetector(LayerDetector):
    """Detect footnote definitions in source text.

    Footnote definitions follow the pattern:
        [^label]: Footnote text

    The parser may or may not produce footnote nodes depending on
    plugin configuration. This detector scans raw text as fallback.
    """

    FOOTNOTE_DEF_RE = re.compile(
        r"^\[\^([^\]]+)\]:\s*(.+)$",
        re.MULTILINE,
    )

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FOOTNOTE

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        # Check if parser already detected footnote nodes
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.FOOTNOTE:
                label = node.attributes.get("label", "")
                return {"label": label}
            return None

        ast_results = self._walk(nodes, predicate, source_text)
        if ast_results:
            return ast_results

        # Fall back to raw text scanning
        results: list[LayerInstance] = []
        lines = source_text.split("\n")
        for match in self.FOOTNOTE_DEF_RE.finditer(source_text):
            label = match.group(1)
            content = match.group(0)
            char_start = match.start()
            char_end = match.end()
            line_start = source_text[:char_start].count("\n")
            line_end = source_text[:char_end].count("\n") + 1

            results.append(
                LayerInstance(
                    layer_type=self.layer_type,
                    char_start=char_start,
                    char_end=char_end,
                    line_start=line_start,
                    line_end=line_end,
                    raw_content=content.strip(),
                    depth=0,
                    sibling_index=len(results),
                    attributes={"label": label},
                )
            )

        return results


class DiagramDetector(LayerDetector):
    """Detect diagrams in code blocks (mermaid, graphviz, plantuml).

    Diagrams are code blocks with specific language identifiers.
    """

    DIAGRAM_LANGUAGES = {"mermaid", "graphviz", "plantuml", "dot"}

    @property
    def layer_type(self) -> LayerType:
        return LayerType.DIAGRAM

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        def predicate(node: MarkdownNode) -> Optional[dict]:
            if node.node_type == NodeType.CODE_BLOCK:
                language = node.attributes.get("language", "").lower()
                if language in self.DIAGRAM_LANGUAGES:
                    return {"diagram_type": language}
                # Also check content for mermaid-like syntax
                if not language and _looks_like_diagram(node.raw_content):
                    return {"diagram_type": "mermaid"}
            return None

        return self._walk(nodes, predicate, source_text)


class FigureDetector(LayerDetector):
    """Detect figures/images in paragraph inline content.

    Figures are Markdown image syntax: ![alt](src)
    They typically appear within paragraphs as inline elements.
    """

    IMAGE_RE = re.compile(
        r"!\[([^\]]*)\]\(([^)]+)\)",
    )

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FIGURE

    def detect(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> list[LayerInstance]:
        results: list[LayerInstance] = []

        def _scan_node(node: MarkdownNode, depth: int, sibling_idx: list[int]):
            # Check inline nodes for image patterns
            if node.node_type == NodeType.INLINE:
                for match in self.IMAGE_RE.finditer(node.raw_content):
                    caption = match.group(1)
                    src = match.group(2)
                    full = match.group(0)

                    # Compute relative char offset within the inline content
                    rel_start = match.start()
                    rel_end = match.end()

                    # Compute absolute char offsets
                    base_start = node.char_start if node.char_start is not None else 0
                    char_start = base_start + rel_start
                    char_end = base_start + rel_end

                    lines = source_text.split("\n")
                    line_start = _line_number_at(char_start, source_text)
                    line_end = _line_number_at(char_end - 1, source_text) + 1

                    results.append(
                        LayerInstance(
                            layer_type=self.layer_type,
                            char_start=char_start,
                            char_end=char_end,
                            line_start=line_start,
                            line_end=line_end,
                            raw_content=full,
                            depth=depth,
                            sibling_index=sibling_idx[0],
                            attributes={"caption": caption, "src": src},
                        )
                    )
                    sibling_idx[0] += 1

            # Recurse
            for child in node.children:
                _scan_node(child, depth + 1, sibling_idx)

        sibling_idx = [0]
        for node in nodes:
            _scan_node(node, 0, sibling_idx)

        return results


def _looks_like_diagram(content: str) -> bool:
    """Heuristic: check if code block content looks like a diagram."""
    first_line = content.strip().split("\n")[0].lower()
    diagram_keywords = [
        "graph ", "digraph ", "flowchart ", "sequenceDiagram",
        "gantt", "pie ", "classDiagram", "stateDiagram",
        "erDiagram", "journey", "gitGraph",
    ]
    return any(first_line.startswith(kw) for kw in diagram_keywords)


def _line_number_at(char_offset: int, source_text: str) -> int:
    """Compute 0-indexed line number at a character offset."""
    return source_text[:char_offset].count("\n")

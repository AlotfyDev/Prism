"""Base class and utilities for layer detectors."""

from abc import ABC, abstractmethod
from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import LayerInstance, MarkdownNode, NodeType


def _line_to_char_offset(line_number: int, lines: list[str]) -> int:
    """Convert line number to character offset in source text."""
    offset = 0
    for i in range(line_number):
        offset += len(lines[i]) + 1  # +1 for newline
    return offset


def _compute_line_number(char_offset: int, lines: list[str]) -> int:
    """Convert character offset to 0-indexed line number."""
    offset = 0
    for i, line in enumerate(lines):
        if offset + len(line) >= char_offset:
            return i
        offset += len(line) + 1
    return len(lines) - 1


class LayerDetector(ABC):
    """Abstract base for all layer detectors.

    Detectors walk the AST produced by MarkdownItParser and identify
    LayerInstance objects for their specific layer type. Each detector
    handles one LayerType.

    Detection happens in Stage 2a (detection phase), producing a
    DetectedLayersReport consumed by Stage 2b (classification phase).
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
        """Detect layer instances in the AST.

        Args:
            nodes: Root-level MarkdownNode objects from the parser.
            source_text: Original Markdown source for char offset computation.

        Returns:
            List of LayerInstance objects for this detector's layer type.
        """

    def _walk(
        self,
        nodes: list[MarkdownNode],
        predicate,
        source_text: str,
        depth: int = 0,
        sibling_offset: dict[int, int] = None,
    ) -> list[LayerInstance]:
        """Walk AST tree, applying predicate to each node.

        Args:
            nodes: Current level of nodes to scan.
            predicate: Callable(MarkdownNode) -> Optional[dict].
                Returns attribute dict if node matches, None otherwise.
            source_text: Original Markdown source.
            depth: Current nesting depth.
            sibling_offset: Tracker for sibling indices at each depth.

        Returns:
            List of LayerInstance objects for matching nodes.
        """
        if sibling_offset is None:
            sibling_offset = {}

        results: list[LayerInstance] = []
        lines = source_text.split("\n")

        # Track sibling index for this depth level
        if depth not in sibling_offset:
            sibling_offset[depth] = 0

        for node in nodes:
            attrs = predicate(node)
            if attrs is not None:
                char_start = node.char_start if node.char_start is not None else 0
                char_end = node.char_end if node.char_end is not None else char_start + 1
                line_start = _compute_line_number(char_start, lines)
                line_end = _compute_line_number(min(char_end - 1, len(source_text) - 1), lines)

                instance = LayerInstance(
                    layer_type=self.layer_type,
                    char_start=char_start,
                    char_end=char_end,
                    line_start=line_start,
                    line_end=line_end + 1 if line_end >= line_start else line_start + 1,
                    raw_content=node.raw_content,
                    depth=depth,
                    sibling_index=sibling_offset[depth],
                    attributes=attrs,
                )
                results.append(instance)
                sibling_offset[depth] += 1

            # Recurse into children
            if node.children:
                child_depth = depth + 1
                child_sib = dict(sibling_offset)
                results.extend(
                    self._walk(
                        node.children,
                        predicate,
                        source_text,
                        depth=child_depth,
                        sibling_offset=child_sib,
                    )
                )

        return results

"""Code Block Aggregator — Structured code block index with line numbers.

Parses fence tokens, extracts language, counts lines, detects syntax markers.
Reliability: 100% — fence tokens are explicit.
"""

from __future__ import annotations

from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.aggregation.aggregation_models import CodeBlockIndex, CodeLine


class CodeBlockAggregator:
    """Builds structured code block index from markdown-it-py AST nodes."""

    # ------------------------------------------------------------------
    # IAggregator Protocol
    # ------------------------------------------------------------------

    def aggregate(self, input_data: list[MarkdownNode]) -> list[CodeBlockIndex]:
        return self._parse_codeblocks(input_data)

    def validate_input(self, input_data: list[MarkdownNode]) -> tuple[bool, str]:
        if not isinstance(input_data, list):
            return False, "Input must be a list of MarkdownNode"
        return True, ""

    def validate_output(self, output_data: list[CodeBlockIndex]) -> tuple[bool, str]:
        for cb in output_data:
            if not cb.component_id:
                return False, "CodeBlockIndex must have component_id"
            if cb.total_lines < 0:
                return False, "total_lines must be >= 0"
        return True, ""

    def name(self) -> str:
        return "CodeBlockAggregator"

    @property
    def tier(self) -> str:
        return "rules"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    def _parse_codeblocks(self, nodes: list[MarkdownNode]) -> list[CodeBlockIndex]:
        """Extract code block indices from AST nodes."""
        results = []
        for node in nodes:
            if node.node_type == NodeType.CODE_BLOCK:
                code_index = self._parse_single_codeblock(node)
                results.append(code_index)
            # Recurse into children
            if node.children:
                results.extend(self._parse_codeblocks(node.children))
        return results

    def _parse_single_codeblock(self, node: MarkdownNode) -> CodeBlockIndex:
        """Parse a single code block node into CodeBlockIndex."""
        # Extract language from attributes or info string
        language = node.attributes.get("language", "")
        if not language:
            language = self._detect_language(node.raw_content)

        # Split into lines
        raw = node.raw_content
        # Remove fence markers (```)
        lines = self._extract_content_lines(raw)

        code_lines = []
        indentation_pattern = []
        non_empty_count = 0
        has_syntax_markers = False

        for i, line in enumerate(lines):
            is_empty = not line.strip()
            if not is_empty:
                non_empty_count += 1

            indent = self._count_leading_whitespace(line)
            indentation_pattern.append(indent)

            code_line = CodeLine(
                line_number=i,
                content=line,
                is_empty=is_empty,
                indentation=indent,
            )
            code_lines.append(code_line)

            # Detect syntax markers (line numbers like "1 | ...")
            if self._has_line_number(line):
                has_syntax_markers = True

        return CodeBlockIndex(
            component_id=node.attributes.get("component_id", f"codeblock:{id(node)}"),
            language=language,
            total_lines=len(lines),
            non_empty_lines=non_empty_count,
            lines=code_lines,
            indentation_pattern=indentation_pattern,
            has_syntax_markers=has_syntax_markers,
        )

    def _extract_content_lines(self, raw: str) -> list[str]:
        """Extract code content lines, removing fence markers."""
        lines = raw.split("\n")
        # Remove opening fence (```python, etc.)
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Remove closing fence (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return lines

    def _detect_language(self, raw: str) -> str:
        """Detect language from fence info string."""
        first_line = raw.split("\n")[0].strip()
        if first_line.startswith("```"):
            parts = first_line[3:].strip().split()
            if parts:
                return parts[0]
        return ""

    def _count_leading_whitespace(self, line: str) -> int:
        """Count leading spaces/tabs in a line."""
        count = 0
        for ch in line:
            if ch in (" ", "\t"):
                count += 1
            else:
                break
        return count

    def _has_line_number(self, line: str) -> bool:
        """Check if line has syntax markers (e.g., '1 | code')."""
        import re
        return bool(re.match(r"^\s*\d+\s*[|:]\s", line))

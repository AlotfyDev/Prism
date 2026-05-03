"""Table Aggregator — Structured table index from markdown-it-py AST.

Builds table matrix, header detection, cell metadata from AST nodes.
Reliability: 100% — AST tokens are explicit.
"""

from __future__ import annotations

from typing import Any

from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.aggregation.aggregation_models import TableIndex


class TableAggregator:
    """Builds structured table index from markdown-it-py AST nodes."""

    # ------------------------------------------------------------------
    # IAggregator Protocol
    # ------------------------------------------------------------------

    def aggregate(self, input_data: list[MarkdownNode]) -> list[TableIndex]:
        return self._parse_tables(input_data)

    def validate_input(self, input_data: list[MarkdownNode]) -> tuple[bool, str]:
        if not isinstance(input_data, list):
            return False, "Input must be a list of MarkdownNode"
        return True, ""

    def validate_output(self, output_data: list[TableIndex]) -> tuple[bool, str]:
        for idx in output_data:
            if not idx.component_id:
                return False, "TableIndex must have component_id"
            if idx.dimensions[0] < 0 or idx.dimensions[1] < 0:
                return False, "Table dimensions must be non-negative"
        return True, ""

    def name(self) -> str:
        return "TableAggregator"

    @property
    def tier(self) -> str:
        return "rules"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    def _parse_tables(self, nodes: list[MarkdownNode]) -> list[TableIndex]:
        """Extract table indices from AST nodes."""
        results = []
        for node in nodes:
            if node.node_type == NodeType.TABLE:
                table_index = self._parse_single_table(node)
                results.append(table_index)
            # Recurse into children
            if node.children:
                results.extend(self._parse_tables(node.children))
        return results

    def _parse_single_table(self, table_node: MarkdownNode) -> TableIndex:
        """Parse a single table node into TableIndex."""
        rows = []
        header_cells = []
        cell_matrix = []
        has_header = False

        # Walk through table children to find rows
        for child in table_node.children:
            if child.node_type == NodeType.PARAGRAPH:
                row_text = child.raw_content.strip()
                if "|" in row_text:
                    cells = self._parse_row_cells(row_text, child)
                    rows.append(cells)

        # Detect header: first row with separator below
        if len(rows) >= 2:
            second_row = rows[1]
            if self._is_separator_row(second_row):
                has_header = True
                header_cells = [c.get("text", "") for c in rows[0]]
                cell_matrix = [
                    row for i, row in enumerate(rows) if i > 1
                ]
            else:
                cell_matrix = rows
        elif rows:
            cell_matrix = rows

        # If no rows found via children, parse from raw content
        if not cell_matrix and not header_cells:
            header_cells, cell_matrix = self._parse_raw_table(table_node.raw_content)
            has_header = len(header_cells) > 0

        dimensions = (len(cell_matrix), len(cell_matrix[0]) if cell_matrix else 0)

        return TableIndex(
            component_id=table_node.attributes.get("component_id", f"table:{id(table_node)}"),
            dimensions=dimensions,
            has_header=has_header,
            header_cells=header_cells,
            cell_matrix=self._build_cell_matrix(cell_matrix),
            raw_markdown=table_node.raw_content,
        )

    def _parse_row_cells(self, row_text: str, node: MarkdownNode) -> list[dict[str, Any]]:
        """Parse a table row into cell metadata."""
        # Remove leading/trailing pipes
        cells_text = row_text.strip().strip("|")
        cells = []
        for cell_text in cells_text.split("|"):
            cells.append({
                "text": cell_text.strip(),
                "char_start": node.char_start or 0,
                "char_end": (node.char_start or 0) + len(node.raw_content),
            })
        return cells

    def _is_separator_row(self, row: list[dict]) -> bool:
        """Check if a row is a table separator (---|---|---)."""
        if not row:
            return False
        for cell in row:
            text = cell.get("text", "").strip()
            if not text or not all(c in "-: " for c in text):
                return False
        return True

    def _parse_raw_table(self, raw_content: str) -> tuple[list[str], list[list[dict]]]:
        """Parse raw table markdown into header and cell matrix."""
        lines = raw_content.strip().split("\n")
        if not lines:
            return [], []

        header_cells = []
        cell_matrix = []
        has_separator = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if "|" not in line_stripped:
                continue

            cells_text = line_stripped.strip("|").split("|")
            cells = [{"text": c.strip()} for c in cells_text]

            if self._is_separator_row_raw(line_stripped):
                has_separator = True
                continue

            if i == 0:
                # First non-separator row: could be header
                # Check if next non-empty line is a separator
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if "|" not in next_line:
                        continue
                    if self._is_separator_row_raw(next_line):
                        header_cells = [c["text"] for c in cells]
                        has_separator = True
                        break
                    else:
                        # Next row is data, so first row is also data
                        break

            if not has_separator or i > 0:
                cell_matrix.append(cells)

        if has_separator and header_cells:
            # Header was detected, cell_matrix should only have data rows
            # (header row was already added to cell_matrix before we knew it was header)
            # Remove it if it's the first row
            if cell_matrix and len(cell_matrix) > 0:
                # The first row is the header data, but we want it separate
                # Check if first row matches header cells
                first_row_texts = [c.get("text", "") for c in cell_matrix[0]]
                if first_row_texts == header_cells:
                    cell_matrix = cell_matrix[1:]

        return header_cells, cell_matrix

    def _is_separator_row_raw(self, line: str) -> bool:
        """Check if raw line is a table separator."""
        line = line.strip().strip("|")
        parts = line.split("|")
        if not parts:
            return False
        for part in parts:
            text = part.strip()
            if not text or not all(c in "-: " for c in text):
                return False
        return True

    def _build_cell_matrix(self, rows: list[list[dict]]) -> list[list[dict[str, Any]]]:
        """Normalize cell matrix with consistent dimensions."""
        if not rows:
            return []
        max_cols = max(len(row) for row in rows)
        matrix = []
        for row in rows:
            normalized = []
            for i in range(max_cols):
                if i < len(row):
                    normalized.append(row[i])
                else:
                    normalized.append({"text": "", "char_start": None, "char_end": None})
            matrix.append(normalized)
        return matrix

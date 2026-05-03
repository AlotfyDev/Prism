"""Tests for nested object schemas (Table, List, Cell, Item)."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    CellPosition,
    ListComponent,
    ListItem,
    ListStyle,
    NestingMatrix,
    PhysicalComponent,
    TableComponent,
    TableCell,
    TableRow,
)


# =============================================================================
# CellPosition Tests
# =============================================================================


class TestCellPosition:
    def test_valid_position(self):
        pos = CellPosition(row=0, col=2)
        assert pos.row == 0
        assert pos.col == 2
        assert pos.is_header is False

    def test_valid_header_position(self):
        pos = CellPosition(row=0, col=0, is_header=True)
        assert pos.is_header is True

    def test_negative_row_rejected(self):
        with pytest.raises(ValidationError):
            CellPosition(row=-1, col=0)

    def test_negative_col_rejected(self):
        with pytest.raises(ValidationError):
            CellPosition(row=0, col=-1)


# =============================================================================
# ListItem Tests
# =============================================================================


class TestListItem:
    def test_valid_minimal_item(self):
        item = ListItem(item_index=0)
        assert item.item_index == 0
        assert item.children == []
        assert item.char_start is None

    def test_valid_item_with_children(self):
        item = ListItem(
            item_index=2,
            children=["paragraph:p1", "list:l2"],
            char_start=100,
            char_end=250,
        )
        assert len(item.children) == 2
        assert item.char_start == 100
        assert item.char_end == 250

    def test_negative_index_rejected(self):
        with pytest.raises(ValidationError):
            ListItem(item_index=-1)


# =============================================================================
# TableCell Tests
# =============================================================================


class TestTableCell:
    def test_valid_minimal_cell(self):
        cell = TableCell(position=CellPosition(row=1, col=0))
        assert cell.position.row == 1
        assert cell.position.col == 0
        assert cell.children == []

    def test_valid_cell_with_children(self):
        cell = TableCell(
            position=CellPosition(row=0, col=1, is_header=True),
            children=["paragraph:p1", "figure:f1"],
        )
        assert len(cell.children) == 2
        assert cell.position.is_header is True

    def test_cell_can_hold_multiple_child_types(self):
        cell = TableCell(
            position=CellPosition(row=2, col=3),
            children=[
                "paragraph:p1",
                "list:l1",
                "code_block:c1",
                "figure:f1",
                "table:tbl2",
                "blockquote:bq1",
                "diagram:d1",
                "heading:h1",
            ],
        )
        assert len(cell.children) == 8


# =============================================================================
# TableRow Tests
# =============================================================================


class TestTableRow:
    def test_valid_row(self):
        row = TableRow(
            row_index=0,
            cells=[
                TableCell(position=CellPosition(row=0, col=0)),
                TableCell(position=CellPosition(row=0, col=1)),
            ],
        )
        assert len(row.cells) == 2

    def test_empty_row_valid(self):
        row = TableRow(row_index=0)
        assert row.cells == []

    def test_negative_row_index_rejected(self):
        with pytest.raises(ValidationError):
            TableRow(row_index=-1)


# =============================================================================
# TableComponent Tests
# =============================================================================


class TestTableComponent:
    def _make_table(self, rows, num_cols=0, has_header=False):
        return TableComponent(
            component_id="table:tbl1",
            layer_type=LayerType.TABLE,
            raw_content="| A | B |\n|---|---|\n| 1 | 2 |",
            char_start=0,
            char_end=29,
            rows=rows,
            num_cols=num_cols,
            has_header=has_header,
        )

    def test_valid_empty_table(self):
        tbl = self._make_table(rows=[])
        assert tbl.rows == []
        assert tbl.num_cols == 0
        assert tbl.has_header is False

    def test_valid_single_cell_table(self):
        tbl = self._make_table(
            rows=[
                TableRow(
                    row_index=0,
                    cells=[TableCell(position=CellPosition(row=0, col=0))],
                )
            ],
        )
        assert tbl.num_cols == 1
        assert len(tbl.rows) == 1

    def test_valid_multi_row_table(self):
        tbl = self._make_table(
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
        assert tbl.num_cols == 2
        assert tbl.has_header is True
        assert len(tbl.rows) == 2

    def test_auto_detect_num_cols(self):
        tbl = self._make_table(
            rows=[
                TableRow(
                    row_index=0,
                    cells=[
                        TableCell(position=CellPosition(row=0, col=0)),
                        TableCell(position=CellPosition(row=0, col=1)),
                        TableCell(position=CellPosition(row=0, col=2)),
                    ],
                )
            ],
        )
        assert tbl.num_cols == 3

    def test_inconsistent_row_column_count_rejected(self):
        with pytest.raises(ValidationError, match="row 1 has 1 cells, expected 2"):
            self._make_table(
                rows=[
                    TableRow(
                        row_index=0,
                        cells=[
                            TableCell(position=CellPosition(row=0, col=0)),
                            TableCell(position=CellPosition(row=0, col=1)),
                        ],
                    ),
                    TableRow(
                        row_index=1,
                        cells=[
                            TableCell(position=CellPosition(row=1, col=0)),
                        ],
                    ),
                ],
                num_cols=2,
            )

    def test_cell_row_position_mismatch_rejected(self):
        with pytest.raises(ValidationError, match="row mismatch"):
            self._make_table(
                rows=[
                    TableRow(
                        row_index=0,
                        cells=[
                            TableCell(position=CellPosition(row=1, col=0)),
                        ],
                    ),
                ],
            )

    def test_cell_col_position_mismatch_rejected(self):
        with pytest.raises(ValidationError, match="expected 1"):
            self._make_table(
                rows=[
                    TableRow(
                        row_index=0,
                        cells=[
                            TableCell(position=CellPosition(row=0, col=0)),
                            TableCell(position=CellPosition(row=0, col=2)),
                        ],
                    ),
                ],
            )

    def test_header_flag_mismatch_rejected(self):
        with pytest.raises(ValidationError, match="is_header"):
            self._make_table(
                rows=[
                    TableRow(
                        row_index=0,
                        cells=[
                            TableCell(position=CellPosition(row=0, col=0, is_header=False)),
                        ],
                    ),
                ],
                has_header=True,
            )

    def test_table_component_inherits_physical_component_fields(self):
        tbl = self._make_table(rows=[])
        assert tbl.component_id == "table:tbl1"
        assert tbl.layer_type == LayerType.TABLE
        assert tbl.token_span is None
        assert tbl.parent_id is None
        assert tbl.children == []

    def test_table_with_children_and_rows(self):
        tbl = TableComponent(
            component_id="table:tbl1",
            layer_type=LayerType.TABLE,
            raw_content="| A | B |\n| 1 | 2 |",
            char_start=0,
            char_end=21,
            children=["paragraph:p1", "paragraph:p2"],
            rows=[
                TableRow(
                    row_index=0,
                    cells=[
                        TableCell(
                            position=CellPosition(row=0, col=0),
                            children=["paragraph:p1"],
                        ),
                        TableCell(
                            position=CellPosition(row=0, col=1),
                            children=["paragraph:p2"],
                        ),
                    ],
                ),
            ],
        )
        # Flat children
        assert len(tbl.children) == 2
        # Structured children
        assert len(tbl.rows[0].cells[0].children) == 1
        assert len(tbl.rows[0].cells[1].children) == 1


# =============================================================================
# ListComponent Tests
# =============================================================================


class TestListComponent:
    def _make_list(self, items, style=ListStyle.UNORDERED):
        return ListComponent(
            component_id="list:l1",
            layer_type=LayerType.LIST,
            raw_content="- Item 1\n- Item 2",
            char_start=0,
            char_end=17,
            items=items,
            style=style,
        )

    def test_valid_empty_list(self):
        lst = self._make_list(items=[])
        assert lst.items == []
        assert lst.style == ListStyle.UNORDERED

    def test_valid_ordered_list(self):
        lst = self._make_list(
            items=[
                ListItem(item_index=0, children=["paragraph:p1"]),
                ListItem(item_index=1, children=["paragraph:p2"]),
            ],
            style=ListStyle.ORDERED,
        )
        assert lst.style == ListStyle.ORDERED
        assert len(lst.items) == 2

    def test_valid_unordered_list(self):
        lst = self._make_list(
            items=[
                ListItem(item_index=0),
                ListItem(item_index=1),
                ListItem(item_index=2),
            ],
            style=ListStyle.UNORDERED,
        )
        assert lst.style == ListStyle.UNORDERED
        assert len(lst.items) == 3

    def test_non_sequential_item_index_rejected(self):
        with pytest.raises(ValidationError, match="expected 1"):
            self._make_list(
                items=[
                    ListItem(item_index=0),
                    ListItem(item_index=5),
                ],
            )

    def test_list_component_inherits_physical_component_fields(self):
        lst = self._make_list(items=[])
        assert lst.component_id == "list:l1"
        assert lst.layer_type == LayerType.LIST
        assert lst.token_span is None

    def test_list_with_nested_sublist(self):
        lst = ListComponent(
            component_id="list:l1",
            layer_type=LayerType.LIST,
            raw_content="- Item 1\n  - Sub 1\n  - Sub 2",
            char_start=0,
            char_end=29,
            items=[
                ListItem(
                    item_index=0,
                    children=["paragraph:p1", "list:l2"],
                ),
                ListItem(
                    item_index=1,
                    children=["paragraph:p2"],
                ),
            ],
        )
        assert len(lst.items[0].children) == 2
        assert "list:l2" in lst.items[0].children


# =============================================================================
# NestingMatrix Updated Rules Tests
# =============================================================================


class TestNestingMatrixTableAndListRules:
    def test_table_can_contain_all_layer_types(self):
        matrix = NestingMatrix.default()
        expected_children = {
            LayerType.PARAGRAPH,
            LayerType.LIST,
            LayerType.TABLE,
            LayerType.CODE_BLOCK,
            LayerType.BLOCKQUOTE,
            LayerType.FIGURE,
            LayerType.DIAGRAM,
            LayerType.HEADING,
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        }
        actual = matrix.get_valid_children(LayerType.TABLE)
        assert actual == expected_children

    def test_table_can_contain_paragraph_in_cell(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.PARAGRAPH)

    def test_table_can_contain_list_in_cell(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.LIST)

    def test_table_can_contain_code_block_in_cell(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.CODE_BLOCK)

    def test_table_can_contain_nested_table_in_cell(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.TABLE)

    def test_table_can_contain_blockquote_in_cell(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.BLOCKQUOTE)

    def test_table_can_contain_heading_in_cell(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.HEADING)

    def test_list_can_contain_all_layer_types(self):
        matrix = NestingMatrix.default()
        expected_children = {
            LayerType.PARAGRAPH,
            LayerType.LIST,
            LayerType.TABLE,
            LayerType.CODE_BLOCK,
            LayerType.BLOCKQUOTE,
            LayerType.FIGURE,
            LayerType.DIAGRAM,
            LayerType.HEADING,
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        }
        actual = matrix.get_valid_children(LayerType.LIST)
        assert actual == expected_children

    def test_list_can_contain_paragraph_in_item(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.LIST, LayerType.PARAGRAPH)

    def test_list_can_contain_table_in_item(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.LIST, LayerType.TABLE)

    def test_list_can_contain_blockquote_in_item(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.LIST, LayerType.BLOCKQUOTE)

    def test_list_can_contain_heading_in_item(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.LIST, LayerType.HEADING)

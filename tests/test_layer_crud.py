"""Tests for P2.2a: CRUD operations for all layer types."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    PhysicalComponent,
    TableComponent,
    ListComponent,
    ListStyle,
)

from prism.stage2.layers.base import LayerCRUD, LayerRegistry
from prism.stage2.layers.table import TableCRUD
from prism.stage2.layers.list import ListCRUD
from prism.stage2.layers.simple_layers import (
    HeadingCRUD,
    ParagraphCRUD,
    CodeBlockCRUD,
    BlockquoteCRUD,
    FootnoteCRUD,
    MetadataCRUD,
    FigureCRUD,
    DiagramCRUD,
)
from prism.stage2.layers import get_crud


# =============================================================================
# LayerRegistry Tests
# =============================================================================


class TestLayerRegistry:
    def test_all_types_registered(self):
        for lt in LayerType:
            assert LayerRegistry.has(lt), f"{lt.value} not registered"

    def test_all_types_retrievable(self):
        for lt in LayerType:
            crud = LayerRegistry.get(lt)
            assert crud.layer_type == lt

    def test_get_crud_convenience(self):
        assert get_crud(LayerType.TABLE).layer_type == LayerType.TABLE
        assert get_crud(LayerType.HEADING).layer_type == LayerType.HEADING

    def test_missing_type_raises_keyerror(self):
        saved = dict(LayerRegistry._registry)
        LayerRegistry.clear()
        try:
            with pytest.raises(KeyError):
                LayerRegistry.get(LayerType.TABLE)
        finally:
            LayerRegistry._registry.update(saved)

    def test_all_types_count(self):
        assert len(LayerRegistry.all_types()) == len(LayerType)


# =============================================================================
# Base LayerCRUD Tests
# =============================================================================


class TestBaseLayerCRUD:
    def _make_component(self):
        return PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world",
        )

    def test_add_child_valid(self):
        crud = ParagraphCRUD()
        parent = self._make_component()
        crud.add_child(parent, "figure:f1", LayerType.FIGURE)
        assert "figure:f1" in parent.children

    def test_add_child_invalid_type(self):
        crud = ParagraphCRUD()
        parent = self._make_component()
        with pytest.raises(ValueError, match="cannot contain"):
            crud.add_child(parent, "list:l1", LayerType.LIST)

    def test_add_child_duplicate(self):
        crud = ParagraphCRUD()
        parent = self._make_component()
        crud.add_child(parent, "figure:f1", LayerType.FIGURE)
        with pytest.raises(ValueError, match="already exists"):
            crud.add_child(parent, "figure:f1", LayerType.FIGURE)

    def test_remove_child_valid(self):
        crud = ParagraphCRUD()
        parent = self._make_component()
        crud.add_child(parent, "figure:f1", LayerType.FIGURE)
        crud.remove_child(parent, "figure:f1")
        assert "figure:f1" not in parent.children

    def test_remove_child_not_found(self):
        crud = ParagraphCRUD()
        parent = self._make_component()
        with pytest.raises(ValueError, match="not found"):
            crud.remove_child(parent, "nonexistent")

    def test_get_children(self):
        crud = ParagraphCRUD()
        parent = self._make_component()
        crud.add_child(parent, "figure:f1", LayerType.FIGURE)
        children = crud.get_children(parent)
        assert children == ["figure:f1"]

    def test_set_parent(self):
        crud = ParagraphCRUD()
        comp = self._make_component()
        crud.set_parent(comp, "heading:h1")
        assert comp.parent_id == "heading:h1"

    def test_set_token_span_valid(self):
        crud = ParagraphCRUD()
        comp = self._make_component()
        crud.set_token_span(comp, 5, 20)
        assert comp.token_span == (5, 20)

    def test_set_token_span_invalid(self):
        crud = ParagraphCRUD()
        comp = self._make_component()
        with pytest.raises(ValueError, match="must be >="):
            crud.set_token_span(comp, 20, 5)

    def test_get_token_span(self):
        crud = ParagraphCRUD()
        comp = self._make_component()
        comp.token_span = (10, 30)
        assert crud.get_token_span(comp) == (10, 30)

    def test_get_token_span_unset(self):
        crud = ParagraphCRUD()
        comp = self._make_component()
        assert crud.get_token_span(comp) is None


# =============================================================================
# HeadingCRUD Tests
# =============================================================================


class TestHeadingCRUD:
    def test_create_default_level(self):
        crud = HeadingCRUD()
        h = crud.create("h1", "# Title")
        assert h.component_id == "heading:h1"
        assert crud.get_level(h) == 1

    def test_create_with_level(self):
        crud = HeadingCRUD()
        h = crud.create("h2", "## Subtitle", level=2)
        assert crud.get_level(h) == 2

    def test_set_level_valid(self):
        crud = HeadingCRUD()
        h = crud.create("h1", "# Title")
        crud.set_level(h, 3)
        assert crud.get_level(h) == 3

    def test_set_level_invalid(self):
        crud = HeadingCRUD()
        h = crud.create("h1", "# Title")
        with pytest.raises(ValueError, match="must be 1-6"):
            crud.set_level(h, 7)

    def test_add_child_valid(self):
        crud = HeadingCRUD()
        h = crud.create("h1", "# Title")
        crud.add_child(h, "paragraph:p1", LayerType.PARAGRAPH)
        assert "paragraph:p1" in h.children

    def test_heading_cannot_contain_heading(self):
        crud = HeadingCRUD()
        h = crud.create("h1", "# Title")
        with pytest.raises(ValueError):
            crud.add_child(h, "heading:h2", LayerType.HEADING)


# =============================================================================
# ParagraphCRUD Tests
# =============================================================================


class TestParagraphCRUD:
    def test_create(self):
        crud = ParagraphCRUD()
        p = crud.create("p1", "Some text")
        assert p.component_id == "paragraph:p1"
        assert p.raw_content == "Some text"

    def test_only_allows_figure_child(self):
        crud = ParagraphCRUD()
        p = crud.create("p1", "Text with ![img](url)")
        crud.add_child(p, "figure:f1", LayerType.FIGURE)
        with pytest.raises(ValueError):
            crud.add_child(p, "paragraph:p2", LayerType.PARAGRAPH)


# =============================================================================
# CodeBlockCRUD Tests
# =============================================================================


class TestCodeBlockCRUD:
    def test_create_without_language(self):
        crud = CodeBlockCRUD()
        c = crud.create("c1", "print('hi')")
        assert c.component_id == "code_block:c1"
        assert crud.get_language(c) == ""

    def test_create_with_language(self):
        crud = CodeBlockCRUD()
        c = crud.create("c2", "def foo(): pass", language="python")
        assert crud.get_language(c) == "python"

    def test_set_language(self):
        crud = CodeBlockCRUD()
        c = crud.create("c1", "code")
        crud.set_language(c, "rust")
        assert crud.get_language(c) == "rust"

    def test_leaf_cannot_have_children(self):
        crud = CodeBlockCRUD()
        c = crud.create("c1", "code")
        with pytest.raises(ValueError):
            crud.add_child(c, "paragraph:p1", LayerType.PARAGRAPH)


# =============================================================================
# BlockquoteCRUD Tests
# =============================================================================


class TestBlockquoteCRUD:
    def test_create_default_style(self):
        crud = BlockquoteCRUD()
        b = crud.create("bq1", "> Quoted text")
        assert crud.get_style(b) == "blockquote"

    def test_create_custom_style(self):
        crud = BlockquoteCRUD()
        b = crud.create("bq2", "> Note: important", style="note")
        assert crud.get_style(b) == "note"

    def test_can_contain_paragraph(self):
        crud = BlockquoteCRUD()
        b = crud.create("bq1", "> Text")
        crud.add_child(b, "paragraph:p1", LayerType.PARAGRAPH)
        assert "paragraph:p1" in b.children

    def test_recursive_nesting(self):
        crud = BlockquoteCRUD()
        b = crud.create("bq1", "> Outer")
        crud.add_child(b, "blockquote:bq2", LayerType.BLOCKQUOTE)
        assert "blockquote:bq2" in b.children


# =============================================================================
# FootnoteCRUD Tests
# =============================================================================


class TestFootnoteCRUD:
    def test_create_with_label(self):
        crud = FootnoteCRUD()
        f = crud.create("fn1", "Footnote text", label="1")
        assert crud.get_label(f) == "1"

    def test_can_contain_paragraph(self):
        crud = FootnoteCRUD()
        f = crud.create("fn1", "Text")
        crud.add_child(f, "paragraph:p1", LayerType.PARAGRAPH)
        assert "paragraph:p1" in f.children


# =============================================================================
# MetadataCRUD Tests
# =============================================================================


class TestMetadataCRUD:
    def test_create(self):
        crud = MetadataCRUD()
        m = crud.create("md1", "---\ntitle: Test\n---")
        assert m.component_id == "metadata:md1"

    def test_leaf_cannot_have_children(self):
        crud = MetadataCRUD()
        m = crud.create("md1", "---\n---")
        with pytest.raises(ValueError):
            crud.add_child(m, "paragraph:p1", LayerType.PARAGRAPH)


# =============================================================================
# FigureCRUD Tests
# =============================================================================


class TestFigureCRUD:
    def test_create_with_attrs(self):
        crud = FigureCRUD()
        f = crud.create("f1", "![caption](url)", caption="A figure", src="url")
        assert crud.get_caption(f) == "A figure"
        assert crud.get_src(f) == "url"

    def test_leaf_cannot_have_children(self):
        crud = FigureCRUD()
        f = crud.create("f1", "![img](url)")
        with pytest.raises(ValueError):
            crud.add_child(f, "paragraph:p1", LayerType.PARAGRAPH)


# =============================================================================
# DiagramCRUD Tests
# =============================================================================


class TestDiagramCRUD:
    def test_create_with_type(self):
        crud = DiagramCRUD()
        d = crud.create("d1", "graph TD", diagram_type="mermaid")
        assert crud.get_diagram_type(d) == "mermaid"

    def test_leaf_cannot_have_children(self):
        crud = DiagramCRUD()
        d = crud.create("d1", "graph TD")
        with pytest.raises(ValueError):
            crud.add_child(d, "paragraph:p1", LayerType.PARAGRAPH)


# =============================================================================
# TableCRUD Tests
# =============================================================================


class TestTableCRUD:
    def test_create_default(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        assert t.component_id == "table:tbl1"
        assert t.num_cols == 0
        assert t.has_header is False

    def test_create_with_header(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |", has_header=True)
        assert t.has_header is True

    def test_add_row_auto_index(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        r0 = crud.add_row(t)
        r1 = crud.add_row(t)
        assert r0.row_index == 0
        assert r1.row_index == 1

    def test_add_row_explicit_index(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        r = crud.add_row(t, row_index=5)
        assert r.row_index == 5

    def test_add_row_duplicate_index(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        with pytest.raises(ValueError, match="already exists"):
            crud.add_row(t, row_index=0)

    def test_remove_row(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_row(t, row_index=1)
        crud.remove_row(t, 0)
        assert crud.get_row_count(t) == 1
        assert crud.get_row(t, 1) is not None

    def test_remove_row_not_found(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        with pytest.raises(ValueError, match="not found"):
            crud.remove_row(t, 99)

    def test_add_cell(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        c0 = crud.add_cell(t, 0, col=0)
        c1 = crud.add_cell(t, 0, col=1)
        assert c0.position.col == 0
        assert c1.position.col == 1

    def test_add_cell_header(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        c = crud.add_cell(t, 0, col=0, is_header=True)
        assert c.position.is_header is True

    def test_add_cell_duplicate(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        with pytest.raises(ValueError, match="already exists"):
            crud.add_cell(t, 0, col=0)

    def test_remove_cell(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        crud.remove_cell(t, 0, 0)
        with pytest.raises(ValueError):
            crud.get_cell(t, 0, 0)

    def test_get_row(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=3)
        row = crud.get_row(t, 3)
        assert row.row_index == 3

    def test_get_row_not_found(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        with pytest.raises(ValueError, match="not found"):
            crud.get_row(t, 0)

    def test_get_cell(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=2)
        cell = crud.get_cell(t, 0, 2)
        assert cell.position.col == 2

    def test_get_cell_not_found(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        with pytest.raises(ValueError, match="not found"):
            crud.get_cell(t, 0, 0)

    def test_add_child_to_cell(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        crud.add_child_to_cell(t, 0, 0, "paragraph:p1", LayerType.PARAGRAPH)
        children = crud.get_cell_children(t, 0, 0)
        assert "paragraph:p1" in children
        assert "paragraph:p1" in t.children

    def test_add_child_to_cell_duplicate(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        crud.add_child_to_cell(t, 0, 0, "paragraph:p1", LayerType.PARAGRAPH)
        with pytest.raises(ValueError, match="already in cell"):
            crud.add_child_to_cell(t, 0, 0, "paragraph:p1", LayerType.PARAGRAPH)

    def test_remove_child_from_cell(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        crud.add_child_to_cell(t, 0, 0, "paragraph:p1", LayerType.PARAGRAPH)
        crud.remove_child_from_cell(t, 0, 0, "paragraph:p1")
        assert "paragraph:p1" not in crud.get_cell_children(t, 0, 0)

    def test_set_header(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        crud.add_cell(t, 0, col=1)
        crud.set_header(t, has_header=True)
        assert t.has_header is True
        for cell in t.rows[0].cells:
            assert cell.position.is_header is True

    def test_set_header_false(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |", has_header=True)
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0, is_header=True)
        crud.set_header(t, has_header=False)
        assert t.has_header is False
        assert t.rows[0].cells[0].position.is_header is False

    def test_get_row_count(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        assert crud.get_row_count(t) == 0
        crud.add_row(t)
        assert crud.get_row_count(t) == 1

    def test_get_col_count(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        assert crud.get_col_count(t) == 0
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        crud.add_cell(t, 0, col=1)
        assert crud.get_col_count(t) == 2

    def test_all_cell_children(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| A | B |")
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0)
        crud.add_cell(t, 0, col=1)
        crud.add_child_to_cell(t, 0, 0, "paragraph:p1", LayerType.PARAGRAPH)
        crud.add_child_to_cell(t, 0, 1, "figure:f1", LayerType.FIGURE)
        all_children = crud.all_cell_children(t)
        assert all_children[(0, 0)] == ["paragraph:p1"]
        assert all_children[(0, 1)] == ["figure:f1"]

    def test_full_table_workflow(self):
        crud = TableCRUD()
        t = crud.create("tbl1", "| Feature | Status |")

        # Add header row
        crud.add_row(t, row_index=0)
        crud.add_cell(t, 0, col=0, is_header=True)
        crud.add_cell(t, 0, col=1, is_header=True)
        crud.add_child_to_cell(t, 0, 0, "paragraph:p1", LayerType.PARAGRAPH)
        crud.add_child_to_cell(t, 0, 1, "paragraph:p2", LayerType.PARAGRAPH)

        # Add data row
        crud.add_row(t, row_index=1)
        crud.add_cell(t, 1, col=0)
        crud.add_cell(t, 1, col=1)
        crud.add_child_to_cell(t, 1, 0, "paragraph:p3", LayerType.PARAGRAPH)
        crud.add_child_to_cell(t, 1, 1, "list:l1", LayerType.LIST)

        assert crud.get_row_count(t) == 2
        assert crud.get_col_count(t) == 2
        assert len(t.children) == 4


# =============================================================================
# ListCRUD Tests
# =============================================================================


class TestListCRUD:
    def test_create_unordered(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1")
        assert lst.component_id == "list:l1"
        assert lst.style == ListStyle.UNORDERED

    def test_create_ordered(self):
        crud = ListCRUD()
        lst = crud.create("l1", "1. Item 1", style=ListStyle.ORDERED)
        assert lst.style == ListStyle.ORDERED

    def test_add_item_auto_index(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1")
        i0 = crud.add_item(lst)
        i1 = crud.add_item(lst)
        assert i0.item_index == 0
        assert i1.item_index == 1

    def test_insert_item(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1")
        crud.add_item(lst)
        crud.add_item(lst)
        inserted = crud.insert_item(lst, position=1)
        assert inserted.item_index == 1
        assert crud.item_count(lst) == 3
        assert lst.items[0].item_index == 0
        assert lst.items[1].item_index == 1
        assert lst.items[2].item_index == 2

    def test_insert_item_out_of_bounds(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1")
        with pytest.raises(ValueError, match="out of range"):
            crud.insert_item(lst, position=5)

    def test_remove_item(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1")
        crud.add_item(lst)
        crud.add_item(lst)
        crud.remove_item(lst, 0)
        assert crud.item_count(lst) == 1
        assert lst.items[0].item_index == 0

    def test_remove_item_not_found(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1")
        with pytest.raises(ValueError, match="not found"):
            crud.remove_item(lst, 5)

    def test_reorder_item(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1")
        crud.add_item(lst)
        crud.add_item(lst)
        crud.add_item(lst)
        crud.reorder_item(lst, from_index=0, to_index=2)
        assert lst.items[0].item_index == 0
        assert lst.items[2].item_index == 2

    def test_nest_sublist(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        crud.nest_sublist(lst, 0, "list:l2")
        assert "list:l2" in lst.items[0].children
        assert "list:l2" in lst.children

    def test_nest_sublist_duplicate(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        crud.nest_sublist(lst, 0, "list:l2")
        with pytest.raises(ValueError, match="already in item"):
            crud.nest_sublist(lst, 0, "list:l2")

    def test_add_child_to_item(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        crud.add_child_to_item(lst, 0, "paragraph:p1")
        assert "paragraph:p1" in lst.items[0].children
        assert "paragraph:p1" in lst.children

    def test_remove_child_from_item(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        crud.add_child_to_item(lst, 0, "paragraph:p1")
        crud.remove_child_from_item(lst, 0, "paragraph:p1")
        assert "paragraph:p1" not in lst.items[0].children

    def test_get_item(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        item = crud.get_item(lst, 0)
        assert item.item_index == 0

    def test_get_item_not_found(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        with pytest.raises(ValueError, match="not found"):
            crud.get_item(lst, 0)

    def test_set_item_char_range(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        crud.set_item_char_range(lst, 0, 100, 200)
        assert lst.items[0].char_start == 100
        assert lst.items[0].char_end == 200

    def test_set_style(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.set_style(lst, ListStyle.ORDERED)
        assert lst.style == ListStyle.ORDERED

    def test_get_item_children(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        crud.add_child_to_item(lst, 0, "paragraph:p1")
        children = crud.get_item_children(lst, 0)
        assert children == ["paragraph:p1"]

    def test_all_item_children(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Item")
        crud.add_item(lst)
        crud.add_item(lst)
        crud.add_child_to_item(lst, 0, "paragraph:p1")
        crud.add_child_to_item(lst, 1, "paragraph:p2")
        all_children = crud.all_item_children(lst)
        assert all_children[0] == ["paragraph:p1"]
        assert all_children[1] == ["paragraph:p2"]

    def test_full_list_workflow(self):
        crud = ListCRUD()
        lst = crud.create("l1", "- Feature\n  - Sub 1\n  - Sub 2", style=ListStyle.UNORDERED)

        crud.add_item(lst)
        crud.add_item(lst)
        crud.add_child_to_item(lst, 0, "paragraph:p1")
        crud.nest_sublist(lst, 0, "list:l2")
        crud.add_child_to_item(lst, 1, "paragraph:p2")

        assert crud.item_count(lst) == 2
        assert "list:l2" in lst.items[0].children
        assert len(lst.children) == 3


# =============================================================================
# Integration: Cross-type nesting
# =============================================================================


class TestCrossTypeNesting:
    def test_table_with_nested_list_in_cell(self):
        table_crud = TableCRUD()
        list_crud = ListCRUD()

        t = table_crud.create("tbl1", "| Desc | Tasks |")
        table_crud.add_row(t, row_index=0)
        table_crud.add_cell(t, 0, col=0)
        table_crud.add_cell(t, 0, col=1)

        lst = list_crud.create("l1", "- Task 1")
        list_crud.add_item(lst)

        table_crud.add_child_to_cell(t, 0, 1, "list:l1", LayerType.LIST)
        assert "list:l1" in table_crud.get_cell_children(t, 0, 1)

    def test_list_with_nested_table_in_item(self):
        list_crud = ListCRUD()
        table_crud = TableCRUD()

        lst = list_crud.create("l1", "- Details:")
        list_crud.add_item(lst)

        t = table_crud.create("tbl1", "| A | B |")
        table_crud.add_row(t, row_index=0)
        table_crud.add_cell(t, 0, col=0)

        list_crud.add_child_to_item(lst, 0, "table:tbl1")
        assert "table:tbl1" in list_crud.get_item_children(lst, 0)

    def test_blockquote_with_table(self):
        bq_crud = BlockquoteCRUD()
        table_crud = TableCRUD()

        bq = bq_crud.create("bq1", "> Data:")
        t = table_crud.create("tbl1", "| X | Y |")

        bq_crud.add_child(bq, "table:tbl1", LayerType.TABLE)
        assert "table:tbl1" in bq.children

    def test_heading_with_list_and_paragraph(self):
        heading_crud = HeadingCRUD()
        list_crud = ListCRUD()
        para_crud = ParagraphCRUD()

        h = heading_crud.create("h1", "# Overview")
        p = para_crud.create("p1", "Summary")
        lst = list_crud.create("l1", "- Point 1")

        heading_crud.add_child(h, "paragraph:p1", LayerType.PARAGRAPH)
        heading_crud.add_child(h, "list:l1", LayerType.LIST)
        assert len(h.children) == 2

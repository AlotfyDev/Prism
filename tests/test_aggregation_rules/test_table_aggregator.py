"""Tests for TableAggregator — structured table index from AST."""

import pytest

from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.aggregation.rules.table_aggregator import TableAggregator


@pytest.fixture
def aggregator():
    return TableAggregator()


class TestValidateInput:
    def test_valid_input(self, aggregator):
        valid, msg = aggregator.validate_input([])
        assert valid is True

    def test_invalid_type(self, aggregator):
        valid, msg = aggregator.validate_input("not a list")
        assert valid is False


class TestValidateOutput:
    def test_valid_output(self, aggregator):
        from prism.stage2.aggregation.aggregation_models import TableIndex
        tables = [TableIndex(
            component_id="table:1",
            dimensions=(3, 2),
            has_header=True,
            raw_markdown="| A | B |\n|---|---|\n| 1 | 2 |",
        )]
        valid, msg = aggregator.validate_output(tables)
        assert valid is True

    def test_missing_component_id(self, aggregator):
        from prism.stage2.aggregation.aggregation_models import TableIndex
        tables = [TableIndex(
            component_id="",
            dimensions=(0, 0),
            raw_markdown="| A |",
        )]
        valid, msg = aggregator.validate_output(tables)
        assert valid is False


class TestParseTable:
    def test_empty_nodes(self, aggregator):
        result = aggregator.aggregate([])
        assert result == []

    def test_single_table_node(self, aggregator):
        table_node = MarkdownNode(
            node_type=NodeType.TABLE,
            raw_content="| A | B |\n|---|---|\n| 1 | 2 |",
            char_start=0,
            char_end=30,
            children=[],
        )
        result = aggregator.aggregate([table_node])
        assert len(result) == 1
        assert result[0].dimensions[0] >= 0

    def test_multiple_tables(self, aggregator):
        nodes = [
            MarkdownNode(
                node_type=NodeType.TABLE,
                raw_content="| X | Y |\n|---|---|\n| a | b |",
                char_start=0,
                char_end=25,
                children=[],
                attributes={"component_id": "table:1"},
            ),
            MarkdownNode(
                node_type=NodeType.TABLE,
                raw_content="| M | N |\n|---|---|\n| x | y |",
                char_start=30,
                char_end=55,
                children=[],
                attributes={"component_id": "table:2"},
            ),
        ]
        result = aggregator.aggregate(nodes)
        assert len(result) == 2
        assert result[0].component_id == "table:1"
        assert result[1].component_id == "table:2"

    def test_raw_content_parsing(self, aggregator):
        """Test parsing table from raw markdown."""
        table_node = MarkdownNode(
            node_type=NodeType.TABLE,
            raw_content="| Name | Age |\n|---|---|\n| Alice | 30 |\n| Bob | 25 |",
            char_start=0,
            char_end=55,
            children=[],
            attributes={"component_id": "table:1"},
        )
        result = aggregator.aggregate([table_node])
        assert len(result) == 1
        assert result[0].has_header is True
        assert "Name" in result[0].header_cells
        assert result[0].dimensions[0] == 2  # 2 data rows


class TestNameAndTier:
    def test_name(self, aggregator):
        assert aggregator.name() == "TableAggregator"

    def test_tier(self, aggregator):
        assert aggregator.tier == "rules"

    def test_version(self, aggregator):
        assert aggregator.version == "1.0.0"

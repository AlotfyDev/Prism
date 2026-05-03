"""Tests for ListAggregator — structured list index with nesting."""

import pytest

from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.aggregation.rules.list_aggregator import ListAggregator


@pytest.fixture
def aggregator():
    return ListAggregator()


class TestValidateInput:
    def test_valid(self, aggregator):
        assert aggregator.validate_input([]) == (True, "")

    def test_invalid(self, aggregator):
        valid, msg = aggregator.validate_input("not a list")
        assert valid is False


class TestParseList:
    def test_empty(self, aggregator):
        result = aggregator.aggregate([])
        assert result == []

    def test_single_list(self, aggregator):
        list_node = MarkdownNode(
            node_type=NodeType.LIST,
            raw_content="- Item 1\n- Item 2",
            char_start=0,
            char_end=20,
            children=[],
            attributes={"component_id": "list:1"},
        )
        result = aggregator.aggregate([list_node])
        assert len(result) == 1
        assert result[0].style in ("ordered", "unordered")
        assert result[0].total_items == 0  # No children = no items

    def test_nested_list(self, aggregator):
        inner_item = MarkdownNode(
            node_type=NodeType.LIST_ITEM,
            raw_content="- Sub 1",
            char_start=10,
            char_end=17,
            children=[],
        )
        inner_list = MarkdownNode(
            node_type=NodeType.LIST,
            raw_content="- Sub 1\n- Sub 2",
            char_start=10,
            char_end=25,
            children=[inner_item],
        )
        outer_item = MarkdownNode(
            node_type=NodeType.LIST_ITEM,
            raw_content="- Item 1\n  - Sub 1",
            char_start=0,
            char_end=20,
            children=[inner_list],
        )
        outer_list = MarkdownNode(
            node_type=NodeType.LIST,
            raw_content="- Item 1\n  - Sub 1\n- Item 2",
            char_start=0,
            char_end=30,
            children=[outer_item],
            attributes={"component_id": "list:1"},
        )
        result = aggregator.aggregate([outer_list])
        # Outer list + inner list parsed separately
        assert len(result) >= 1
        assert result[0].total_items >= 1


class TestNestingTree:
    def test_flat_items(self, aggregator):
        from prism.stage2.aggregation.aggregation_models import ListItemIndex
        items = [
            ListItemIndex(item_index=0, depth=0, text="A", has_children=False),
            ListItemIndex(item_index=1, depth=0, text="B", has_children=False),
        ]
        tree = aggregator._build_nesting_tree(items)
        assert len(tree) == 2
        assert tree[0].item.text == "A"
        assert tree[1].item.text == "B"

    def test_nested_items(self, aggregator):
        from prism.stage2.aggregation.aggregation_models import ListItemIndex
        items = [
            ListItemIndex(item_index=0, depth=0, text="A", has_children=True),
            ListItemIndex(item_index=1, depth=1, text="A.1", has_children=False),
            ListItemIndex(item_index=2, depth=1, text="A.2", has_children=False),
            ListItemIndex(item_index=3, depth=0, text="B", has_children=False),
        ]
        tree = aggregator._build_nesting_tree(items)
        assert len(tree) == 2
        assert len(tree[0].children) == 2
        assert tree[0].children[0].item.text == "A.1"


class TestNameAndTier:
    def test_name(self, aggregator):
        assert aggregator.name() == "ListAggregator"

    def test_tier(self, aggregator):
        assert aggregator.tier == "rules"

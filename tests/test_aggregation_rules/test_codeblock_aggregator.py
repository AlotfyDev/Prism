"""Tests for CodeBlockAggregator — structured code block index."""

import pytest

from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.aggregation.rules.codeblock_aggregator import CodeBlockAggregator


@pytest.fixture
def aggregator():
    return CodeBlockAggregator()


class TestValidateInput:
    def test_valid(self, aggregator):
        assert aggregator.validate_input([]) == (True, "")

    def test_invalid(self, aggregator):
        valid, msg = aggregator.validate_input("not a list")
        assert valid is False


class TestParseCodeBlock:
    def test_empty(self, aggregator):
        result = aggregator.aggregate([])
        assert result == []

    def test_python_code_block(self, aggregator):
        node = MarkdownNode(
            node_type=NodeType.CODE_BLOCK,
            raw_content="```python\ndef hello():\n    print('world')\n```",
            char_start=0,
            char_end=45,
            children=[],
            attributes={"component_id": "codeblock:1", "language": "python"},
        )
        result = aggregator.aggregate([node])
        assert len(result) == 1
        assert result[0].language == "python"
        assert result[0].total_lines == 2  # def hello(): + print('world')
        assert result[0].non_empty_lines == 2

    def test_language_detection(self, aggregator):
        """Detect language from fence info string."""
        node = MarkdownNode(
            node_type=NodeType.CODE_BLOCK,
            raw_content="```javascript\nconst x = 1;\n```",
            char_start=0,
            char_end=30,
            children=[],
        )
        result = aggregator.aggregate([node])
        assert len(result) == 1
        assert result[0].language == "javascript"

    def test_empty_lines(self, aggregator):
        node = MarkdownNode(
            node_type=NodeType.CODE_BLOCK,
            raw_content="```\nline1\n\nline3\n```",
            char_start=0,
            char_end=20,
            children=[],
        )
        result = aggregator.aggregate([node])
        assert result[0].total_lines == 3
        assert result[0].non_empty_lines == 2

    def test_indentation_pattern(self, aggregator):
        node = MarkdownNode(
            node_type=NodeType.CODE_BLOCK,
            raw_content="```\ndef foo():\n    pass\n        nested\n```",
            char_start=0,
            char_end=40,
            children=[],
        )
        result = aggregator.aggregate([node])
        assert result[0].indentation_pattern[0] == 0
        assert result[0].indentation_pattern[1] == 4

    def test_line_numbers(self, aggregator):
        """Detect line number syntax markers."""
        node = MarkdownNode(
            node_type=NodeType.CODE_BLOCK,
            raw_content="```\n1 | def foo():\n2 |     pass\n```",
            char_start=0,
            char_end=35,
            children=[],
        )
        result = aggregator.aggregate([node])
        assert result[0].has_syntax_markers is True

    def test_no_line_numbers(self, aggregator):
        node = MarkdownNode(
            node_type=NodeType.CODE_BLOCK,
            raw_content="```\ndef foo():\n    pass\n```",
            char_start=0,
            char_end=25,
            children=[],
        )
        result = aggregator.aggregate([node])
        assert result[0].has_syntax_markers is False


class TestNameAndTier:
    def test_name(self, aggregator):
        assert aggregator.name() == "CodeBlockAggregator"

    def test_tier(self, aggregator):
        assert aggregator.tier == "rules"

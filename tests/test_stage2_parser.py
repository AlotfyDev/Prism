"""Unit tests for Stage 2 MarkdownParser (markdown-it-py)."""

import pytest

from prism.schemas.physical import MarkdownNode, NodeType


class TestMarkdownNodeSchema:
    """MarkdownNode Pydantic schema validation."""

    def test_valid_heading_node(self):
        node = MarkdownNode(
            node_type=NodeType.HEADING,
            raw_content="# Hello",
            level=1,
        )
        assert node.node_type == NodeType.HEADING
        assert node.raw_content == "# Hello"
        assert node.level == 1

    def test_valid_paragraph_node(self):
        node = MarkdownNode(
            node_type=NodeType.PARAGRAPH,
            raw_content="Some text here",
        )
        assert node.node_type == NodeType.PARAGRAPH
        assert node.raw_content == "Some text here"

    def test_valid_node_with_char_offsets(self):
        node = MarkdownNode(
            node_type=NodeType.HEADING,
            raw_content="# Title",
            char_start=0,
            char_end=7,
        )
        assert node.char_start == 0
        assert node.char_end == 7

    def test_valid_node_with_children(self):
        parent = MarkdownNode(
            node_type=NodeType.LIST,
            raw_content="- a\n- b",
            children=[
                MarkdownNode(node_type=NodeType.INLINE, raw_content="a"),
                MarkdownNode(node_type=NodeType.INLINE, raw_content="b"),
            ],
        )
        assert len(parent.children) == 2

    def test_valid_node_with_attributes(self):
        node = MarkdownNode(
            node_type=NodeType.CODE_BLOCK,
            raw_content="```python\nx = 1\n```",
            attributes={"language": "python"},
        )
        assert node.attributes["language"] == "python"

    def test_valid_hr_node(self):
        node = MarkdownNode(
            node_type=NodeType.HR,
            raw_content="---",
        )
        assert node.node_type == NodeType.HR

    def test_valid_blockquote_node(self):
        node = MarkdownNode(
            node_type=NodeType.BLOCKQUOTE,
            raw_content="> quoted text",
        )
        assert node.node_type == NodeType.BLOCKQUOTE

    def test_valid_table_node(self):
        node = MarkdownNode(
            node_type=NodeType.TABLE,
            raw_content="| A | B |\n|---|---|\n| 1 | 2 |",
        )
        assert node.node_type == NodeType.TABLE

    def test_invalid_empty_content(self):
        with pytest.raises(Exception):
            MarkdownNode(
                node_type=NodeType.PARAGRAPH,
                raw_content="",
            )


class TestNodeTypeEnum:
    """NodeType enum covers all markdown-it-py node types."""

    def test_all_layer_types_present(self):
        """NodeType must cover all LayerType values for downstream mapping."""
        from prism.schemas.enums import LayerType

        for lt in LayerType:
            # diagram, footnote, metadata, figure may not have direct
            # markdown-it-py tokens — they are classified later
            if lt.value in ("paragraph", "list", "table", "heading", "code_block", "blockquote"):
                assert hasattr(NodeType, lt.name)

    def test_inline_and_hr_exist(self):
        assert hasattr(NodeType, "INLINE")
        assert hasattr(NodeType, "HR")


class TestMarkdownItParser:
    """MarkdownItParser implements ProcessingUnit[Stage1Output, list[MarkdownNode], TopologyConfig]."""

    def _make_parser(self):
        from prism.stage2.parser import MarkdownItParser
        return MarkdownItParser()

    def _make_input(self, text: str):
        from prism.schemas.token import Stage1Output
        return Stage1Output(
            tokens={},
            metadata={},
            source_text=text,
        )

    def test_parses_heading(self):
        parser = self._make_parser()
        nodes = parser.process(self._make_input("# Hello\n\nWorld"), None)
        headings = [n for n in nodes if n.node_type == NodeType.HEADING]
        assert len(headings) == 1
        assert headings[0].level == 1

    def test_parses_paragraph(self):
        parser = self._make_parser()
        nodes = parser.process(self._make_input("Some text here"), None)
        paragraphs = [n for n in nodes if n.node_type == NodeType.PARAGRAPH]
        assert len(paragraphs) >= 1

    def test_parses_code_block(self):
        parser = self._make_parser()
        md = "```python\nx = 1\n```"
        nodes = parser.process(self._make_input(md), None)
        code_blocks = [n for n in nodes if n.node_type == NodeType.CODE_BLOCK]
        assert len(code_blocks) >= 1
        assert code_blocks[0].attributes.get("language") == "python"

    def test_parses_list_with_items(self):
        parser = self._make_parser()
        md = "- item 1\n- item 2\n- item 3"
        nodes = parser.process(self._make_input(md), None)
        lists = [n for n in nodes if n.node_type == NodeType.LIST]
        assert len(lists) >= 1
        assert len(lists[0].children) == 3

    def test_parses_blockquote(self):
        parser = self._make_parser()
        nodes = parser.process(self._make_input("> quoted text"), None)
        blockquotes = [n for n in nodes if n.node_type == NodeType.BLOCKQUOTE]
        assert len(blockquotes) >= 1

    def test_parses_hr(self):
        parser = self._make_parser()
        nodes = parser.process(self._make_input("---"), None)
        hrs = [n for n in nodes if n.node_type == NodeType.HR]
        assert len(hrs) >= 1

    def test_parses_multi_layer_document(self):
        """Parse a document with all node types."""
        parser = self._make_parser()
        md = """# Main Title

A paragraph here.

## Section

- list item 1
- list item 2

| A | B |
|---|---|
| 1 | 2 |

> A blockquote

```python
code here
```

---
"""
        nodes = parser.process(self._make_input(md), None)
        types = {n.node_type for n in nodes}
        assert NodeType.HEADING in types
        assert NodeType.PARAGRAPH in types
        assert NodeType.LIST in types
        assert NodeType.TABLE in types
        assert NodeType.BLOCKQUOTE in types
        assert NodeType.CODE_BLOCK in types
        assert NodeType.HR in types

    def test_char_offsets_preserved(self):
        """Each node has char_start/char_end mapping to source text."""
        parser = self._make_parser()
        md = "# Hello\n\nWorld"
        nodes = parser.process(self._make_input(md), None)
        for node in nodes:
            if node.char_start is not None and node.char_end is not None:
                assert node.char_start >= 0
                assert node.char_end > node.char_start
                assert node.char_end <= len(md)

    def test_name_returns_string(self):
        parser = self._make_parser()
        name = parser.name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_tier_is_python_nlp(self):
        parser = self._make_parser()
        assert parser.tier == "python_nlp"

    def test_validate_input_rejects_empty(self):
        parser = self._make_parser()
        valid, msg = parser.validate_input(self._make_input(""))
        assert not valid

    def test_validate_input_accepts_non_empty(self):
        parser = self._make_parser()
        valid, msg = parser.validate_input(self._make_input("# Hello"))
        assert valid

    def test_validate_output_accepts_valid_nodes(self):
        parser = self._make_parser()
        nodes = [MarkdownNode(node_type=NodeType.PARAGRAPH, raw_content="test")]
        valid, msg = parser.validate_output(nodes)
        assert valid

    def test_validate_output_rejects_empty_list(self):
        parser = self._make_parser()
        valid, msg = parser.validate_output([])
        assert not valid

    def test_nested_lists_preserve_hierarchy(self):
        """Nested list items are children of the list node."""
        parser = self._make_parser()
        md = "- item 1\n  - sub 1\n  - sub 2\n- item 2"
        nodes = parser.process(self._make_input(md), None)
        lists = [n for n in nodes if n.node_type == NodeType.LIST]
        assert len(lists) >= 1
        # List should have children
        assert len(lists[0].children) >= 2

    def test_tables_parsed_with_gfm_plugin(self):
        """Tables are properly parsed using GFM tables plugin."""
        parser = self._make_parser()
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        nodes = parser.process(self._make_input(md), None)
        tables = [n for n in nodes if n.node_type == NodeType.TABLE]
        assert len(tables) >= 1

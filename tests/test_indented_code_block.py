"""Tests for Indented Code Block detection, CRUD, schema, and mapper integration."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HierarchyNode,
    HierarchyTree,
    IndentedCodeBlockComponent,
    LayerInstance,
    MarkdownNode,
    NodeType,
    NESTING_MATRIX,
)
from prism.stage2.layers.indented_code_block import IndentedCodeBlockCRUD
from prism.stage2.layers.specific_detectors import ASTIndentedCodeBlockDetector
from prism.stage2.mapper import ComponentMapper


class TestIndentedCodeBlockComponentSchema:
    """Test IndentedCodeBlockComponent Pydantic schema."""

    def test_create_indented_code_block(self):
        comp = IndentedCodeBlockComponent(
            component_id="indented_code_block:icb1",
            layer_type=LayerType.INDENTED_CODE_BLOCK,
            raw_content="    code here\n    more code",
            line_count=2,
            char_start=0,
            char_end=30,
        )
        assert comp.component_id == "indented_code_block:icb1"
        assert comp.layer_type == LayerType.INDENTED_CODE_BLOCK
        assert comp.line_count == 2

    def test_default_line_count_is_one(self):
        comp = IndentedCodeBlockComponent(
            component_id="indented_code_block:icb2",
            layer_type=LayerType.INDENTED_CODE_BLOCK,
            raw_content="    single line",
            char_start=0,
            char_end=15,
        )
        assert comp.line_count == 1

    def test_is_leaf(self):
        matrix = NESTING_MATRIX
        assert matrix.is_leaf(LayerType.INDENTED_CODE_BLOCK)

    def test_component_id_prefix(self):
        comp = IndentedCodeBlockComponent(
            component_id="indented_code_block:icb3",
            layer_type=LayerType.INDENTED_CODE_BLOCK,
            raw_content="    test",
            char_start=0,
            char_end=8,
        )
        assert comp.component_id.startswith("indented_code_block:")

    def test_multi_line_count(self):
        comp = IndentedCodeBlockComponent(
            component_id="indented_code_block:icb4",
            layer_type=LayerType.INDENTED_CODE_BLOCK,
            raw_content="    line1\n    line2\n    line3\n",
            line_count=3,
            char_start=0,
            char_end=30,
        )
        assert comp.line_count == 3

    def test_inherits_physical_component_fields(self):
        comp = IndentedCodeBlockComponent(
            component_id="indented_code_block:icb5",
            layer_type=LayerType.INDENTED_CODE_BLOCK,
            raw_content="    code",
            char_start=10,
            char_end=18,
        )
        assert comp.char_start == 10
        assert comp.char_end == 18
        assert comp.raw_content == "    code"


class TestIndentedCodeBlockNesting:
    """Test NestingMatrix rules for INDENTED_CODE_BLOCK."""

    def test_indented_code_block_is_leaf(self):
        matrix = NESTING_MATRIX
        assert matrix.is_leaf(LayerType.INDENTED_CODE_BLOCK)

    def test_heading_can_contain_indented_code_block(self):
        assert NESTING_MATRIX.can_contain(
            LayerType.HEADING, LayerType.INDENTED_CODE_BLOCK
        )

    def test_list_can_contain_indented_code_block(self):
        assert NESTING_MATRIX.can_contain(
            LayerType.LIST, LayerType.INDENTED_CODE_BLOCK
        )

    def test_table_can_contain_indented_code_block(self):
        assert NESTING_MATRIX.can_contain(
            LayerType.TABLE, LayerType.INDENTED_CODE_BLOCK
        )

    def test_blockquote_can_contain_indented_code_block(self):
        assert NESTING_MATRIX.can_contain(
            LayerType.BLOCKQUOTE, LayerType.INDENTED_CODE_BLOCK
        )

    def test_paragraph_cannot_contain_indented_code_block(self):
        assert not NESTING_MATRIX.can_contain(
            LayerType.PARAGRAPH, LayerType.INDENTED_CODE_BLOCK
        )

    def test_task_list_can_contain_indented_code_block(self):
        assert NESTING_MATRIX.can_contain(
            LayerType.TASK_LIST, LayerType.INDENTED_CODE_BLOCK
        )

    def test_indented_code_block_cannot_contain_anything(self):
        matrix = NESTING_MATRIX
        for lt in LayerType:
            if lt != LayerType.INDENTED_CODE_BLOCK:
                assert not matrix.can_contain(LayerType.INDENTED_CODE_BLOCK, lt)


class TestASTIndentedCodeBlockDetector:
    """Test AST-based indented code block detector."""

    def test_detect_single_line(self):
        detector = ASTIndentedCodeBlockDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.INDENTED_CODE_BLOCK,
                raw_content="    code here\n",
                char_start=0,
                char_end=14,
            )
        ]
        results = detector.detect(nodes, "    code here\n")
        assert len(results) == 1
        assert results[0].layer_type == LayerType.INDENTED_CODE_BLOCK
        assert results[0].attributes["line_count"] == "1"

    def test_detect_multi_line(self):
        detector = ASTIndentedCodeBlockDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.INDENTED_CODE_BLOCK,
                raw_content="    line1\n    line2\n",
                char_start=0,
                char_end=20,
            )
        ]
        results = detector.detect(nodes, "    line1\n    line2\n")
        assert len(results) == 1
        assert results[0].attributes["line_count"] == "2"

    def test_no_indented_code_block_in_text(self):
        detector = ASTIndentedCodeBlockDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.PARAGRAPH,
                raw_content="Hello world",
                char_start=0,
                char_end=11,
            )
        ]
        results = detector.detect(nodes, "Hello world")
        assert len(results) == 0

    def test_multiple_indented_code_blocks(self):
        detector = ASTIndentedCodeBlockDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.INDENTED_CODE_BLOCK,
                raw_content="    code1\n",
                char_start=0,
                char_end=10,
            ),
            MarkdownNode(
                node_type=NodeType.INDENTED_CODE_BLOCK,
                raw_content="    code2\n    code3\n",
                char_start=12,
                char_end=30,
            ),
        ]
        results = detector.detect(nodes, "    code1\n\n    code2\n    code3\n")
        assert len(results) == 2
        assert results[0].attributes["line_count"] == "1"
        assert results[1].attributes["line_count"] == "2"


class TestIndentedCodeBlockCRUD:
    """Test IndentedCodeBlockCRUD operations."""

    def test_create_single_line(self):
        crud = IndentedCodeBlockCRUD()
        icb = crud.create("icb1", "    code here", char_start=0, char_end=13)
        assert icb.component_id == "indented_code_block:icb1"
        assert icb.layer_type == LayerType.INDENTED_CODE_BLOCK
        assert icb.raw_content == "    code here"
        assert icb.line_count == 1
        assert icb.char_start == 0
        assert icb.char_end == 13

    def test_create_multi_line(self):
        crud = IndentedCodeBlockCRUD()
        icb = crud.create("icb2", "    line1\n    line2\n", char_start=0, char_end=20)
        assert icb.line_count == 2

    def test_char_end_auto_computed(self):
        crud = IndentedCodeBlockCRUD()
        icb = crud.create("icb3", "    code", char_start=10)
        assert icb.char_start == 10
        assert icb.char_end == 18

    def test_layer_type_property(self):
        crud = IndentedCodeBlockCRUD()
        assert crud.layer_type == LayerType.INDENTED_CODE_BLOCK


class TestIndentedCodeBlockMapperIntegration:
    """Test ComponentMapper integration for IndentedCodeBlockComponent."""

    def test_mapper_creates_indented_code_block_component(self):
        mapper = ComponentMapper()
        inst = LayerInstance(
            layer_type=LayerType.INDENTED_CODE_BLOCK,
            raw_content="    code here\n",
            char_start=0,
            char_end=14,
            line_start=0,
            line_end=1,
            attributes={"line_count": "1"},
            depth=0,
            sibling_index=0,
        )
        hierarchy_node = HierarchyNode(
            instance=inst,
            children=[],
        )
        tree = HierarchyTree(root_nodes=[hierarchy_node])

        components = mapper.map(tree)
        assert len(components) == 1
        comp = components[0]
        assert isinstance(comp, IndentedCodeBlockComponent)
        assert comp.raw_content == "    code here\n"


class TestIndentedCodeBlockEndToEnd:
    """End-to-end tests: parser → detector → mapper."""

    def test_parser_creates_indented_code_block_node(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "    indented code\n    second line\n"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        icb_nodes = [n for n in nodes if n.node_type == NodeType.INDENTED_CODE_BLOCK]
        assert len(icb_nodes) == 1
        assert "indented code" in icb_nodes[0].raw_content

    def test_fenced_code_block_not_confused_with_indented(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "```python\nx = 1\n```"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        fenced = [n for n in nodes if n.node_type == NodeType.CODE_BLOCK]
        indented = [n for n in nodes if n.node_type == NodeType.INDENTED_CODE_BLOCK]
        assert len(fenced) == 1
        assert len(indented) == 0

    def test_full_pipeline_indented_code_block(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "    code line 1\n    code line 2\n"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        detector = ASTIndentedCodeBlockDetector()
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].layer_type == LayerType.INDENTED_CODE_BLOCK
        assert results[0].attributes["line_count"] == "2"

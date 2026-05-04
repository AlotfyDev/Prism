"""Tests for footnote reference detection and handling."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    FootnoteRefComponent,
    HierarchyNode,
    HierarchyTree,
    LayerInstance,
    MarkdownNode,
    NestingMatrix,
    NodeType,
)
from prism.stage2.layers import FootnoteRefCRUD, FootnoteRefDetector, RegexFootnoteRefDetector
from prism.stage2.layers.base import LayerRegistry


class TestFootnoteRefEnum:
    """Test FOOTNOTE_REF LayerType."""

    def test_footnote_ref_exists(self):
        assert LayerType.FOOTNOTE_REF == "footnote_ref"

    def test_footnote_ref_in_all_layer_types(self):
        assert LayerType.FOOTNOTE_REF in LayerType


class TestFootnoteRefComponent:
    """Test FootnoteRefComponent model."""

    def test_basic_creation(self):
        comp = FootnoteRefComponent(
            component_id="footnote_ref:ref1",
            layer_type=LayerType.FOOTNOTE_REF,
            raw_content="[^1]",
            ref_id="1",
            char_start=0,
            char_end=4,
        )
        assert comp.ref_id == "1"
        assert comp.target_id == "1"

    def test_ref_id_extraction(self):
        comp = FootnoteRefComponent(
            component_id="footnote_ref:ref2",
            layer_type=LayerType.FOOTNOTE_REF,
            raw_content="[^note]",
            ref_id="note",
            char_start=10,
            char_end=18,
        )
        assert comp.ref_id == "note"
        assert comp.target_id == "note"

    def test_inherits_from_physical_component(self):
        comp = FootnoteRefComponent(
            component_id="footnote_ref:ref3",
            layer_type=LayerType.FOOTNOTE_REF,
            raw_content="[^cite]",
            ref_id="cite",
            char_start=0,
            char_end=7,
        )
        assert comp.char_length == 7
        assert comp.layer_type == LayerType.FOOTNOTE_REF


class TestFootnoteRefCRUD:
    """Test FootnoteRefCRUD operations."""

    def test_create_basic(self):
        crud = FootnoteRefCRUD()
        comp = crud.create("ref1", "[^1]")
        assert comp.component_id == "footnote_ref:ref1"
        assert comp.ref_id == "1"
        assert comp.layer_type == LayerType.FOOTNOTE_REF

    def test_create_with_explicit_ref_id(self):
        crud = FootnoteRefCRUD()
        comp = crud.create("ref2", "[^source]", ref_id="source")
        assert comp.ref_id == "source"

    def test_create_extracts_ref_id_from_raw(self):
        crud = FootnoteRefCRUD()
        comp = crud.create("ref3", "[^author]")
        assert comp.ref_id == "author"

    def test_create_with_char_offsets(self):
        crud = FootnoteRefCRUD()
        comp = crud.create("ref4", "[^4]", char_start=50, char_end=54)
        assert comp.char_start == 50
        assert comp.char_end == 54

    def test_create_auto_computes_char_end(self):
        crud = FootnoteRefCRUD()
        comp = crud.create("ref5", "[^test]", char_start=10)
        assert comp.char_end == 17  # 10 + len("[^test]")

    def test_get_ref_id(self):
        crud = FootnoteRefCRUD()
        comp = crud.create("ref6", "[^citation]", ref_id="citation")
        assert crud.get_ref_id(comp) == "citation"

    def test_registered_in_layer_registry(self):
        crud = LayerRegistry.get(LayerType.FOOTNOTE_REF)
        assert isinstance(crud, FootnoteRefCRUD)


class TestRegexFootnoteRefDetector:
    """Test RegexFootnoteRefDetector."""

    def test_detect_single_reference(self):
        detector = RegexFootnoteRefDetector()
        source = "Some text[^1] more text."
        nodes = [
            MarkdownNode(
                node_type=NodeType.INLINE,
                raw_content=source,
                char_start=0,
                char_end=len(source),
            )
        ]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].layer_type == LayerType.FOOTNOTE_REF
        assert results[0].attributes["ref_id"] == "1"

    def test_detect_multiple_references(self):
        detector = RegexFootnoteRefDetector()
        source = "Text[^a] and text[^b] end."
        nodes = [
            MarkdownNode(
                node_type=NodeType.INLINE,
                raw_content=source,
                char_start=0,
                char_end=len(source),
            )
        ]
        results = detector.detect(nodes, source)
        assert len(results) == 2
        assert results[0].attributes["ref_id"] == "a"
        assert results[1].attributes["ref_id"] == "b"

    def test_detect_complex_ref_ids(self):
        detector = RegexFootnoteRefDetector()
        source = "See source[^author2023] for details."
        nodes = [
            MarkdownNode(
                node_type=NodeType.INLINE,
                raw_content=source,
                char_start=0,
                char_end=len(source),
            )
        ]
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].attributes["ref_id"] == "author2023"

    def test_no_false_positives(self):
        detector = RegexFootnoteRefDetector()
        source = "No footnotes here, just [regular link](url)."
        nodes = [
            MarkdownNode(
                node_type=NodeType.INLINE,
                raw_content=source,
                char_start=0,
                char_end=len(source),
            )
        ]
        results = detector.detect(nodes, source)
        assert len(results) == 0

    def test_detects_in_inline_nodes(self):
        detector = RegexFootnoteRefDetector()
        source = "Text[^1]"
        nodes = [
            MarkdownNode(
                node_type=NodeType.INLINE,
                raw_content=source,
                char_start=0,
                char_end=len(source),
            )
        ]
        results = detector.detect(nodes, source)
        assert len(results) == 1

    def test_char_offsets_accurate(self):
        detector = RegexFootnoteRefDetector()
        source = "Hello[^1] world[^2]"
        nodes = [
            MarkdownNode(
                node_type=NodeType.INLINE,
                raw_content=source,
                char_start=0,
                char_end=len(source),
            )
        ]
        results = detector.detect(nodes, source)
        assert len(results) == 2
        # [^1] is at position 5-9
        assert results[0].char_start == 5
        assert results[0].char_end == 9
        # [^2] is at position 15-19
        assert results[1].char_start == 15
        assert results[1].char_end == 19


class TestNestingMatrixFootnoteRef:
    """Test NestingMatrix allows footnote_ref in appropriate containers."""

    def test_footnote_ref_is_leaf(self):
        matrix = NestingMatrix.default()
        assert matrix.is_leaf(LayerType.FOOTNOTE_REF)

    def test_footnote_ref_in_paragraph(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.PARAGRAPH, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_in_heading(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.HEADING, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_in_list(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.LIST, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_in_table(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_in_blockquote(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.BLOCKQUOTE, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_in_footnote(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.FOOTNOTE, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_in_task_list(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TASK_LIST, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_not_in_code_block(self):
        matrix = NestingMatrix.default()
        assert not matrix.can_contain(LayerType.CODE_BLOCK, LayerType.FOOTNOTE_REF)

    def test_footnote_ref_not_in_diagram(self):
        matrix = NestingMatrix.default()
        assert not matrix.can_contain(LayerType.DIAGRAM, LayerType.FOOTNOTE_REF)


class TestMapperFootnoteRef:
    """Test ComponentMapper handles FOOTNOTE_REF."""

    def test_mapper_creates_footnote_ref_component(self):
        from prism.stage2.mapper import ComponentMapper

        mapper = ComponentMapper()
        inst = LayerInstance(
            layer_type=LayerType.FOOTNOTE_REF,
            raw_content="[^1]",
            char_start=10,
            char_end=14,
            line_start=0,
            line_end=1,
            attributes={"ref_id": "1"},
            depth=0,
            sibling_index=0,
        )
        hierarchy_node = HierarchyNode(instance=inst, children=[])
        tree = HierarchyTree(root_nodes=[hierarchy_node])

        components = mapper.map(tree)
        assert len(components) == 1
        comp = components[0]
        assert isinstance(comp, FootnoteRefComponent)
        assert comp.ref_id == "1"
        assert comp.char_start == 10
        assert comp.char_end == 14


class TestClassifierFootnoteRef:
    """Test LayerClassifier detects footnote references."""

    def test_classifier_detects_footnote_refs(self):
        from prism.stage2.classifier import LayerClassifier
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        source = "Text[^1] and more[^note] here."

        parser = MarkdownItParser()
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        classifier = LayerClassifier()
        report = classifier.classify(nodes, source)

        refs = report.instances_of(LayerType.FOOTNOTE_REF)
        assert len(refs) == 2
        ref_ids = [r.attributes.get("ref_id") for r in refs]
        assert "1" in ref_ids
        assert "note" in ref_ids


class TestFootnoteRefEndToEnd:
    """End-to-end tests for footnote reference detection."""

    def test_full_pipeline_with_footnote_refs(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.classifier import LayerClassifier
        from prism.stage2.parser import MarkdownItParser

        source = "This is a claim[^1] and another[^source]."

        parser = MarkdownItParser()
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        classifier = LayerClassifier()
        report = classifier.classify(nodes, source)

        refs = report.instances_of(LayerType.FOOTNOTE_REF)
        assert len(refs) == 2

    def test_paragraph_with_refs_and_other_inlines(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.classifier import LayerClassifier
        from prism.stage2.parser import MarkdownItParser

        source = "Text `code` and **bold**[^1] with [link](url)[^2]."

        parser = MarkdownItParser()
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        classifier = LayerClassifier()
        report = classifier.classify(nodes, source)

        refs = report.instances_of(LayerType.FOOTNOTE_REF)
        assert len(refs) == 2

    def test_multiple_paragraphs_with_refs(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.classifier import LayerClassifier
        from prism.stage2.parser import MarkdownItParser

        source = "Para one[^1].\n\nPara two[^2].\n\nPara three[^1] again."

        parser = MarkdownItParser()
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        classifier = LayerClassifier()
        report = classifier.classify(nodes, source)

        refs = report.instances_of(LayerType.FOOTNOTE_REF)
        assert len(refs) == 3

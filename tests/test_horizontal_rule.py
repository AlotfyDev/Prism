"""Tests for Horizontal Rule detection, CRUD, and mapper integration."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HRuleStyle,
    HorizontalRuleComponent,
    HierarchyNode,
    HierarchyTree,
    LayerInstance,
    MarkdownNode,
    NodeType,
)
from prism.stage2.layers.horizontal_rule import HRCRUD
from prism.stage2.layers.specific_detectors import ASTHRDetector
from prism.stage2.mapper import ComponentMapper


class TestASTHRDetector:
    """Test AST-based horizontal rule detector."""

    def test_detect_dash_hr(self):
        detector = ASTHRDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.HR,
                raw_content="---",
                char_start=0,
                char_end=3,
                attributes={"markup": "---"},
            )
        ]
        results = detector.detect(nodes, "---")
        assert len(results) == 1
        assert results[0].layer_type == LayerType.HORIZONTAL_RULE
        assert results[0].attributes["style"] == "dash"

    def test_detect_star_hr(self):
        detector = ASTHRDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.HR,
                raw_content="***",
                char_start=0,
                char_end=3,
                attributes={"markup": "***"},
            )
        ]
        results = detector.detect(nodes, "***")
        assert len(results) == 1
        assert results[0].layer_type == LayerType.HORIZONTAL_RULE
        assert results[0].attributes["style"] == "star"

    def test_detect_underscore_hr(self):
        detector = ASTHRDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.HR,
                raw_content="___",
                char_start=0,
                char_end=3,
                attributes={"markup": "___"},
            )
        ]
        results = detector.detect(nodes, "___")
        assert len(results) == 1
        assert results[0].layer_type == LayerType.HORIZONTAL_RULE
        assert results[0].attributes["style"] == "underscore"

    def test_detect_longer_hr(self):
        detector = ASTHRDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.HR,
                raw_content="-----",
                char_start=0,
                char_end=5,
                attributes={"markup": "-----"},
            )
        ]
        results = detector.detect(nodes, "-----")
        assert len(results) == 1
        assert results[0].attributes["style"] == "dash"

    def test_no_hr_in_text(self):
        detector = ASTHRDetector()
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

    def test_multiple_hrs(self):
        detector = ASTHRDetector()
        nodes = [
            MarkdownNode(
                node_type=NodeType.HR,
                raw_content="---",
                char_start=0,
                char_end=3,
                attributes={"markup": "---"},
            ),
            MarkdownNode(
                node_type=NodeType.HR,
                raw_content="***",
                char_start=5,
                char_end=8,
                attributes={"markup": "***"},
            ),
        ]
        results = detector.detect(nodes, "---\n\n***")
        assert len(results) == 2
        assert results[0].attributes["style"] == "dash"
        assert results[1].attributes["style"] == "star"


class TestHRCRUD:
    """Test HRCRUD operations."""

    def test_create_dash_hr(self):
        crud = HRCRUD()
        hr = crud.create("hr1", "---", char_start=0, char_end=3)
        assert hr.component_id == "horizontal_rule:hr1"
        assert hr.layer_type == LayerType.HORIZONTAL_RULE
        assert hr.raw_content == "---"
        assert hr.style == HRuleStyle.DASH
        assert hr.char_start == 0
        assert hr.char_end == 3

    def test_create_star_hr(self):
        crud = HRCRUD()
        hr = crud.create("hr2", "***", char_start=5, char_end=8)
        assert hr.style == HRuleStyle.STAR

    def test_create_underscore_hr(self):
        crud = HRCRUD()
        hr = crud.create("hr3", "___", char_start=10, char_end=13)
        assert hr.style == HRuleStyle.UNDERSCORE

    def test_create_with_explicit_style(self):
        crud = HRCRUD()
        hr = crud.create("hr4", "---", style=HRuleStyle.STAR, char_start=0, char_end=3)
        assert hr.style == HRuleStyle.STAR

    def test_create_with_string_style(self):
        crud = HRCRUD()
        hr = crud.create("hr5", "---", style="star", char_start=0, char_end=3)
        assert hr.style == HRuleStyle.STAR

    def test_create_with_invalid_string_style_defaults_to_dash(self):
        crud = HRCRUD()
        hr = crud.create("hr6", "___", style="invalid", char_start=0, char_end=3)
        assert hr.style == HRuleStyle.DASH

    def test_set_style(self):
        crud = HRCRUD()
        hr = crud.create("hr7", "---", char_start=0, char_end=3)
        assert hr.style == HRuleStyle.DASH

        crud.set_style(hr, HRuleStyle.STAR)
        assert hr.style == HRuleStyle.STAR

    def test_auto_detect_style_from_raw_content(self):
        crud = HRCRUD()
        hr = crud.create("hr8", "*****", char_start=0, char_end=5)
        assert hr.style == HRuleStyle.STAR

    def test_char_end_auto_computed(self):
        crud = HRCRUD()
        hr = crud.create("hr9", "---", char_start=10)
        assert hr.char_start == 10
        assert hr.char_end == 13

    def test_layer_type_property(self):
        crud = HRCRUD()
        assert crud.layer_type == LayerType.HORIZONTAL_RULE


class TestHRMapperIntegration:
    """Test ComponentMapper integration for HorizontalRuleComponent."""

    def test_mapper_creates_horizontal_rule_component(self):
        mapper = ComponentMapper()
        inst = LayerInstance(
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="---",
            char_start=0,
            char_end=3,
            line_start=0,
            line_end=1,
            attributes={"style": "dash"},
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
        assert isinstance(comp, HorizontalRuleComponent)
        assert comp.raw_content == "---"
        assert comp.style == HRuleStyle.DASH

    def test_mapper_creates_star_hr(self):
        mapper = ComponentMapper()
        inst = LayerInstance(
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="***",
            char_start=0,
            char_end=3,
            line_start=0,
            line_end=1,
            attributes={"style": "star"},
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
        assert isinstance(comp, HorizontalRuleComponent)
        assert comp.style == HRuleStyle.STAR


class TestHREndToEnd:
    """End-to-end tests: parser → detector → mapper."""

    def test_full_pipeline_dash_hr(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "Hello\n\n---\n\nWorld"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        # Find HR node
        hr_nodes = [n for n in nodes if n.node_type == NodeType.HR]
        assert len(hr_nodes) == 1
        assert hr_nodes[0].raw_content.strip() == "---"
        markup = hr_nodes[0].attributes.get("markup", "")
        assert markup.startswith("-")

        # Detect
        detector = ASTHRDetector()
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].attributes["style"] == "dash"

    def test_full_pipeline_star_hr(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "***"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        hr_nodes = [n for n in nodes if n.node_type == NodeType.HR]
        assert len(hr_nodes) == 1

        detector = ASTHRDetector()
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].attributes["style"] == "star"

    def test_full_pipeline_underscore_hr(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "___"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        hr_nodes = [n for n in nodes if n.node_type == NodeType.HR]
        assert len(hr_nodes) == 1

        detector = ASTHRDetector()
        results = detector.detect(nodes, source)
        assert len(results) == 1
        assert results[0].attributes["style"] == "underscore"

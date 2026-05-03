"""Tests for Stage2GraphState model."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyTree,
    LayerInstance,
    MarkdownNode,
    NodeType,
    PhysicalComponent,
)
from prism.stage2.graph.state import Stage2GraphState


class TestStage2GraphState:
    def test_default_state(self):
        state = Stage2GraphState()
        assert state.source_text == ""
        assert state.nodes == []
        assert state.report is None
        assert state.tree is None
        assert state.components == []
        assert state.token_mapping == {}
        assert state.stage2_output is None
        assert state.errors == []
        assert state.current_step == "init"
        assert state.retry_count == {}

    def test_has_error_false_when_empty(self):
        state = Stage2GraphState()
        assert not state.has_error()

    def test_has_error_true_with_errors(self):
        state = Stage2GraphState(errors=["test error"])
        assert state.has_error()

    def test_last_error_none_when_empty(self):
        state = Stage2GraphState()
        assert state.last_error() is None

    def test_last_error_returns_last(self):
        state = Stage2GraphState(errors=["first", "second"])
        assert state.last_error() == "second"

    def test_populate_nodes(self):
        node = MarkdownNode(
            node_type=NodeType.HEADING,
            raw_content="# Title",
        )
        state = Stage2GraphState(nodes=[node])
        assert len(state.nodes) == 1
        assert state.nodes[0].node_type == NodeType.HEADING

    def test_populate_report(self):
        report = DetectedLayersReport(source_text="text")
        state = Stage2GraphState(report=report)
        assert state.report is not None
        assert state.report.source_text == "text"

    def test_populate_tree(self):
        tree = HierarchyTree()
        state = Stage2GraphState(tree=tree)
        assert state.tree is not None

    def test_progressive_accumulation(self):
        state = Stage2GraphState(source_text="# Title\n\nText")
        state.nodes = [MarkdownNode(
            node_type=NodeType.HEADING,
            raw_content="# Title",
        )]
        state.report = DetectedLayersReport(source_text=state.source_text)
        state.tree = HierarchyTree()

        assert state.source_text != ""
        assert len(state.nodes) > 0
        assert state.report is not None
        assert state.tree is not None
        assert state.stage2_output is None  # Not yet populated

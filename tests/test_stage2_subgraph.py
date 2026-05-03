"""LangGraph subgraph integration tests for Stage 2."""

import pytest

from prism.schemas.enums import LayerType
from prism.stage2.graph import build_stage2_subgraph
from prism.stage2.graph.state import Stage2GraphState


class TestStage2Subgraph:
    """Integration tests for the full Stage 2 LangGraph subgraph."""

    def test_full_subgraph_execution(self):
        """Test that the subgraph executes all steps successfully."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke(
            {"source_text": "# Heading\n\nParagraph text"}
        )
        assert result.get("stage2_output") is not None

    def test_subgraph_produces_heading(self):
        """Test that the subgraph detects heading layers."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke(
            {"source_text": "# Title\n\nSome paragraph text"}
        )
        output = result.get("stage2_output")
        assert output is not None
        assert LayerType.HEADING in output.layer_types

    def test_subgraph_produces_paragraph(self):
        """Test that the subgraph detects paragraph layers."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke(
            {"source_text": "# Title\n\nHello world paragraph"}
        )
        output = result.get("stage2_output")
        assert output is not None
        assert LayerType.PARAGRAPH in output.layer_types

    def test_subgraph_empty_input(self):
        """Test that the subgraph handles empty input gracefully."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke({"source_text": ""})
        # Should halt because parser produces no nodes
        assert len(result.get("errors", [])) > 0 or result.get("current_step") == "halted"

    def test_subgraph_with_list(self):
        """Test that the subgraph detects list layers."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke(
            {"source_text": "- Item 1\n- Item 2\n- Item 3"}
        )
        output = result.get("stage2_output")
        assert output is not None
        assert LayerType.LIST in output.layer_types

    def test_subgraph_with_code_block(self):
        """Test that the subgraph detects code block layers."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke(
            {"source_text": "```\nprint('hello')\n```"}
        )
        output = result.get("stage2_output")
        assert output is not None
        assert LayerType.CODE_BLOCK in output.layer_types

    def test_subgraph_accumulates_state(self):
        """Test that state is progressively accumulated."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke(
            {"source_text": "# Title\n\nParagraph text"}
        )
        # All intermediate fields should be populated
        assert len(result.get("nodes", [])) > 0
        assert result.get("report") is not None
        assert result.get("tree") is not None
        assert len(result.get("components", [])) > 0
        assert result.get("stage2_output") is not None


class TestStage2SubgraphValidation:
    """Test validation gates in the subgraph."""

    def test_halts_on_empty_source(self):
        """Empty source should cause parser to fail validation."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke({"source_text": ""})
        # Parser produces no nodes, so validate_parser should fail
        assert len(result.get("errors", [])) > 0 or result.get("current_step") == "halted"


class TestStage2SubgraphConfig:
    """Test subgraph with custom config."""

    def test_default_config(self):
        """Test with default pipeline config."""
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke({"source_text": "# Test"})
        assert result["stage2_output"] is not None

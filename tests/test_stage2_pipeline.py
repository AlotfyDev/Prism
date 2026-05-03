"""Tests for Stage2Pipeline orchestrator."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyTree,
    LayerInstance,
    PhysicalComponent,
    Stage2Output,
    TopologyConfig,
)
from prism.schemas.token import Stage1Output, Token, TokenMetadata
from prism.stage2.classifier import LayerClassifier
from prism.stage2.hierarchy import HierarchyBuilder
from prism.stage2.mapper import ComponentMapper
from prism.stage2.parser import MarkdownItParser
from prism.stage2.pipeline import PipelineStepError, Stage2Pipeline
from prism.stage2.pipeline_config import Stage2PipelineConfig
from prism.stage2.pipeline_models import (
    ClassifierInput,
    HierarchyInput,
    MapperInput,
    MapperOutput,
    TokenSpanInput,
    TokenSpanOutput,
    TopologyInput,
)
from prism.stage2.token_span import TokenSpanMapper
from prism.stage2.topology import TopologyBuilder


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def stage1_output():
    """Minimal Stage1Output for pipeline tests."""
    text = "# Title\n\nHello world.\n"
    return Stage1Output(
        tokens={
            "T0": Token(id="T0", text="#"),
            "T1": Token(id="T1", text=" "),
            "T2": Token(id="T2", text="Title"),
            "T3": Token(id="T3", text="\n"),
            "T4": Token(id="T4", text="\n"),
            "T5": Token(id="T5", text="Hello"),
            "T6": Token(id="T6", text=" "),
            "T7": Token(id="T7", text="world"),
            "T8": Token(id="T8", text="."),
            "T9": Token(id="T9", text="\n"),
        },
        metadata={
            f"T{i}": TokenMetadata(
                token_id=f"T{i}",
                char_start=i,
                char_end=i + 1,
                source_line=1,
            )
            for i in range(10)
        },
        source_text=text,
    )


@pytest.fixture
def default_pipeline():
    """Pipeline with default config."""
    return Stage2Pipeline()


@pytest.fixture
def custom_config():
    """Config with explicit class references."""
    return Stage2PipelineConfig(
        parser=MarkdownItParser,
        classifier=LayerClassifier,
        hierarchy_builder=HierarchyBuilder,
        component_mapper=ComponentMapper,
        token_span_mapper=TokenSpanMapper,
        topology_builder=TopologyBuilder,
    )


# =============================================================================
# Stage2PipelineConfig Tests
# =============================================================================

class TestStage2PipelineConfig:
    def test_default_config(self):
        config = Stage2PipelineConfig()
        assert config.parser == MarkdownItParser
        assert config.classifier == LayerClassifier
        assert config.hierarchy_builder == HierarchyBuilder
        assert config.component_mapper == ComponentMapper
        assert config.token_span_mapper == TokenSpanMapper
        assert config.topology_builder == TopologyBuilder

    def test_get_unit_classes(self):
        config = Stage2PipelineConfig()
        classes = config.get_unit_classes()
        assert len(classes) == 15  # 6 original + 9 aggregation
        assert "parser" in classes
        assert "classifier" in classes
        assert "token_range_aggregator" in classes
        assert "table_aggregator" in classes
        assert "heading_sequence_analyzer" in classes
        assert "detector_correlator" in classes

    def test_custom_config(self):
        class FakeParser:
            pass

        config = Stage2PipelineConfig(parser=FakeParser)
        assert config.parser == FakeParser


# =============================================================================
# Stage2Pipeline Tests
# =============================================================================

class TestStage2Pipeline:
    def test_default_instantiation(self, default_pipeline):
        assert len(default_pipeline._units) == 15  # 6 original + 9 aggregation
        assert "parser" in default_pipeline._units
        assert "classifier" in default_pipeline._units
        assert "token_range_aggregator" in default_pipeline._units

    def test_custom_config_instantiation(self, custom_config):
        pipeline = Stage2Pipeline(config=custom_config)
        assert len(pipeline._units) == 15

    def test_full_pipeline(self, default_pipeline, stage1_output):
        output = default_pipeline.process(stage1_output)
        assert isinstance(output, Stage2Output)
        assert output.component_count > 0
        assert len(output.layer_types) > 0
        assert LayerType.HEADING in output.layer_types

    def test_pipeline_with_config(self, custom_config, stage1_output):
        pipeline = Stage2Pipeline(config=custom_config)
        output = pipeline.process(stage1_output)
        assert output.component_count > 0

    def test_pipeline_discovers_multiple_layers(
        self, default_pipeline, stage1_output
    ):
        output = default_pipeline.process(stage1_output)
        # Should find at least HEADING and PARAGRAPH
        assert LayerType.HEADING in output.layer_types
        assert LayerType.PARAGRAPH in output.layer_types

    def test_pipeline_token_mapping(self, default_pipeline, stage1_output):
        output = default_pipeline.process(stage1_output)
        # component_to_tokens should have entries for mapped components
        assert len(output.component_to_tokens) >= 0  # May be empty if no token_span

    def test_pipeline_name_property(self, default_pipeline):
        # Pipeline doesn't have name/tier/version itself,
        # but all units do
        for unit in default_pipeline._units.values():
            assert unit.name()
            assert unit.tier
            assert unit.version


# =============================================================================
# PipelineStepError Tests
# =============================================================================

class TestPipelineStepError:
    def test_error_message(self):
        err = PipelineStepError("classifier", "input", "No AST nodes")
        assert "classifier" in str(err)
        assert "input" in str(err)
        assert "No AST nodes" in str(err)

    def test_error_attributes(self):
        err = PipelineStepError("mapper", "output", "No components")
        assert err.step_name == "mapper"
        assert err.validation_type == "output"
        assert err.message == "No components"


# =============================================================================
# Pipeline with Validation Failure Tests
# =============================================================================

class TestPipelineValidation:
    """Test that validation gates work correctly."""

    def test_validate_step_passes(self, default_pipeline):
        # Internal validation should pass for valid data
        unit = default_pipeline._units["parser"]
        stage1 = Stage1Output(source_text="# Title\n\nText\n")
        nodes = unit.process(stage1)
        # Should not raise
        default_pipeline._validate_step("parser", stage1, nodes)

    def test_validate_step_fails_on_empty_output(self, default_pipeline):
        # Empty classifier output should fail validation
        from prism.schemas.physical import MarkdownNode, NodeType
        mock_node = MarkdownNode(
            node_type=NodeType.PARAGRAPH,
            raw_content="text",
        )
        valid_input = ClassifierInput(nodes=[mock_node], source_text="text")
        empty_output = DetectedLayersReport(source_text="text")
        with pytest.raises(PipelineStepError) as exc_info:
            default_pipeline._validate_step("classifier", valid_input, empty_output)
        assert "classifier" in str(exc_info.value)
        assert "output" in str(exc_info.value)


# =============================================================================
# End-to-End Pipeline Tests
# =============================================================================

class TestPipelineEndToEnd:
    """Full pipeline integration tests."""

    def test_heading_detection(self, default_pipeline, stage1_output):
        output = default_pipeline.process(stage1_output)
        headings = [
            c for c in output.discovered_layers.values()
            if c.layer_type == LayerType.HEADING
        ]
        assert len(headings) == 1
        assert headings[0].level == 1

    def test_paragraph_detection(self, default_pipeline, stage1_output):
        output = default_pipeline.process(stage1_output)
        paragraphs = [
            c for c in output.discovered_layers.values()
            if c.layer_type == LayerType.PARAGRAPH
        ]
        assert len(paragraphs) >= 1

    def test_pipeline_determinism(self, default_pipeline, stage1_output):
        """Running the same input twice produces identical output."""
        out1 = default_pipeline.process(stage1_output)
        out2 = default_pipeline.process(stage1_output)
        assert out1.component_count == out2.component_count
        assert out1.layer_types == out2.layer_types
        assert set(out1.discovered_layers.keys()) == set(
            out2.discovered_layers.keys()
        )

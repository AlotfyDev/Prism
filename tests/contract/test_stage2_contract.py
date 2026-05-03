"""Contract tests for Stage 2 interfaces.

Verifies that all Stage 2 ProcessingUnits and validation gates
adhere to their interface contracts:
  - Correct input/output types
  - validate_input/validate_output behavior
  - tier/version/name properties
  - Non-mutating input data
"""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyTree,
    LayerInstance,
    MarkdownNode,
    NodeType,
    PhysicalComponent,
    Stage2Input,
    Stage2Output,
    TopologyConfig,
)
from prism.schemas.token import Stage1Output, Token, TokenMetadata
from prism.stage2.classifier import LayerClassifier
from prism.stage2.hierarchy import HierarchyBuilder
from prism.stage2.mapper import ComponentMapper
from prism.stage2.parser import MarkdownItParser
from prism.stage2.token_span import TokenSpanMapper
from prism.stage2.topology import TopologyBuilder
from prism.stage2.pipeline_models import (
    ClassifierInput,
    HierarchyInput,
    MapperInput,
    TokenSpanInput,
    TopologyInput,
    MapperOutput,
    TokenSpanOutput,
)
from prism.stage2.validation_v2 import ValidationV2


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_markdown():
    return "# Title\n\nHello world.\n\n- Item 1\n- Item 2\n"


@pytest.fixture
def stage1_output(sample_markdown):
    return Stage1Output(
        source_text=sample_markdown,
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
            "T10": Token(id="T10", text="\n"),
            "T11": Token(id="T11", text="-"),
            "T12": Token(id="T12", text=" "),
            "T13": Token(id="T13", text="Item"),
            "T14": Token(id="T14", text=" "),
            "T15": Token(id="T15", text="1"),
            "T16": Token(id="T16", text="\n"),
            "T17": Token(id="T17", text="-"),
            "T18": Token(id="T18", text=" "),
            "T19": Token(id="T19", text="Item"),
            "T20": Token(id="T20", text=" "),
            "T21": Token(id="T21", text="2"),
            "T22": Token(id="T22", text="\n"),
        },
        metadata={
            f"T{i}": TokenMetadata(token_id=f"T{i}", char_start=i, char_end=i+1, source_line=1)
            for i in range(23)
        },
    )


@pytest.fixture
def parser():
    return MarkdownItParser()


@pytest.fixture
def classifier():
    return LayerClassifier()


@pytest.fixture
def hierarchy_builder():
    return HierarchyBuilder()


@pytest.fixture
def component_mapper():
    return ComponentMapper()


@pytest.fixture
def token_span_mapper():
    return TokenSpanMapper()


@pytest.fixture
def topology_builder():
    return TopologyBuilder()


@pytest.fixture
def validator():
    return ValidationV2()


# =============================================================================
# Contract: MarkdownItParser
# =============================================================================

class TestParserContract:
    def test_has_required_properties(self, parser):
        """Contract: ProcessingUnit must have tier, version, name()."""
        assert hasattr(parser, "tier")
        assert hasattr(parser, "version")
        assert callable(getattr(parser, "name", None))
        assert isinstance(parser.tier, str)
        assert isinstance(parser.version, str)
        assert isinstance(parser.name(), str)

    def test_process_returns_list_of_markdown_node(self, parser, stage1_output):
        """Contract: process(Stage1Output) -> list[MarkdownNode]."""
        result = parser.process(stage1_output)
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], MarkdownNode)

    def test_validate_input_returns_tuple(self, parser, stage1_output):
        """Contract: validate_input -> tuple[bool, str]."""
        valid, msg = parser.validate_input(stage1_output)
        assert isinstance(valid, bool)
        assert isinstance(msg, str)

    def test_validate_output_returns_tuple(self, parser, stage1_output):
        """Contract: validate_output -> tuple[bool, str]."""
        nodes = parser.process(stage1_output)
        valid, msg = parser.validate_output(nodes)
        assert isinstance(valid, bool)
        assert isinstance(msg, str)

    def test_empty_input_returns_empty_list(self, parser):
        """Contract: empty source_text -> empty list."""
        empty = Stage1Output(source_text="")
        result = parser.process(empty)
        assert result == []


# =============================================================================
# Contract: LayerClassifier
# =============================================================================

class TestClassifierContract:
    def test_has_required_properties(self, classifier):
        assert hasattr(classifier, "tier")
        assert hasattr(classifier, "version")
        assert callable(getattr(classifier, "name", None))

    def test_classify_returns_detected_layers_report(self, classifier, parser, stage1_output):
        """Contract: classify(nodes, source_text) -> DetectedLayersReport."""
        nodes = parser.process(stage1_output)
        result = classifier.classify(nodes, stage1_output.source_text)
        assert isinstance(result, DetectedLayersReport)

    def test_validate_input_returns_tuple(self, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        valid, msg = classifier.validate_input(
            ClassifierInput(nodes=nodes, source_text=stage1_output.source_text)
        )
        assert isinstance(valid, bool)
        assert isinstance(msg, str)

    def test_validate_output_returns_tuple(self, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        valid, msg = classifier.validate_output(report)
        assert isinstance(valid, bool)
        assert isinstance(msg, str)


# =============================================================================
# Contract: HierarchyBuilder
# =============================================================================

class TestHierarchyBuilderContract:
    def test_has_required_properties(self, hierarchy_builder):
        assert hasattr(hierarchy_builder, "tier")
        assert hasattr(hierarchy_builder, "version")
        assert callable(getattr(hierarchy_builder, "name", None))

    def test_build_returns_hierarchy_tree(self, hierarchy_builder, classifier, parser, stage1_output):
        """Contract: build(report) -> HierarchyTree."""
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        result = hierarchy_builder.build(report)
        assert isinstance(result, HierarchyTree)

    def test_validate_input_returns_tuple(self, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        valid, msg = hierarchy_builder.validate_input(HierarchyInput(report=report))
        assert isinstance(valid, bool)
        assert isinstance(msg, str)

    def test_validate_output_returns_tuple(self, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        valid, msg = hierarchy_builder.validate_output(tree)
        assert isinstance(valid, bool)
        assert isinstance(msg, str)


# =============================================================================
# Contract: ComponentMapper
# =============================================================================

class TestComponentMapperContract:
    def test_has_required_properties(self, component_mapper):
        assert hasattr(component_mapper, "tier")
        assert hasattr(component_mapper, "version")
        assert callable(getattr(component_mapper, "name", None))

    def test_map_returns_list_of_physical_component(self, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        """Contract: map(tree) -> list[PhysicalComponent]."""
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        result = component_mapper.map(tree)
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], PhysicalComponent)

    def test_validate_input_returns_tuple(self, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        valid, msg = component_mapper.validate_input(MapperInput(tree=tree))
        assert isinstance(valid, bool)
        assert isinstance(msg, str)

    def test_validate_output_returns_tuple(self, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        valid, msg = component_mapper.validate_output(MapperOutput(components=components))
        assert isinstance(valid, bool)
        assert isinstance(msg, str)


# =============================================================================
# Contract: TokenSpanMapper
# =============================================================================

class TestTokenSpanMapperContract:
    def test_has_required_properties(self, token_span_mapper):
        assert hasattr(token_span_mapper, "tier")
        assert hasattr(token_span_mapper, "version")
        assert callable(getattr(token_span_mapper, "name", None))

    def test_map_returns_dict(self, token_span_mapper, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        """Contract: map(components, stage1_output) -> dict[str, list[str]]."""
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        result = token_span_mapper.map(components, stage1_output)
        assert isinstance(result, dict)
        if result:
            key, value = next(iter(result.items()))
            assert isinstance(key, str)
            assert isinstance(value, list)

    def test_validate_input_returns_tuple(self, token_span_mapper, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        valid, msg = token_span_mapper.validate_input(
            TokenSpanInput(components=components, stage1_output=stage1_output)
        )
        assert isinstance(valid, bool)
        assert isinstance(msg, str)

    def test_validate_output_returns_tuple(self, token_span_mapper, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        mapping = token_span_mapper.map(components, stage1_output)
        valid, msg = token_span_mapper.validate_output(
            TokenSpanOutput(component_to_tokens=mapping)
        )
        assert isinstance(valid, bool)
        assert isinstance(msg, str)


# =============================================================================
# Contract: TopologyBuilder
# =============================================================================

class TestTopologyBuilderContract:
    def test_has_required_properties(self, topology_builder):
        assert hasattr(topology_builder, "tier")
        assert hasattr(topology_builder, "version")
        assert callable(getattr(topology_builder, "name", None))

    def test_build_returns_stage2_output(self, topology_builder, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        """Contract: build(components, token_mapping) -> Stage2Output."""
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        result = topology_builder.build(components, {})
        assert isinstance(result, Stage2Output)

    def test_validate_input_returns_tuple(self, topology_builder, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        valid, msg = topology_builder.validate_input(
            TopologyInput(components=components, token_mapping={})
        )
        assert isinstance(valid, bool)
        assert isinstance(msg, str)

    def test_validate_output_returns_tuple(self, topology_builder, component_mapper, hierarchy_builder, classifier, parser, stage1_output):
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        output = topology_builder.build(components, {})
        valid, msg = topology_builder.validate_output(output)
        assert isinstance(valid, bool)
        assert isinstance(msg, str)


# =============================================================================
# Contract: ValidationV2
# =============================================================================

class TestValidationV2Contract:
    def test_has_required_properties(self, validator):
        """Contract: ValidationUnit must have name()."""
        assert callable(getattr(validator, "name", None))
        assert isinstance(validator.name(), str)

    def test_validate_returns_validation_report(self, validator):
        """Contract: validate(Stage2Output) -> ValidationReport."""
        from prism.core.validation_unit import ValidationReport
        output = Stage2Output()
        result = validator.validate(output)
        assert isinstance(result, ValidationReport)

    def test_validate_wrong_type_returns_failed_report(self, validator):
        """Contract: wrong input type -> failed report with V2.0 check."""
        result = validator.validate("not_stage2_output")
        assert not result.passed
        assert result.checks[0].id == "V2.0"


# =============================================================================
# Contract: Full Pipeline
# =============================================================================

class TestFullPipelineContract:
    """Verify the complete Stage 2 pipeline adheres to interface contracts."""

    def test_end_to_end_produces_valid_stage2_output(self, parser, classifier, hierarchy_builder, component_mapper, topology_builder, stage1_output):
        """Contract: Full pipeline produces valid Stage2Output."""
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        output = topology_builder.build(components, {})
        assert isinstance(output, Stage2Output)
        assert output.component_count > 0

    def test_validation_passes_on_pipeline_output(self, validator, parser, classifier, hierarchy_builder, component_mapper, token_span_mapper, topology_builder, stage1_output):
        """Contract: Pipeline output passes ValidationV2."""
        nodes = parser.process(stage1_output)
        report = classifier.classify(nodes, stage1_output.source_text)
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)

        # Assign token spans manually (TokenSpanMapper needs char offsets)
        for i, comp in enumerate(components):
            comp.token_span = (i * 5, i * 5 + 3)

        token_mapping = token_span_mapper.map(components, stage1_output)
        output = topology_builder.build(components, token_mapping)
        validation_report = validator.validate(output)
        assert validation_report.passed

    def test_pipeline_is_deterministic(self, parser, classifier, hierarchy_builder, component_mapper, topology_builder, stage1_output):
        """Contract: Pipeline produces same output for same input."""
        def run_pipeline():
            nodes = parser.process(stage1_output)
            report = classifier.classify(nodes, stage1_output.source_text)
            tree = hierarchy_builder.build(report)
            components = component_mapper.map(tree)
            return topology_builder.build(components, {})

        output1 = run_pipeline()
        output2 = run_pipeline()

        assert output1.component_count == output2.component_count
        assert output1.layer_types == output2.layer_types
        assert output1.is_single_layer == output2.is_single_layer

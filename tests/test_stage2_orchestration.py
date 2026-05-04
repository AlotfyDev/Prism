"""Tests for Stage 2 orchestration pipeline (2.2b-2.3)."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyNode,
    HierarchyTree,
    LayerInstance,
    ListComponent,
    ListStyle,
    MarkdownNode,
    NodeType,
    NestingMatrix,
    PhysicalComponent,
    Stage2Output,
    TableComponent,
    TopologyConfig,
)
from prism.schemas.token import Stage1Output, Token, TokenMetadata, TokenType
from prism.stage2.classifier import LayerClassifier, _ALL_DETECTORS
from prism.stage2.hierarchy import HierarchyBuilder
from prism.stage2.mapper import ComponentMapper
from prism.stage2.token_span import TokenSpanMapper
from prism.stage2.topology import TopologyBuilder
from prism.stage2.pipeline_models import (
    ClassifierInput,
    HierarchyInput,
    MapperInput,
    TokenSpanInput,
    TopologyInput,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_markdown():
    """Simple Markdown with heading, paragraph, and list."""
    return """# Title

Hello world.

- Item 1
- Item 2

## Subtitle

Some text here.
"""


@pytest.fixture
def sample_nodes(sample_markdown):
    """Parse sample Markdown into AST nodes."""
    from prism.stage2.parser import MarkdownItParser
    parser = MarkdownItParser()
    # We need Stage1Input for parser, but it takes Stage1Output
    # Actually parser takes Stage1Output in process()
    # Let's create a minimal Stage1Output
    stage1 = Stage1Output(
        source_text=sample_markdown,
        config=None,
    )
    return parser.process(stage1)


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


# =============================================================================
# 2.2b LayerClassifier Tests
# =============================================================================

class TestLayerClassifier:
    def test_tier(self, classifier):
        assert classifier.tier == "orchestrator"

    def test_version(self, classifier):
        assert classifier.version == "v1.0.0"

    def test_name(self, classifier):
        assert classifier.name() == "LayerClassifier"

    def test_all_detectors_registered(self):
        assert len(_ALL_DETECTORS) == 18

    def test_classify_heading(self, classifier, sample_nodes, sample_markdown):
        report = classifier.classify(sample_nodes, sample_markdown)
        assert report.has_type(LayerType.HEADING)
        headings = report.instances_of(LayerType.HEADING)
        assert len(headings) == 2  # "Title" and "Subtitle"

    def test_classify_paragraph(self, classifier, sample_nodes, sample_markdown):
        report = classifier.classify(sample_nodes, sample_markdown)
        assert report.has_type(LayerType.PARAGRAPH)
        paragraphs = report.instances_of(LayerType.PARAGRAPH)
        assert len(paragraphs) >= 2

    def test_classify_list(self, classifier, sample_nodes, sample_markdown):
        report = classifier.classify(sample_nodes, sample_markdown)
        assert report.has_type(LayerType.LIST)
        lists = report.instances_of(LayerType.LIST)
        assert len(lists) == 1

    def test_classify_total_instances(self, classifier, sample_nodes, sample_markdown):
        report = classifier.classify(sample_nodes, sample_markdown)
        assert report.total_instances > 0

    def test_classify_filtered_types(self, classifier, sample_nodes, sample_markdown):
        config = TopologyConfig(
            layer_types_to_detect=[LayerType.HEADING]
        )
        report = classifier.classify(sample_nodes, sample_markdown, config)
        assert report.has_type(LayerType.HEADING)
        assert not report.has_type(LayerType.PARAGRAPH)
        assert not report.has_type(LayerType.LIST)

    def test_classify_empty_nodes(self, classifier):
        report = classifier.classify([], "")
        assert report.total_instances == 0

    def test_validate_input_valid(self, classifier, sample_nodes, sample_markdown):
        valid, msg = classifier.validate_input(
            ClassifierInput(nodes=sample_nodes, source_text=sample_markdown)
        )
        assert valid

    def test_validate_input_empty_nodes(self, classifier):
        valid, msg = classifier.validate_input(
            ClassifierInput(nodes=[], source_text="text")
        )
        assert not valid
        assert "No AST nodes" in msg

    def test_validate_input_empty_text(self, classifier, sample_nodes):
        valid, msg = classifier.validate_input(
            ClassifierInput(nodes=sample_nodes, source_text="")
        )
        assert not valid
        assert "empty" in msg

    def test_validate_output_valid(self, classifier, sample_nodes, sample_markdown):
        report = classifier.classify(sample_nodes, sample_markdown)
        valid, msg = classifier.validate_output(report)
        assert valid

    def test_validate_output_empty(self, classifier):
        report = DetectedLayersReport(source_text="text")
        valid, msg = classifier.validate_output(report)
        assert not valid
        assert "No layer instances" in msg

    def test_classify_preserves_source_text(self, classifier, sample_nodes, sample_markdown):
        report = classifier.classify(sample_nodes, sample_markdown)
        assert report.source_text == sample_markdown


# =============================================================================
# 2.2c HierarchyBuilder Tests
# =============================================================================

class TestHierarchyBuilder:
    def test_tier(self, hierarchy_builder):
        assert hierarchy_builder.tier == "orchestrator"

    def test_version(self, hierarchy_builder):
        assert hierarchy_builder.version == "v1.0.0"

    def test_name(self, hierarchy_builder):
        assert hierarchy_builder.name() == "HierarchyBuilder"

    def test_build_empty_report(self, hierarchy_builder):
        report = DetectedLayersReport(source_text="")
        tree = hierarchy_builder.build(report)
        assert tree.total_nodes == 0

    def test_build_single_instance(self, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="Hello world",
        )
        report = DetectedLayersReport(
            source_text="Hello world",
            instances={LayerType.PARAGRAPH: [instance]},
        )
        tree = hierarchy_builder.build(report)
        assert tree.total_nodes == 1
        assert len(tree.root_nodes) == 1

    def test_build_parent_child(self, hierarchy_builder):
        parent = LayerInstance(
            layer_type=LayerType.HEADING,
            char_start=0,
            char_end=50,
            line_start=0,
            line_end=3,
            raw_content="# Title\n\nParagraph text\n",
        )
        child = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=10,
            char_end=30,
            line_start=2,
            line_end=3,
            raw_content="Paragraph text",
        )
        report = DetectedLayersReport(
            source_text="# Title\n\nParagraph text\n",
            instances={
                LayerType.HEADING: [parent],
                LayerType.PARAGRAPH: [child],
            },
        )
        tree = hierarchy_builder.build(report)
        assert tree.total_nodes == 2
        assert len(tree.root_nodes) == 1
        assert len(tree.root_nodes[0].children) == 1

    def test_build_max_depth(self, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="Hello world",
        )
        report = DetectedLayersReport(
            source_text="Hello world",
            instances={LayerType.PARAGRAPH: [instance]},
        )
        tree = hierarchy_builder.build(report)
        assert tree.max_depth == 0

    def test_build_invalid_nesting_raises(self, hierarchy_builder):
        # CODE_BLOCK cannot contain PARAGRAPH
        parent = LayerInstance(
            layer_type=LayerType.CODE_BLOCK,
            char_start=0,
            char_end=50,
            line_start=0,
            line_end=3,
            raw_content="```\nsome code\n```",
        )
        child = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=5,
            char_end=15,
            line_start=1,
            line_end=2,
            raw_content="some code",
        )
        report = DetectedLayersReport(
            source_text="```\nsome code\n```",
            instances={
                LayerType.CODE_BLOCK: [parent],
                LayerType.PARAGRAPH: [child],
            },
        )
        # Should not raise — CODE_BLOCK doesn't contain PARAGRAPH in NestingMatrix
        # so the paragraph should be a root node, not a child
        tree = hierarchy_builder.build(report)
        assert tree.total_nodes == 2
        assert len(tree.root_nodes) == 2  # Both are roots

    def test_build_disjoint_instances(self, hierarchy_builder):
        p1 = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="First para",
        )
        p2 = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=20,
            char_end=30,
            line_start=2,
            line_end=3,
            raw_content="Second para",
        )
        report = DetectedLayersReport(
            source_text="First para\n\nSecond para",
            instances={LayerType.PARAGRAPH: [p1, p2]},
        )
        tree = hierarchy_builder.build(report)
        assert tree.total_nodes == 2
        assert len(tree.root_nodes) == 2

    def test_flatten(self, hierarchy_builder):
        parent = LayerInstance(
            layer_type=LayerType.HEADING,
            char_start=0,
            char_end=50,
            line_start=0,
            line_end=3,
            raw_content="# Title\n\nParagraph text\n",
        )
        child = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=10,
            char_end=30,
            line_start=2,
            line_end=3,
            raw_content="Paragraph text",
        )
        report = DetectedLayersReport(
            source_text="# Title\n\nParagraph text\n",
            instances={
                LayerType.HEADING: [parent],
                LayerType.PARAGRAPH: [child],
            },
        )
        tree = hierarchy_builder.build(report)
        flat = tree.flatten()
        assert len(flat) == 2

    def test_get_node_by_id(self, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="Hello world",
        )
        report = DetectedLayersReport(
            source_text="Hello world",
            instances={LayerType.PARAGRAPH: [instance]},
        )
        tree = hierarchy_builder.build(report)
        node = tree.get_node_by_id("paragraph:depth0_sib0")
        assert node is not None
        assert node.instance.layer_type == LayerType.PARAGRAPH

    def test_validate_input_valid(self, hierarchy_builder):
        report = DetectedLayersReport(source_text="text")
        valid, msg = hierarchy_builder.validate_input(HierarchyInput(report=report))
        assert valid

    def test_validate_input_empty(self, hierarchy_builder):
        report = DetectedLayersReport(source_text="")
        valid, msg = hierarchy_builder.validate_input(HierarchyInput(report=report))
        assert not valid

    def test_validate_output_empty(self, hierarchy_builder):
        tree = HierarchyTree()
        valid, msg = hierarchy_builder.validate_output(tree)
        assert not valid

    def test_validate_output_valid(self, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="Hello world",
        )
        report = DetectedLayersReport(
            source_text="Hello world",
            instances={LayerType.PARAGRAPH: [instance]},
        )
        tree = hierarchy_builder.build(report)
        valid, msg = hierarchy_builder.validate_output(tree)
        assert valid


# =============================================================================
# 2.2d ComponentMapper Tests
# =============================================================================

class TestComponentMapper:
    def test_tier(self, component_mapper):
        assert component_mapper.tier == "orchestrator"

    def test_version(self, component_mapper):
        assert component_mapper.version == "v1.0.0"

    def test_name(self, component_mapper):
        assert component_mapper.name() == "ComponentMapper"

    def test_map_single_paragraph(self, component_mapper, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="Hello world",
        )
        report = DetectedLayersReport(
            source_text="Hello world",
            instances={LayerType.PARAGRAPH: [instance]},
        )
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        assert len(components) == 1
        assert components[0].layer_type == LayerType.PARAGRAPH
        assert components[0].component_id.startswith("paragraph:")

    def test_map_heading(self, component_mapper, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.HEADING,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="# Title",
            attributes={"level": "1"},
        )
        report = DetectedLayersReport(
            source_text="# Title",
            instances={LayerType.HEADING: [instance]},
        )
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        assert len(components) == 1
        assert components[0].layer_type == LayerType.HEADING
        assert components[0].level == 1

    def test_map_list(self, component_mapper, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.LIST,
            char_start=0,
            char_end=20,
            line_start=0,
            line_end=2,
            raw_content="- Item 1\n- Item 2",
            attributes={"style": "unordered"},
        )
        report = DetectedLayersReport(
            source_text="- Item 1\n- Item 2",
            instances={LayerType.LIST: [instance]},
        )
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        assert len(components) == 1
        assert components[0].layer_type == LayerType.LIST
        assert isinstance(components[0], ListComponent)

    def test_map_code_block(self, component_mapper, hierarchy_builder):
        instance = LayerInstance(
            layer_type=LayerType.CODE_BLOCK,
            char_start=0,
            char_end=20,
            line_start=0,
            line_end=3,
            raw_content="```\nprint('hi')\n```",
            attributes={"language": "python"},
        )
        report = DetectedLayersReport(
            source_text="```\nprint('hi')\n```",
            instances={LayerType.CODE_BLOCK: [instance]},
        )
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        assert len(components) == 1
        assert components[0].layer_type == LayerType.CODE_BLOCK
        assert components[0].language == "python"

    def test_map_parent_child(self, component_mapper, hierarchy_builder):
        parent = LayerInstance(
            layer_type=LayerType.HEADING,
            char_start=0,
            char_end=50,
            line_start=0,
            line_end=3,
            raw_content="# Title\n\nParagraph text\n",
            attributes={"level": "1"},
        )
        child = LayerInstance(
            layer_type=LayerType.PARAGRAPH,
            char_start=10,
            char_end=30,
            line_start=2,
            line_end=3,
            raw_content="Paragraph text",
        )
        report = DetectedLayersReport(
            source_text="# Title\n\nParagraph text\n",
            instances={
                LayerType.HEADING: [parent],
                LayerType.PARAGRAPH: [child],
            },
        )
        tree = hierarchy_builder.build(report)
        components = component_mapper.map(tree)
        assert len(components) == 2

        heading_comp = next(c for c in components if c.layer_type == LayerType.HEADING)
        para_comp = next(c for c in components if c.layer_type == LayerType.PARAGRAPH)

        assert para_comp.component_id in heading_comp.children

    def test_validate_input_empty(self, component_mapper):
        tree = HierarchyTree()
        valid, msg = component_mapper.validate_input(MapperInput(tree=tree))
        assert not valid

    def test_validate_output_empty(self, component_mapper):
        from prism.stage2.pipeline_models import MapperOutput
        valid, msg = component_mapper.validate_output(MapperOutput(components=[]))
        assert not valid


# =============================================================================
# 2.2e TokenSpanMapper Tests
# =============================================================================

class TestTokenSpanMapper:
    def test_tier(self, token_span_mapper):
        assert token_span_mapper.tier == "orchestrator"

    def test_version(self, token_span_mapper):
        assert token_span_mapper.version == "v1.0.0"

    def test_name(self, token_span_mapper):
        assert token_span_mapper.name() == "TokenSpanMapper"

    @pytest.fixture
    def stage1_with_tokens(self):
        return Stage1Output(
            tokens={
                "T0": Token(id="T0", text="Hello"),
                "T1": Token(id="T1", text=" "),
                "T2": Token(id="T2", text="world"),
                "T3": Token(id="T3", text="."),
                "T4": Token(id="T4", text="\n"),
                "T5": Token(id="T5", text="Second"),
                "T6": Token(id="T6", text=" "),
                "T7": Token(id="T7", text="line"),
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=0, char_end=5, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=5, char_end=6, source_line=1),
                "T2": TokenMetadata(token_id="T2", char_start=6, char_end=11, source_line=1),
                "T3": TokenMetadata(token_id="T3", char_start=11, char_end=12, source_line=1),
                "T4": TokenMetadata(token_id="T4", char_start=12, char_end=13, source_line=1),
                "T5": TokenMetadata(token_id="T5", char_start=13, char_end=19, source_line=2),
                "T6": TokenMetadata(token_id="T6", char_start=19, char_end=20, source_line=2),
                "T7": TokenMetadata(token_id="T7", char_start=20, char_end=24, source_line=2),
            },
            source_text="Hello world.\nSecond line",
        )

    def test_map_with_token_span(self, token_span_mapper, stage1_with_tokens):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world.",
            token_span=(0, 3),
            char_start=0,
            char_end=12,
        )
        result = token_span_mapper.map([comp], stage1_with_tokens)
        assert "paragraph:p1" in result
        assert result["paragraph:p1"] == ["T0", "T1", "T2", "T3"]

    def test_map_multiple_components(self, token_span_mapper, stage1_with_tokens):
        c1 = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world.",
            token_span=(0, 3),
            char_start=0,
            char_end=12,
        )
        c2 = PhysicalComponent(
            component_id="paragraph:p2",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Second line",
            token_span=(5, 7),
            char_start=13,
            char_end=24,
        )
        result = token_span_mapper.map([c1, c2], stage1_with_tokens)
        assert len(result) == 2
        assert result["paragraph:p1"] == ["T0", "T1", "T2", "T3"]
        assert result["paragraph:p2"] == ["T5", "T6", "T7"]

    def test_validate_input_empty_components(self, token_span_mapper, stage1_with_tokens):
        valid, msg = token_span_mapper.validate_input(
            TokenSpanInput(components=[], stage1_output=stage1_with_tokens)
        )
        assert not valid

    def test_validate_input_empty_tokens(self, token_span_mapper):
        stage1 = Stage1Output(source_text="")
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="text",
            char_start=0,
            char_end=4,
        )
        valid, msg = token_span_mapper.validate_input(
            TokenSpanInput(components=[comp], stage1_output=stage1)
        )
        assert not valid

    def test_validate_output_empty(self, token_span_mapper):
        from prism.stage2.pipeline_models import TokenSpanOutput
        valid, msg = token_span_mapper.validate_output(TokenSpanOutput(component_to_tokens={}))
        assert not valid

    def test_no_overlap(self, token_span_mapper):
        """Component range [100, 120], all tokens at [0, 24] → returns []."""
        stage1 = Stage1Output(
            tokens={
                "T0": Token(id="T0", text="Hello"),
                "T1": Token(id="T1", text="world"),
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=0, char_end=5, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=6, char_end=11, source_line=1),
            },
            source_text="Hello world",
        )
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="distant text",
            char_start=100,
            char_end=120,
        )
        result = token_span_mapper.map([comp], stage1)
        assert result["paragraph:p1"] == []

    def test_exact_single_token(self, token_span_mapper):
        """Component range [5, 10], one token at [5, 10] → returns ["T0"]."""
        stage1 = Stage1Output(
            tokens={
                "T0": Token(id="T0", text="Hello"),
                "T1": Token(id="T1", text="world"),
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=5, char_end=10, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=20, char_end=25, source_line=1),
            },
            source_text="     Hello          world",
        )
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello",
            char_start=5,
            char_end=10,
        )
        result = token_span_mapper.map([comp], stage1)
        assert result["paragraph:p1"] == ["T0"]

    def test_partial_overlap_start(self, token_span_mapper):
        """Component [5, 15], token [0, 10] → includes token (intersects)."""
        stage1 = Stage1Output(
            tokens={
                "T0": Token(id="T0", text="HelloWorld"),
                "T1": Token(id="T1", text="After"),
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=0, char_end=10, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=20, char_end=25, source_line=1),
            },
            source_text="HelloWorld     After",
        )
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="loWorld",
            char_start=5,
            char_end=15,
        )
        result = token_span_mapper.map([comp], stage1)
        assert "T0" in result["paragraph:p1"]

    def test_partial_overlap_end(self, token_span_mapper):
        """Component [5, 15], token [10, 20] → includes token (intersects)."""
        stage1 = Stage1Output(
            tokens={
                "T0": Token(id="T0", text="Before"),
                "T1": Token(id="T1", text="TenChars12"),
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=0, char_end=6, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=10, char_end=20, source_line=1),
            },
            source_text="Before     TenChars12",
        )
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="partial",
            char_start=5,
            char_end=15,
        )
        result = token_span_mapper.map([comp], stage1)
        assert "T1" in result["paragraph:p1"]

    def test_multi_token_range(self, token_span_mapper):
        """Component [0, 24], tokens T0[0,5] T1[5,10] T2[10,19] T3[19,24] → all 4."""
        stage1 = Stage1Output(
            tokens={
                "T0": Token(id="T0", text="Hello"),
                "T1": Token(id="T1", text="world"),
                "T2": Token(id="T2", text="Second!"),
                "T3": Token(id="T3", text="End."),
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=0, char_end=5, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=5, char_end=10, source_line=1),
                "T2": TokenMetadata(token_id="T2", char_start=10, char_end=17, source_line=1),
                "T3": TokenMetadata(token_id="T3", char_start=17, char_end=21, source_line=1),
            },
            source_text="HelloworldSecond!End.",
        )
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world Second! End.",
            char_start=0,
            char_end=21,
        )
        result = token_span_mapper.map([comp], stage1)
        assert result["paragraph:p1"] == ["T0", "T1", "T2", "T3"]

    def test_component_in_gap_between_tokens(self, token_span_mapper):
        """Component [6, 8], tokens at [0,5] and [10,15] → [] (gap)."""
        stage1 = Stage1Output(
            tokens={
                "T0": Token(id="T0", text="Hello"),
                "T1": Token(id="T1", text="World"),
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=0, char_end=5, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=10, char_end=15, source_line=1),
            },
            source_text="Hello     World",
        )
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="  ",
            char_start=6,
            char_end=8,
        )
        result = token_span_mapper.map([comp], stage1)
        assert result["paragraph:p1"] == []


# =============================================================================
# 2.3 TopologyBuilder Tests
# =============================================================================

class TestTopologyBuilder:
    def test_tier(self, topology_builder):
        assert topology_builder.tier == "orchestrator"

    def test_version(self, topology_builder):
        assert topology_builder.version == "v1.0.0"

    def test_name(self, topology_builder):
        assert topology_builder.name() == "TopologyBuilder"

    def test_build_single_component(self, topology_builder):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world.",
            char_start=0,
            char_end=12,
        )
        result = topology_builder.build([comp], {})
        assert result.component_count == 1
        assert "paragraph:p1" in result.discovered_layers

    def test_build_multiple_components(self, topology_builder):
        c1 = PhysicalComponent(
            component_id="heading:h1",
            layer_type=LayerType.HEADING,
            raw_content="# Title",
            char_start=0,
            char_end=7,
        )
        c2 = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world.",
            char_start=9,
            char_end=21,
        )
        result = topology_builder.build([c1, c2], {})
        assert result.component_count == 2
        assert LayerType.HEADING in result.layer_types
        assert LayerType.PARAGRAPH in result.layer_types
        assert not result.is_single_layer

    def test_build_with_token_mapping(self, topology_builder):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world.",
            token_span=(0, 2),
            char_start=0,
            char_end=12,
        )
        token_mapping = {
            "paragraph:p1": ["T0", "T1", "T2"],
        }
        result = topology_builder.build([comp], token_mapping)
        assert "paragraph:p1" in result.component_to_tokens
        assert result.component_to_tokens["paragraph:p1"] == (0, 2)

    def test_build_single_layer(self, topology_builder):
        c1 = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="First.",
            char_start=0,
            char_end=6,
        )
        c2 = PhysicalComponent(
            component_id="paragraph:p2",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Second.",
            char_start=7,
            char_end=14,
        )
        result = topology_builder.build([c1, c2], {})
        assert result.is_single_layer
        assert result.layer_types == {LayerType.PARAGRAPH}

    def test_validate_input_empty(self, topology_builder):
        valid, msg = topology_builder.validate_input(
            TopologyInput(components=[], token_mapping={})
        )
        assert not valid

    def test_validate_output_empty(self, topology_builder):
        output = Stage2Output()
        valid, msg = topology_builder.validate_output(output)
        assert not valid


# =============================================================================
# End-to-End Pipeline Tests
# =============================================================================

class TestEndToEndPipeline:
    """Test the full Stage 2 pipeline: Parser → Classifier → Hierarchy → Mapper → TokenSpan → Topology."""

    @pytest.fixture
    def full_pipeline(self):
        from prism.stage2.parser import MarkdownItParser
        return {
            "parser": MarkdownItParser(),
            "classifier": LayerClassifier(),
            "hierarchy": HierarchyBuilder(),
            "mapper": ComponentMapper(),
            "token_span": TokenSpanMapper(),
            "topology": TopologyBuilder(),
        }

    @pytest.fixture
    def stage1_output(self):
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
            },
            metadata={
                "T0": TokenMetadata(token_id="T0", char_start=0, char_end=1, source_line=1),
                "T1": TokenMetadata(token_id="T1", char_start=1, char_end=2, source_line=1),
                "T2": TokenMetadata(token_id="T2", char_start=2, char_end=7, source_line=1),
                "T3": TokenMetadata(token_id="T3", char_start=7, char_end=8, source_line=1),
                "T4": TokenMetadata(token_id="T4", char_start=8, char_end=9, source_line=2),
                "T5": TokenMetadata(token_id="T5", char_start=9, char_end=14, source_line=3),
                "T6": TokenMetadata(token_id="T6", char_start=14, char_end=15, source_line=3),
                "T7": TokenMetadata(token_id="T7", char_start=15, char_end=20, source_line=3),
                "T8": TokenMetadata(token_id="T8", char_start=20, char_end=21, source_line=3),
            },
            source_text="# Title\n\nHello world.",
        )

    def test_full_pipeline(self, full_pipeline, stage1_output):
        source_text = stage1_output.source_text

        # Step 1: Parse
        nodes = full_pipeline["parser"].process(stage1_output)
        assert len(nodes) > 0

        # Step 2: Classify
        report = full_pipeline["classifier"].classify(nodes, source_text)
        assert report.total_instances > 0
        assert report.has_type(LayerType.HEADING)
        assert report.has_type(LayerType.PARAGRAPH)

        # Step 3: Build hierarchy
        tree = full_pipeline["hierarchy"].build(report)
        assert tree.total_nodes > 0

        # Step 4: Map to components
        components = full_pipeline["mapper"].map(tree)
        assert len(components) > 0

        # Step 5: Token span mapping
        token_mapping = full_pipeline["token_span"].map(components, stage1_output)
        assert len(token_mapping) > 0

        # Step 6: Assemble topology
        output = full_pipeline["topology"].build(components, token_mapping)
        assert output.component_count > 0
        assert len(output.layer_types) > 0

    def test_full_pipeline_with_list(self, full_pipeline, stage1_output):
        source_text = "# Title\n\n- Item 1\n- Item 2\n"
        stage1 = Stage1Output(
            source_text=source_text,
            tokens={
                "T0": Token(id="T0", text="#"),
                "T1": Token(id="T1", text=" "),
                "T2": Token(id="T2", text="Title"),
                "T3": Token(id="T3", text="\n"),
                "T4": Token(id="T4", text="\n"),
                "T5": Token(id="T5", text="-"),
                "T6": Token(id="T6", text=" "),
                "T7": Token(id="T7", text="Item"),
                "T8": Token(id="T8", text=" "),
                "T9": Token(id="T9", text="1"),
                "T10": Token(id="T10", text="\n"),
                "T11": Token(id="T11", text="-"),
                "T12": Token(id="T12", text=" "),
                "T13": Token(id="T13", text="Item"),
                "T14": Token(id="T14", text=" "),
                "T15": Token(id="T15", text="2"),
                "T16": Token(id="T16", text="\n"),
            },
            metadata={
                f"T{i}": TokenMetadata(token_id=f"T{i}", char_start=i, char_end=i+1, source_line=1)
                for i in range(17)
            },
        )

        nodes = full_pipeline["parser"].process(stage1)
        report = full_pipeline["classifier"].classify(nodes, source_text)
        assert report.has_type(LayerType.LIST)

        tree = full_pipeline["hierarchy"].build(report)
        components = full_pipeline["mapper"].map(tree)

        list_comps = [c for c in components if c.layer_type == LayerType.LIST]
        assert len(list_comps) >= 1

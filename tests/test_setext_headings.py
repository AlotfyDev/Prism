"""Tests for Setext heading detection and heading_style handling."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HeadingComponent,
    HeadingStyle,
    HierarchyNode,
    HierarchyTree,
    LayerInstance,
    MarkdownNode,
    NodeType,
)
from prism.stage2.layers.simple_layers import HeadingCRUD
from prism.stage2.mapper import ComponentMapper


class TestHeadingStyleEnum:
    """Test HeadingStyle enum."""

    def test_atx_style(self):
        assert HeadingStyle.ATX == "atx"

    def test_setext_style(self):
        assert HeadingStyle.SETEXT == "setext"

    def test_heading_style_values(self):
        assert set(HeadingStyle) == {HeadingStyle.ATX, HeadingStyle.SETEXT}


class TestHeadingComponentWithStyle:
    """Test HeadingComponent with heading_style field."""

    def test_default_style_is_atx(self):
        comp = HeadingComponent(
            component_id="heading:h1",
            layer_type=LayerType.HEADING,
            raw_content="# Title",
            level=1,
            text="Title",
            char_start=0,
            char_end=7,
        )
        assert comp.heading_style == HeadingStyle.ATX

    def test_setext_style_heading(self):
        comp = HeadingComponent(
            component_id="heading:h2",
            layer_type=LayerType.HEADING,
            raw_content="Title\n=====",
            level=1,
            text="Title",
            heading_style=HeadingStyle.SETEXT,
            char_start=0,
            char_end=11,
        )
        assert comp.heading_style == HeadingStyle.SETEXT
        assert comp.level == 1

    def test_setext_h2_heading(self):
        comp = HeadingComponent(
            component_id="heading:h3",
            layer_type=LayerType.HEADING,
            raw_content="Subtitle\n--------",
            level=2,
            text="Subtitle",
            heading_style=HeadingStyle.SETEXT,
            char_start=0,
            char_end=17,
        )
        assert comp.heading_style == HeadingStyle.SETEXT
        assert comp.level == 2

    def test_atx_heading_still_works(self):
        comp = HeadingComponent(
            component_id="heading:h4",
            layer_type=LayerType.HEADING,
            raw_content="### Section",
            level=3,
            text="Section",
            char_start=0,
            char_end=11,
        )
        assert comp.heading_style == HeadingStyle.ATX
        assert comp.level == 3


class TestHeadingCRUDWithSetext:
    """Test HeadingCRUD with setext heading support."""

    def test_create_atx_heading(self):
        crud = HeadingCRUD()
        comp = crud.create("h1", "# Title")
        assert comp.heading_style == HeadingStyle.ATX
        assert comp.level == 1
        assert comp.text == "Title"

    def test_create_setext_h1_heading(self):
        crud = HeadingCRUD()
        comp = crud.create("h2", "Title\n=====", heading_style=HeadingStyle.SETEXT)
        assert comp.heading_style == HeadingStyle.SETEXT
        assert comp.level == 1
        assert comp.text == "Title"

    def test_create_setext_h2_heading(self):
        crud = HeadingCRUD()
        comp = crud.create("h3", "Subtitle\n------", heading_style=HeadingStyle.SETEXT)
        assert comp.heading_style == HeadingStyle.SETEXT
        assert comp.level == 2

    def test_create_setext_with_explicit_level(self):
        crud = HeadingCRUD()
        comp = crud.create(
            "h4", "Custom\n=====", heading_style=HeadingStyle.SETEXT, level=1
        )
        assert comp.level == 1
        assert comp.heading_style == HeadingStyle.SETEXT

    def test_create_setext_with_string_style(self):
        crud = HeadingCRUD()
        comp = crud.create("h5", "Title\n=====", heading_style="setext")
        assert comp.heading_style == HeadingStyle.SETEXT

    def test_setext_text_extraction_from_first_line(self):
        crud = HeadingCRUD()
        comp = crud.create("h6", "My Heading\n========", heading_style=HeadingStyle.SETEXT)
        assert comp.text == "My Heading"

    def test_atx_text_extraction_still_works(self):
        crud = HeadingCRUD()
        comp = crud.create("h7", "## My Section")
        assert comp.text == "My Section"
        assert comp.heading_style == HeadingStyle.ATX

    def test_setext_default_level_for_equals(self):
        crud = HeadingCRUD()
        comp = crud.create("h8", "Title\n=====", heading_style=HeadingStyle.SETEXT)
        assert comp.level == 1

    def test_setext_default_level_for_dashes(self):
        crud = HeadingCRUD()
        comp = crud.create("h9", "Title\n-----", heading_style=HeadingStyle.SETEXT)
        assert comp.level == 2


class TestParserSetextHeadings:
    """Test parser captures heading_style for setext headings."""

    def test_atx_heading_has_atx_style(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "# ATX Heading"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        headings = [n for n in nodes if n.node_type == NodeType.HEADING]
        assert len(headings) == 1
        assert headings[0].attributes.get("heading_style") == "atx"

    def test_setext_h1_heading_has_setext_style(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "Setext H1\n========="
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        headings = [n for n in nodes if n.node_type == NodeType.HEADING]
        assert len(headings) == 1
        assert headings[0].attributes.get("heading_style") == "setext"
        assert headings[0].level == 1

    def test_setext_h2_heading_has_setext_style(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "Setext H2\n---------"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        headings = [n for n in nodes if n.node_type == NodeType.HEADING]
        assert len(headings) == 1
        assert headings[0].attributes.get("heading_style") == "setext"
        assert headings[0].level == 2

    def test_mixed_atx_and_setext_headings(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.parser import MarkdownItParser

        parser = MarkdownItParser()
        source = "# ATX H1\n\nSetext H1\n=========\n\n## ATX H2\n\nSetext H2\n---------"
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        headings = [n for n in nodes if n.node_type == NodeType.HEADING]
        assert len(headings) == 4

        styles = [h.attributes.get("heading_style") for h in headings]
        assert styles == ["atx", "setext", "atx", "setext"]

        levels = [h.level for h in headings]
        assert levels == [1, 1, 2, 2]


class TestMapperSetextHeadings:
    """Test ComponentMapper preserves heading_style."""

    def test_mapper_creates_atx_heading(self):
        mapper = ComponentMapper()
        inst = LayerInstance(
            layer_type=LayerType.HEADING,
            raw_content="# Title",
            char_start=0,
            char_end=7,
            line_start=0,
            line_end=1,
            attributes={"level": "1", "heading_style": "atx"},
            depth=0,
            sibling_index=0,
        )
        hierarchy_node = HierarchyNode(instance=inst, children=[])
        tree = HierarchyTree(root_nodes=[hierarchy_node])

        components = mapper.map(tree)
        assert len(components) == 1
        comp = components[0]
        assert isinstance(comp, HeadingComponent)
        assert comp.heading_style == HeadingStyle.ATX

    def test_mapper_creates_setext_heading(self):
        mapper = ComponentMapper()
        inst = LayerInstance(
            layer_type=LayerType.HEADING,
            raw_content="Title\n=====",
            char_start=0,
            char_end=11,
            line_start=0,
            line_end=2,
            attributes={"level": "1", "heading_style": "setext"},
            depth=0,
            sibling_index=0,
        )
        hierarchy_node = HierarchyNode(instance=inst, children=[])
        tree = HierarchyTree(root_nodes=[hierarchy_node])

        components = mapper.map(tree)
        assert len(components) == 1
        comp = components[0]
        assert isinstance(comp, HeadingComponent)
        assert comp.heading_style == HeadingStyle.SETEXT
        assert comp.text == "Title"


class TestSetextEndToEnd:
    """End-to-end tests for setext heading detection."""

    def test_full_pipeline_setext_h1(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.classifier import LayerClassifier
        from prism.stage2.hierarchy import HierarchyBuilder
        from prism.stage2.mapper import ComponentMapper
        from prism.stage2.parser import MarkdownItParser

        source = "Main Title\n=========="

        parser = MarkdownItParser()
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        classifier = LayerClassifier()
        report = classifier.classify(nodes, source)

        headings = report.instances_of(LayerType.HEADING)
        assert len(headings) == 1
        assert headings[0].attributes.get("heading_style") == "setext"

    def test_full_pipeline_mixed_headings(self):
        from prism.schemas.token import Stage1Output
        from prism.stage2.classifier import LayerClassifier
        from prism.stage2.parser import MarkdownItParser

        source = "# ATX H1\n\nSetext H1\n=========\n\nParagraph text.\n\nSetext H2\n---------"

        parser = MarkdownItParser()
        stage1 = Stage1Output(tokens={}, metadata={}, source_text=source)
        nodes = parser.process(stage1, None)

        classifier = LayerClassifier()
        report = classifier.classify(nodes, source)

        headings = report.instances_of(LayerType.HEADING)
        assert len(headings) == 3

        styles = [h.attributes.get("heading_style") for h in headings]
        assert styles == ["atx", "setext", "setext"]

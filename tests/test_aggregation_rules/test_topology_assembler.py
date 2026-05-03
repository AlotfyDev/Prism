"""Tests for TopologyAssembler — final Stage2Output assembly."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HeadingComponent,
    ParagraphComponent,
    Stage2Output,
)
from prism.stage2.aggregation.aggregation_models import (
    AssemblyInput,
    TokenRangeIndex,
)
from prism.stage2.aggregation.rules.topology_assembler import TopologyAssembler


@pytest.fixture
def assembler():
    return TopologyAssembler()


def make_heading(comp_id: str) -> HeadingComponent:
    return HeadingComponent(
        component_id=comp_id,
        layer_type=LayerType.HEADING,
        raw_content="# Title",
        char_start=0,
        char_end=7,
        level=1,
        text="Title",
        anchor_id=comp_id,
    )


def make_paragraph(comp_id: str) -> ParagraphComponent:
    return ParagraphComponent(
        component_id=comp_id,
        layer_type=LayerType.PARAGRAPH,
        raw_content="Some text",
        char_start=8,
        char_end=17,
    )


class TestValidateInput:
    def test_valid(self, assembler):
        comp = make_heading("heading:1")
        input_data = AssemblyInput(components={"heading:1": comp})
        assert assembler.validate_input(input_data) == (True, "")

    def test_invalid_type(self, assembler):
        valid, msg = assembler.validate_input("not AssemblyInput")
        assert valid is False

    def test_empty_components(self, assembler):
        input_data = AssemblyInput(components={})
        valid, msg = assembler.validate_input(input_data)
        assert valid is False


class TestValidateOutput:
    def test_valid(self, assembler):
        output = Stage2Output(
            discovered_layers={"heading:1": make_heading("heading:1")},
            layer_types={LayerType.HEADING},
        )
        assert assembler.validate_output(output) == (True, "")

    def test_empty_layers(self, assembler):
        output = Stage2Output()
        valid, msg = assembler.validate_output(output)
        assert valid is False


class TestAssemble:
    def test_basic_assembly(self, assembler):
        heading = make_heading("heading:1")
        para = make_paragraph("paragraph:1")

        input_data = AssemblyInput(
            components={
                "heading:1": heading,
                "paragraph:1": para,
            }
        )
        result = assembler.aggregate(input_data)

        assert "heading:1" in result.discovered_layers
        assert "paragraph:1" in result.discovered_layers
        assert len(result.layer_types) == 2

    def test_single_layer(self, assembler):
        h1 = make_heading("heading:1")
        h2 = make_heading("heading:2")

        input_data = AssemblyInput(
            components={"heading:1": h1, "heading:2": h2}
        )
        result = assembler.aggregate(input_data)

        assert result.is_single_layer is True
        assert result.layer_types == {LayerType.HEADING}

    def test_multi_layer(self, assembler):
        heading = make_heading("heading:1")
        para = make_paragraph("paragraph:1")

        input_data = AssemblyInput(
            components={"heading:1": heading, "paragraph:1": para}
        )
        result = assembler.aggregate(input_data)

        assert result.is_single_layer is False

    def test_token_mapping_from_index(self, assembler):
        heading = make_heading("heading:1")
        token_index = TokenRangeIndex(
            component_to_tokens={"heading:1": ["T0", "T1", "T2"]},
            total_tokens=3,
            assigned_tokens=3,
        )

        input_data = AssemblyInput(
            components={"heading:1": heading},
            token_range_index=token_index,
        )
        result = assembler.aggregate(input_data)

        assert "heading:1" in result.component_to_tokens
        assert result.component_to_tokens["heading:1"] == (0, 2)


class TestExtractNumericIds:
    def test_t_format(self, assembler):
        assert assembler._extract_numeric_ids(["T0", "T1", "T2"]) == [0, 1, 2]

    def test_token_format(self, assembler):
        assert assembler._extract_numeric_ids(["token_0", "token_1"]) == [0, 1]

    def test_mixed_format(self, assembler):
        result = assembler._extract_numeric_ids(["T0", "token_1", "invalid"])
        assert result == [0, 1]

    def test_empty(self, assembler):
        assert assembler._extract_numeric_ids([]) == []


class TestNameAndTier:
    def test_name(self, assembler):
        assert assembler.name() == "TopologyAssembler"

    def test_tier(self, assembler):
        assert assembler.tier == "rules"

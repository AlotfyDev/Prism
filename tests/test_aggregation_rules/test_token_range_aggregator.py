"""Tests for TokenRangeAggregator — bidirectional Token <-> Component mapping."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import PhysicalComponent
from prism.schemas.token import Stage1Output, Token, TokenMetadata
from prism.stage2.aggregation.aggregation_models import TokenRangeIndex
from prism.stage2.aggregation.rules.token_range_aggregator import TokenRangeAggregator


@pytest.fixture
def aggregator():
    return TokenRangeAggregator()


def make_token(tid: str, text: str, char_start: int, char_end: int) -> Token:
    return Token(
        id=tid,
        text=text,
    )


def make_metadata(tid: str, char_start: int, char_end: int) -> TokenMetadata:
    return TokenMetadata(
        token_id=tid,
        char_start=char_start,
        char_end=char_end,
        source_line=1,
    )


def make_component(
    comp_id: str, layer_type, raw_content: str,
    char_start: int, char_end: int,
) -> PhysicalComponent:
    return PhysicalComponent(
        component_id=comp_id,
        layer_type=layer_type,
        raw_content=raw_content,
        char_start=char_start,
        char_end=char_end,
    )


class TestValidateInput:
    def test_valid_input(self, aggregator):
        comp = make_component("heading:1", LayerType.HEADING, "# Title", 0, 7)
        stage1 = Stage1Output(tokens={}, metadata={})
        input_data = {"components": [comp], "stage1_output": stage1}
        valid, msg = aggregator.validate_input(input_data)
        assert valid is True

    def test_missing_components(self, aggregator):
        stage1 = Stage1Output(tokens={}, metadata={})
        input_data = {"stage1_output": stage1}
        valid, msg = aggregator.validate_input(input_data)
        assert valid is False

    def test_missing_stage1_output(self, aggregator):
        comp = make_component("heading:1", LayerType.HEADING, "# Title", 0, 7)
        input_data = {"components": [comp]}
        valid, msg = aggregator.validate_input(input_data)
        assert valid is False

    def test_components_not_list(self, aggregator):
        stage1 = Stage1Output(tokens={}, metadata={})
        input_data = {"components": "not a list", "stage1_output": stage1}
        valid, msg = aggregator.validate_input(input_data)
        assert valid is False


class TestValidateOutput:
    def test_valid_output(self, aggregator):
        output = TokenRangeIndex(
            component_to_tokens={"heading:1": ["T0", "T1"]},
            token_to_component={"T0": "heading:1"},
            unassigned_tokens=[],
            coverage_pct=100.0,
            total_tokens=2,
            assigned_tokens=2,
        )
        valid, msg = aggregator.validate_output(output)
        assert valid is True


class TestBuildIndex:
    def test_forward_mapping(self, aggregator):
        t0 = make_token("T0", "Hello", 0, 5)
        t1 = make_token("T1", " ", 5, 6)
        t2 = make_token("T2", "World", 6, 11)
        stage1 = Stage1Output(
            tokens={"T0": t0, "T1": t1, "T2": t2},
            metadata={
                "T0": make_metadata("T0", 0, 5),
                "T1": make_metadata("T1", 5, 6),
                "T2": make_metadata("T2", 6, 11),
            },
        )

        comp = make_component("heading:1", LayerType.HEADING, "# Hello World", 0, 11)
        result = aggregator.aggregate({"components": [comp], "stage1_output": stage1})

        assert "heading:1" in result.component_to_tokens
        assert "T0" in result.component_to_tokens["heading:1"]
        assert "T2" in result.component_to_tokens["heading:1"]

    def test_reverse_mapping(self, aggregator):
        t0 = make_token("T0", "Hello", 0, 5)
        t1 = make_token("T1", "World", 6, 11)
        stage1 = Stage1Output(
            tokens={"T0": t0, "T1": t1},
            metadata={
                "T0": make_metadata("T0", 0, 5),
                "T1": make_metadata("T1", 6, 11),
            },
        )

        comp = make_component("heading:1", LayerType.HEADING, "# Hello World", 0, 11)
        result = aggregator.aggregate({"components": [comp], "stage1_output": stage1})

        assert result.token_to_component["T0"] == "heading:1"
        assert result.token_to_component["T1"] == "heading:1"

    def test_multiple_components(self, aggregator):
        t0 = make_token("T0", "Hello", 0, 5)
        t1 = make_token("T1", "World", 6, 11)
        t2 = make_token("T2", "Foo", 12, 15)
        stage1 = Stage1Output(
            tokens={"T0": t0, "T1": t1, "T2": t2},
            metadata={
                "T0": make_metadata("T0", 0, 5),
                "T1": make_metadata("T1", 6, 11),
                "T2": make_metadata("T2", 12, 15),
            },
        )

        comp1 = make_component("heading:1", LayerType.HEADING, "Hello", 0, 5)
        comp2 = make_component("paragraph:1", LayerType.PARAGRAPH, "World Foo", 6, 15)

        result = aggregator.aggregate({"components": [comp1, comp2], "stage1_output": stage1})

        assert result.token_to_component["T0"] == "heading:1"
        assert result.token_to_component["T1"] == "paragraph:1"

    def test_unassigned_tokens(self, aggregator):
        t0 = make_token("T0", "Hello", 0, 5)
        t1 = make_token("T1", "Unassigned", 100, 110)
        stage1 = Stage1Output(
            tokens={"T0": t0, "T1": t1},
            metadata={
                "T0": make_metadata("T0", 0, 5),
                "T1": make_metadata("T1", 100, 110),
            },
        )

        comp = make_component("heading:1", LayerType.HEADING, "Hello", 0, 5)
        result = aggregator.aggregate({"components": [comp], "stage1_output": stage1})

        assert "T1" in result.unassigned_tokens

    def test_coverage_calculation(self, aggregator):
        t0 = make_token("T0", "Hello", 0, 5)
        t1 = make_token("T1", "World", 6, 11)
        t2 = make_token("T2", "Gap", 100, 103)
        stage1 = Stage1Output(
            tokens={"T0": t0, "T1": t1, "T2": t2},
            metadata={
                "T0": make_metadata("T0", 0, 5),
                "T1": make_metadata("T1", 6, 11),
                "T2": make_metadata("T2", 100, 103),
            },
        )

        comp = make_component("heading:1", LayerType.HEADING, "Hello World", 0, 11)
        result = aggregator.aggregate({"components": [comp], "stage1_output": stage1})

        assert result.total_tokens == 3
        assert result.assigned_tokens == 2
        assert result.coverage_pct == pytest.approx(66.67, abs=0.1)

    def test_empty_tokens(self, aggregator):
        stage1 = Stage1Output(tokens={}, metadata={})
        comp = make_component("heading:1", LayerType.HEADING, "Hello", 0, 5)
        result = aggregator.aggregate({"components": [comp], "stage1_output": stage1})

        assert result.total_tokens == 0
        assert result.coverage_pct == 100.0

    def test_empty_components(self, aggregator):
        t0 = make_token("T0", "Hello", 0, 5)
        stage1 = Stage1Output(
            tokens={"T0": t0},
            metadata={"T0": make_metadata("T0", 0, 5)},
        )
        result = aggregator.aggregate({"components": [], "stage1_output": stage1})

        assert result.total_tokens == 1
        assert result.assigned_tokens == 0
        assert "T0" in result.unassigned_tokens
        assert result.coverage_pct == 0.0


class TestNameAndTier:
    def test_name(self, aggregator):
        assert aggregator.name() == "TokenRangeAggregator"

    def test_tier(self, aggregator):
        assert aggregator.tier == "rules"

    def test_version(self, aggregator):
        assert aggregator.version == "1.0.0"

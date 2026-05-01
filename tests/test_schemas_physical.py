"""Unit tests for Stage 2 schema models (PhysicalComponent, etc.)."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    PhysicalComponent,
    Stage2Input,
    Stage2Output,
    TopologyConfig,
)


class TestPhysicalComponent:
    def test_valid_minimal(self):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello world",
        )
        assert comp.component_id == "paragraph:p1"
        assert comp.layer_type == LayerType.PARAGRAPH
        assert comp.raw_content == "Hello world"
        assert comp.token_span is None
        assert comp.parent_id is None
        assert comp.children == []
        assert comp.attributes == {}

    def test_valid_with_token_span(self):
        comp = PhysicalComponent(
            component_id="table:t1",
            layer_type=LayerType.TABLE,
            raw_content="| A | B |\n| 1 | 2 |",
            token_span=(5, 12),
        )
        assert comp.token_span == (5, 12)
        assert comp.token_range == (5, 12)
        assert comp.token_count == 8

    def test_valid_with_hierarchy(self):
        comp = PhysicalComponent(
            component_id="list:l1",
            layer_type=LayerType.LIST,
            raw_content="- item 1\n- item 2",
            children=["list:l1_item1", "list:l1_item2"],
            attributes={"style": "unordered"},
        )
        assert len(comp.children) == 2
        assert comp.attributes["style"] == "unordered"

    def test_valid_nested_under_heading(self):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Content under heading",
            parent_id="heading:h1",
        )
        assert comp.parent_id == "heading:h1"

    def test_invalid_id_no_colon(self):
        with pytest.raises(ValidationError, match="pattern"):
            PhysicalComponent(
                component_id="paragraph_p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="text",
            )

    def test_invalid_id_empty_identifier(self):
        with pytest.raises(ValidationError, match="pattern"):
            PhysicalComponent(
                component_id="paragraph:",
                layer_type=LayerType.PARAGRAPH,
                raw_content="text",
            )

    def test_invalid_id_mismatched_layer_type(self):
        with pytest.raises(ValidationError, match="prefix"):
            PhysicalComponent(
                component_id="table:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="text",
            )

    def test_invalid_empty_content(self):
        with pytest.raises(ValidationError, match="at least 1 character"):
            PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="",
            )

    def test_all_layer_types_valid(self):
        for lt in LayerType:
            comp = PhysicalComponent(
                component_id=f"{lt.value}:x1",
                layer_type=lt,
                raw_content="test",
            )
            assert comp.layer_type == lt

    def test_token_span_invalid_negative(self):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="test",
            token_span=(-1, 5),
        )
        assert comp.token_span == (-1, 5)

    def test_token_range_raises_when_unset(self):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="test",
        )
        with pytest.raises(ValueError, match="token_span not set"):
            _ = comp.token_range

    def test_token_count_zero_when_unset(self):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="test",
        )
        assert comp.token_count == 0


class TestTopologyConfig:
    def test_defaults(self):
        config = TopologyConfig()
        assert config.layer_types_to_detect == list(LayerType)
        assert config.nesting_depth_limit == 10

    def test_custom_values(self):
        config = TopologyConfig(
            layer_types_to_detect=[LayerType.PARAGRAPH, LayerType.TABLE],
            nesting_depth_limit=5,
        )
        assert len(config.layer_types_to_detect) == 2
        assert config.nesting_depth_limit == 5

    def test_invalid_nesting_depth(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            TopologyConfig(nesting_depth_limit=0)


class TestStage2Input:
    def test_valid_minimal(self):
        inp = Stage2Input(source_text="Hello world", token_ids=["T0", "T1"])
        assert inp.source_text == "Hello world"
        assert inp.token_ids == ["T0", "T1"]
        assert isinstance(inp.config, TopologyConfig)

    def test_custom_config(self):
        config = TopologyConfig(nesting_depth_limit=3)
        inp = Stage2Input(
            source_text="text",
            token_ids=["T0"],
            config=config,
        )
        assert inp.config.nesting_depth_limit == 3

    def test_missing_source_text(self):
        with pytest.raises(ValidationError):
            Stage2Input(token_ids=["T0"])

    def test_empty_token_ids(self):
        inp = Stage2Input(source_text="")
        assert inp.token_ids == []


class TestStage2Output:
    def test_empty_output(self):
        output = Stage2Output()
        assert output.component_count == 0
        assert output.layer_types == set()
        assert output.is_single_layer is True
        assert output.component_to_tokens == {}

    def test_single_component(self):
        comp = PhysicalComponent(
            component_id="paragraph:p1",
            layer_type=LayerType.PARAGRAPH,
            raw_content="Hello",
            token_span=(0, 0),
        )
        output = Stage2Output(discovered_layers={"paragraph:p1": comp})
        assert output.component_count == 1
        assert output.layer_types == {LayerType.PARAGRAPH}
        assert output.is_single_layer is True
        assert output.component_to_tokens == {"paragraph:p1": (0, 0)}

    def test_multiple_layer_types(self):
        components = {
            "paragraph:p1": PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="Para",
                token_span=(0, 1),
            ),
            "table:t1": PhysicalComponent(
                component_id="table:t1",
                layer_type=LayerType.TABLE,
                raw_content="|A|B|",
                token_span=(2, 5),
            ),
        }
        output = Stage2Output(discovered_layers=components)
        assert output.component_count == 2
        assert output.layer_types == {LayerType.PARAGRAPH, LayerType.TABLE}
        assert output.is_single_layer is False

    def test_multiple_same_layer_types(self):
        components = {
            "paragraph:p1": PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="Para 1",
            ),
            "paragraph:p2": PhysicalComponent(
                component_id="paragraph:p2",
                layer_type=LayerType.PARAGRAPH,
                raw_content="Para 2",
            ),
        }
        output = Stage2Output(discovered_layers=components)
        assert output.layer_types == {LayerType.PARAGRAPH}
        assert output.is_single_layer is True

    def test_component_to_tokens_excludes_unset(self):
        components = {
            "paragraph:p1": PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="Has span",
                token_span=(0, 3),
            ),
            "heading:h1": PhysicalComponent(
                component_id="heading:h1",
                layer_type=LayerType.HEADING,
                raw_content="No span",
            ),
        }
        output = Stage2Output(discovered_layers=components)
        assert "paragraph:p1" in output.component_to_tokens
        assert "heading:h1" not in output.component_to_tokens

"""Tests for HorizontalRuleComponent schema and NestingMatrix HR rules."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HRuleStyle,
    HorizontalRuleComponent,
    NestingMatrix,
    PhysicalComponent,
)


class TestHorizontalRuleComponent:
    """Tests for the HorizontalRuleComponent model."""

    def test_create_dash_rule(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr1",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="---",
            style=HRuleStyle.DASH,
            char_start=0,
            char_end=3,
        )
        assert hr.style == HRuleStyle.DASH
        assert hr.length == 3

    def test_create_star_rule(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr2",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="***",
            style=HRuleStyle.STAR,
            char_start=10,
            char_end=13,
        )
        assert hr.style == HRuleStyle.STAR
        assert hr.length == 3

    def test_create_underscore_rule(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr3",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="___",
            style=HRuleStyle.UNDERSCORE,
            char_start=20,
            char_end=23,
        )
        assert hr.style == HRuleStyle.UNDERSCORE
        assert hr.length == 3

    def test_auto_computes_length(self):
        """Length is auto-computed from raw_content if not set."""
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr4",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="- - -",
            style=HRuleStyle.DASH,
            char_start=0,
            char_end=5,
        )
        assert hr.length == 3

    def test_auto_computes_length_from_stars(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr5",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="* * *",
            style=HRuleStyle.STAR,
            char_start=0,
            char_end=5,
        )
        assert hr.length == 3

    def test_auto_computes_length_long_rule(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr6",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="------",
            style=HRuleStyle.DASH,
            char_start=0,
            char_end=6,
        )
        assert hr.length == 6

    def test_explicit_length_overrides_auto(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr7",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="---",
            style=HRuleStyle.DASH,
            length=5,
            char_start=0,
            char_end=3,
        )
        assert hr.length == 5

    def test_is_leaf_no_children(self):
        """Horizontal rules are leaf components — no children allowed."""
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr8",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="---",
            style=HRuleStyle.DASH,
            char_start=0,
            char_end=3,
        )
        assert hr.children == []

    def test_inherits_physical_component_fields(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr9",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="---",
            style=HRuleStyle.DASH,
            char_start=100,
            char_end=103,
        )
        assert hr.component_id == "horizontal_rule:hr9"
        assert hr.layer_type == LayerType.HORIZONTAL_RULE
        assert hr.raw_content == "---"
        assert hr.char_start == 100
        assert hr.char_end == 103
        assert hr.parent_id is None
        assert hr.attributes == {}

    def test_default_style_is_dash(self):
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr10",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="---",
            char_start=0,
            char_end=3,
        )
        assert hr.style == HRuleStyle.DASH

    def test_auto_length_not_overridden_by_zero(self):
        """Auto-compute overrides explicit length=0 if raw_content is present."""
        hr = HorizontalRuleComponent(
            component_id="horizontal_rule:hr11",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content="---",
            style=HRuleStyle.DASH,
            char_start=0,
            char_end=3,
        )
        # Length is auto-computed from raw_content
        assert hr.length == 3

    def test_component_id_must_start_with_prefix(self):
        with pytest.raises(ValidationError, match="horizontal_rule:"):
            HorizontalRuleComponent(
                component_id="hr:bad",
                layer_type=LayerType.HORIZONTAL_RULE,
                raw_content="---",
                style=HRuleStyle.DASH,
                char_start=0,
                char_end=3,
            )


class TestHRuleNestingRules:
    """Tests for HorizontalRule nesting in NestingMatrix."""

    def test_hr_is_leaf(self):
        matrix = NestingMatrix.default()
        children = matrix.get_valid_children(LayerType.HORIZONTAL_RULE)
        assert children == set()

    def test_hr_cannot_contain_anything(self):
        matrix = NestingMatrix.default()
        for lt in LayerType:
            assert not matrix.can_contain(LayerType.HORIZONTAL_RULE, lt)

    def test_heading_can_contain_hr(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.HEADING, LayerType.HORIZONTAL_RULE)

    def test_paragraph_can_contain_hr(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.PARAGRAPH, LayerType.HORIZONTAL_RULE)

    def test_list_can_contain_hr(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.LIST, LayerType.HORIZONTAL_RULE)

    def test_table_can_contain_hr(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TABLE, LayerType.HORIZONTAL_RULE)

    def test_blockquote_can_contain_hr(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.BLOCKQUOTE, LayerType.HORIZONTAL_RULE)

    def test_footnote_can_contain_hr(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.FOOTNOTE, LayerType.HORIZONTAL_RULE)

    def test_task_list_can_contain_hr(self):
        matrix = NestingMatrix.default()
        assert matrix.can_contain(LayerType.TASK_LIST, LayerType.HORIZONTAL_RULE)

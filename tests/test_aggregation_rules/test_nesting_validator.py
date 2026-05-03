"""Tests for NestingValidator — validates component hierarchy against NestingMatrix."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HeadingComponent,
    ParagraphComponent,
    PhysicalComponent,
)
from prism.stage2.aggregation.rules.nesting_validator import NestingValidator


@pytest.fixture
def validator():
    return NestingValidator()


def make_heading(comp_id: str, level: int, parent_id: str = None) -> HeadingComponent:
    return HeadingComponent(
        component_id=f"heading:{comp_id}",
        layer_type=LayerType.HEADING,
        raw_content=f"{'#' * level} Title",
        char_start=0,
        char_end=10,
        level=level,
        text="Title",
        anchor_id=f"heading:{comp_id}",
        parent_id=parent_id,
    )


def make_paragraph(comp_id: str, parent_id: str = None) -> ParagraphComponent:
    return ParagraphComponent(
        component_id=comp_id,
        layer_type=LayerType.PARAGRAPH,
        raw_content="Some text",
        char_start=0,
        char_end=9,
        parent_id=parent_id,
    )


class TestValidateInput:
    def test_valid(self, validator):
        comp = make_heading("1", 1)
        assert validator.validate_input({"heading:1": comp}) == (True, "")

    def test_invalid_type(self, validator):
        valid, msg = validator.validate_input("not a dict")
        assert valid is False

    def test_key_mismatch(self, validator):
        comp = make_heading("1", 1)
        valid, msg = validator.validate_input({"heading:wrong": comp})
        assert valid is False


class TestValidateNesting:
    def test_valid_hierarchy(self, validator):
        """Test valid parent-child relationship."""
        heading = make_heading("1", 1)
        para = make_paragraph("paragraph:1", parent_id="heading:1")

        components = {
            "heading:1": heading,
            "paragraph:1": para,
        }
        result = validator.aggregate(components)

        assert result.is_valid is True
        assert result.total_components == 2

    def test_valid_root_components(self, validator):
        """Test root components (no parent)."""
        heading = make_heading("1", 1)
        heading2 = make_heading("2", 1)

        components = {
            "heading:1": heading,
            "heading:2": heading2,
        }
        result = validator.aggregate(components)

        assert result.is_valid is True
        assert result.max_depth == 0

    def test_depth_calculation(self, validator):
        """Test depth calculation via parent chain."""
        h1 = make_heading("1", 1)
        h2 = make_heading("2", 2, parent_id="heading:1")
        h3 = make_heading("3", 3, parent_id="heading:2")

        components = {
            "heading:1": h1,
            "heading:2": h2,
            "heading:3": h3,
        }
        result = validator.aggregate(components)

        assert result.max_depth == 2

    def test_depth_distribution(self, validator):
        """Test depth distribution calculation."""
        h1 = make_heading("1", 1)
        h2 = make_heading("2", 1)
        p1 = make_paragraph("paragraph:1", parent_id="heading:1")

        components = {
            "heading:1": h1,
            "heading:2": h2,
            "paragraph:1": p1,
        }
        result = validator.aggregate(components)

        assert result.depth_distribution.get(0, 0) == 2
        assert result.depth_distribution.get(1, 0) == 1

    def test_empty_components(self, validator):
        result = validator.aggregate({})
        assert result.is_valid is True
        assert result.total_components == 0
        assert result.max_depth == 0


class TestContainerStats:
    def test_container_with_children(self, validator):
        heading = make_heading("1", 1)
        para = make_paragraph("paragraph:1", parent_id="heading:1")

        components = {
            "heading:1": heading,
            "paragraph:1": para,
        }
        result = validator.aggregate(components)

        assert "heading:1" in result.container_stats
        assert result.container_stats["heading:1"]["children_count"] == 1


class TestValidateOutput:
    def test_valid(self, validator):
        from prism.stage2.aggregation.aggregation_models import NestingValidationReport
        report = NestingValidationReport(
            is_valid=True,
            violations=[],
            max_depth=0,
            total_components=2,
        )
        assert validator.validate_output(report) == (True, "")

    def test_invalid_missing_violations(self, validator):
        from prism.stage2.aggregation.aggregation_models import NestingValidationReport
        report = NestingValidationReport(
            is_valid=False,
            violations=[],
            max_depth=0,
            total_components=2,
        )
        valid, msg = validator.validate_output(report)
        assert valid is False


class TestNameAndTier:
    def test_name(self, validator):
        assert validator.name() == "NestingValidator"

    def test_tier(self, validator):
        assert validator.tier == "rules"

"""Tests for IndentationAnalyzer — heading indentation pattern analysis."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import HeadingComponent
from prism.stage2.aggregation.rules.indentation_analyzer import IndentationAnalyzer


@pytest.fixture
def aggregator():
    return IndentationAnalyzer()


def make_heading(comp_id: str, level: int, text: str, raw: str) -> HeadingComponent:
    return HeadingComponent(
        component_id=f"heading:{comp_id}",
        layer_type=LayerType.HEADING,
        raw_content=raw,
        char_start=0,
        char_end=len(raw),
        level=level,
        text=text,
        anchor_id=f"heading:{comp_id}",
    )


class TestValidateInput:
    def test_valid(self, aggregator):
        assert aggregator.validate_input([]) == (True, "")

    def test_invalid_type(self, aggregator):
        valid, msg = aggregator.validate_input("not a list")
        assert valid is False

    def test_invalid_items(self, aggregator):
        valid, msg = aggregator.validate_input(["not a heading"])
        assert valid is False


class TestAnalyzeIndentation:
    def test_empty(self, aggregator):
        result = aggregator.aggregate([])
        assert result.total_headings == 0
        assert result.is_consistent is True
        assert result.pattern_type == "standard"

    def test_standard_pattern(self, aggregator):
        headings = [
            make_heading("h:1", 1, "Title", "# Title"),
            make_heading("h:2", 2, "Section", "## Section"),
            make_heading("h:3", 2, "Section 2", "## Section 2"),
        ]
        result = aggregator.aggregate(headings)
        assert result.pattern_type == "standard"
        assert result.is_consistent is True
        assert result.total_headings == 3

    def test_all_zero_indent(self, aggregator):
        headings = [
            make_heading("h:1", 1, "A", "# A"),
            make_heading("h:2", 2, "B", "## B"),
        ]
        result = aggregator.aggregate(headings)
        assert result.pattern_type == "standard"
        assert result.levels == [0]

    def test_indented_pattern(self, aggregator):
        headings = [
            make_heading("h:1", 1, "Title", "# Title"),
            make_heading("h:2", 2, "Section", "  ## Section"),  # 2 spaces indent
            make_heading("h:3", 3, "Sub", "    ### Sub"),  # 4 spaces indent
        ]
        result = aggregator.aggregate(headings)
        # 0, 2, 4 — consistent increment of 2
        assert result.pattern_type == "indented"

    def test_mixed_pattern(self, aggregator):
        headings = [
            make_heading("h:1", 1, "A", "# A"),
            make_heading("h:2", 2, "B", "  ## B"),  # 2 spaces
            make_heading("h:3", 2, "C", "     ## C"),  # 5 spaces (not consistent increment)
        ]
        result = aggregator.aggregate(headings)
        # Unique levels: 0, 2, 5 — diffs: [2, 3] — not consistent → mixed
        assert result.pattern_type == "mixed"
        assert result.is_consistent is False

    def test_anomaly_detection(self, aggregator):
        headings = [
            make_heading("h:1", 1, "A", "# A"),
            make_heading("h:2", 2, "B", "  ## B"),  # Anomaly: indented in standard
            make_heading("h:3", 2, "C", "## C"),
        ]
        result = aggregator.aggregate(headings)
        # h:2 has indentation in standard pattern
        assert len(result.anomalies) >= 1


class TestExtractIndentation:
    def test_no_indent(self, aggregator):
        assert aggregator._extract_indentation("# Title") == 0

    def test_spaces(self, aggregator):
        assert aggregator._extract_indentation("  ## Title") == 2

    def test_tabs(self, aggregator):
        assert aggregator._extract_indentation("\t### Title") == 4


class TestNameAndTier:
    def test_name(self, aggregator):
        assert aggregator.name() == "IndentationAnalyzer"

    def test_tier(self, aggregator):
        assert aggregator.tier == "rules"

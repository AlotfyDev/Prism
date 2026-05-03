"""Tests for HeadingSequenceAnalyzer — spaCy-enhanced heading validation."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import HeadingComponent
from prism.stage2.aggregation.nlp.heading_sequence import HeadingSequenceAnalyzer


@pytest.fixture
def analyzer():
    return HeadingSequenceAnalyzer(spacy_model="en_core_web_sm")


def make_heading(comp_id: str, level: int, text: str, raw: str, char_start: int = 0) -> HeadingComponent:
    full_id = f"heading:{comp_id}"
    return HeadingComponent(
        component_id=full_id,
        layer_type=LayerType.HEADING,
        raw_content=raw,
        char_start=char_start,
        char_end=char_start + len(raw),
        level=level,
        text=text,
        anchor_id=full_id,
    )


class TestValidateInput:
    def test_valid(self, analyzer):
        assert analyzer.validate_input([]) == (True, "")

    def test_invalid_type(self, analyzer):
        valid, msg = analyzer.validate_input("not a list")
        assert valid is False

    def test_invalid_items(self, analyzer):
        valid, msg = analyzer.validate_input(["not a heading"])
        assert valid is False


class TestValidateOutput:
    def test_valid(self, analyzer):
        from prism.stage2.aggregation.aggregation_models import HeadingSequenceReport
        report = HeadingSequenceReport(
            headings=[],
            total_headings=0,
        )
        assert analyzer.validate_output(report) == (True, "")

    def test_mismatch_count(self, analyzer):
        from prism.stage2.aggregation.aggregation_models import HeadingSequenceReport
        report = HeadingSequenceReport(
            headings=[make_heading("h:1", 1, "A", "# A")],
            total_headings=5,  # Mismatch
        )
        valid, msg = analyzer.validate_output(report)
        assert valid is False


class TestAnalyze:
    def test_empty(self, analyzer):
        result = analyzer.aggregate([])
        assert result.total_headings == 0
        assert result.is_valid is True
        assert result.sequence == []

    def test_valid_sequence(self, analyzer):
        headings = [
            make_heading("h:1", 1, "Title", "# Title", 0),
            make_heading("h:2", 2, "Section", "## Section", 10),
            make_heading("h:3", 2, "Section 2", "## Section 2", 25),
            make_heading("h:4", 3, "Sub", "### Sub", 40),
        ]
        result = analyzer.aggregate(headings)
        assert result.is_valid is True
        assert result.sequence == [1, 2, 2, 3]
        assert result.max_depth == 3
        assert result.total_headings == 4

    def test_skip_violation(self, analyzer):
        """H1 -> H3 should be flagged as skip."""
        headings = [
            make_heading("h:1", 1, "Title", "# Title", 0),
            make_heading("h:2", 3, "Sub", "### Sub", 10),  # Skip: H1 -> H3
        ]
        result = analyzer.aggregate(headings)
        assert result.is_valid is False
        assert len(result.violations) >= 1
        assert result.violations[0].severity == "skip"

    def test_jump_back_violation(self, analyzer):
        """H4 -> H2 should be flagged as jump_back."""
        headings = [
            make_heading("h:1", 1, "Title", "# Title", 0),
            make_heading("h:2", 4, "Deep", "#### Deep", 10),
            make_heading("h:3", 2, "Jump", "## Jump", 25),  # Jump back: H4 -> H2
        ]
        result = analyzer.aggregate(headings)
        assert result.is_valid is False
        jump_backs = [v for v in result.violations if v.severity == "jump_back"]
        assert len(jump_backs) >= 1


class TestGroups:
    def test_root_groups(self, analyzer):
        headings = [
            make_heading("h:1", 1, "A", "# A", 0),
            make_heading("h:2", 1, "B", "# B", 10),
        ]
        result = analyzer.aggregate(headings)
        assert len(result.groups) == 2

    def test_nested_groups(self, analyzer):
        headings = [
            make_heading("h:1", 1, "A", "# A", 0),
            make_heading("h:2", 2, "A.1", "## A.1", 10),
            make_heading("h:3", 2, "A.2", "## A.2", 20),
        ]
        result = analyzer.aggregate(headings)
        assert len(result.groups) == 1
        assert len(result.groups[0].siblings) == 2


class TestIndentationPattern:
    def test_standard(self, analyzer):
        headings = [
            make_heading("h:1", 1, "A", "# A", 0),
            make_heading("h:2", 2, "B", "## B", 10),
        ]
        result = analyzer.aggregate(headings)
        assert result.indentation_pattern == "standard"

    def test_indented(self, analyzer):
        headings = [
            make_heading("h:1", 1, "A", "# A", 0),
            make_heading("h:2", 2, "B", "  ## B", 10),
            make_heading("h:3", 3, "C", "    ### C", 25),
        ]
        result = analyzer.aggregate(headings)
        # Indentation: 0, 2, 4 — consistent increment
        assert result.indentation_pattern == "indented"

    def test_mixed(self, analyzer):
        headings = [
            make_heading("h:1", 1, "A", "# A", 0),
            make_heading("h:2", 2, "B", "  ## B", 10),  # 2 spaces
            make_heading("h:3", 2, "C", "   ## C", 25),  # 3 spaces (not consistent)
        ]
        result = analyzer.aggregate(headings)
        assert result.indentation_pattern == "mixed"


class TestSpacyEnhancement:
    def test_spacy_not_installed_fallback(self, analyzer):
        """Test graceful fallback when spaCy model is not installed."""
        # Use a non-existent model to test fallback
        analyzer_no_spacy = HeadingSequenceAnalyzer(spacy_model="nonexistent_model")
        headings = [
            make_heading("h:1", 1, "Title", "# Title", 0),
        ]
        result = analyzer_no_spacy.aggregate(headings)
        # Should still work, just without spacy_enhanced
        assert result.total_headings == 1
        assert result.spacy_enhanced is False


class TestNameAndTier:
    def test_name(self, analyzer):
        assert analyzer.name() == "HeadingSequenceAnalyzer"

    def test_tier(self, analyzer):
        assert analyzer.tier == "nlp"

    def test_version(self, analyzer):
        assert analyzer.version == "1.0.0"

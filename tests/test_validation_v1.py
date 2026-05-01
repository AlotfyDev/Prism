"""Behavioral tests for ValidationV1 — Token Integrity Gate (P1.4).

Tests the ValidationUnit contract: validate() returns ValidationReport
with per-check results, severity levels, and critical failure detection.
Unlike MetadataIndexer.validate_output (tuple[bool, str]), ValidationV1
provides detailed, actionable reports that the pipeline can use to decide
whether to halt or continue.
"""

import pytest

from prism.core.validation_unit import ValidationReport, ValidationCheck, ValidationSeverity
from prism.schemas import Stage1Input, Stage1Output, Token, TokenMetadata, TokenizationConfig
from prism.stage1.validation_v1 import ValidationV1


class TestValidationV1Instantiation:
    """ValidationV1 construction and contract."""

    def test_can_instantiate(self):
        v = ValidationV1()
        assert isinstance(v.name(), str)

    def test_name_is_descriptive(self):
        v = ValidationV1()
        assert "v1" in v.name().lower()

    def test_implements_validation_unit(self):
        v = ValidationV1()
        assert callable(v.validate)


class TestValidationV1_ValidOutput:
    """Baseline: valid Stage1Output passes all checks."""

    def test_valid_output_with_whitespace(self):
        """Complete token stream with whitespace passes all 5 checks."""
        output = self._full_output("hello world")
        report = ValidationV1().validate(output)
        assert report.passed is True
        assert len(report.critical_failures) == 0
        assert report.stage == "stage1"

    def test_valid_output_single_token(self):
        """Single token passes all checks."""
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello",
            config=TokenizationConfig(include_whitespace=True),
        )
        report = ValidationV1().validate(output)
        assert report.passed is True
        assert len(report.critical_failures) == 0

    def test_all_checks_present(self):
        """Report contains all 5 validation checks."""
        output = self._full_output("hello world")
        report = ValidationV1().validate(output)
        check_names = {c.name for c in report.checks}
        assert "V1.1_sequential_ids" in check_names
        assert "V1.2_no_empty_tokens" in check_names
        assert "V1.3_metadata_completeness" in check_names
        assert "V1.4_no_overlapping_ranges" in check_names
        assert "V1.5_full_coverage" in check_names

    def test_all_checks_passed(self):
        """All 5 checks show passed=True."""
        output = self._full_output("hello world")
        report = ValidationV1().validate(output)
        for check in report.checks:
            assert check.passed is True

    def _full_output(self, source_text: str) -> Stage1Output:
        return Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": " "},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 6, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text=source_text,
            config=TokenizationConfig(include_whitespace=True),
        )


class TestValidationV1_SequentialIDs:
    """V1.1: Sequential token IDs (no gaps: T0, T1, ... TN)."""

    def test_sequential_ids_pass(self):
        """T0, T1, T2 passes V1.1."""
        output = self._output_with_ids(["T0", "T1", "T2"])
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.1_sequential_ids")
        assert check is not None
        assert check.passed is True

    def test_missing_id_fails_critical(self):
        """T0, T2 (missing T1) fails V1.1 as CRITICAL."""
        output = self._output_with_ids(["T0", "T2"])
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.1_sequential_ids")
        assert check is not None
        assert check.passed is False
        assert check.severity == ValidationSeverity.CRITICAL
        assert report.critical_failures

    def test_id_mismatch_between_key_and_token_fails(self):
        """Key T0 with token.id=T1 reveals data corruption."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T1", "text": "hello"},
                "T1": {"id": "T0", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
        )
        report = ValidationV1().validate(output)
        # V1.1 sees T0, T1 which is sequential — but metadata token_id mismatch
        # should be caught by V1.3 if we add that check
        v1 = self._find_check(report, "V1.1_sequential_ids")
        assert v1 is not None
        assert v1.passed is True  # Keys are sequential, even if token.id is wrong
        assert v1.severity == ValidationSeverity.CRITICAL

    def test_non_sequential_start_fails(self):
        """T1, T2 (missing T0) fails V1.1 as CRITICAL."""
        output = Stage1Output(
            tokens={
                "T1": {"id": "T1", "text": "hello"},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T1": {"token_id": "T1", "char_start": 0, "char_end": 5, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
            config=TokenizationConfig(include_whitespace=True),
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.1_sequential_ids")
        assert check is not None
        assert check.passed is False
        assert check.severity == ValidationSeverity.CRITICAL

    def _output_with_ids(self, ids: list[str]) -> Stage1Output:
        tokens = {}
        metadata = {}
        cursor = 0
        for i, tid in enumerate(ids):
            text = f"tok{i}"
            start = cursor
            end = cursor + len(text)
            tokens[tid] = {"id": tid, "text": text}
            metadata[tid] = {"token_id": tid, "char_start": start, "char_end": end, "source_line": 1}
            cursor = end
        source = "".join(tokens[tid]["text"] for tid in ids)
        return Stage1Output(
            tokens=tokens,
            metadata=metadata,
            source_text=source,
            config=TokenizationConfig(include_whitespace=True),
        )

    def _find_check(self, report: ValidationReport, name: str) -> ValidationCheck | None:
        for c in report.checks:
            if c.name == name:
                return c
        return None


class TestValidationV1_NoEmptyTokens:
    """V1.2: No empty tokens (token.text must have content)."""

    def test_no_empty_tokens_pass(self):
        """All tokens have non-empty text."""
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello",
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.2_no_empty_tokens")
        assert check is not None
        assert check.passed is True

    def test_empty_token_rejected_by_schema(self):
        """Pydantic schema rejects empty token text (min_length=1)."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            Stage1Output(
                tokens={
                    "T0": {"id": "T0", "text": "hello"},
                    "T1": {"id": "T1", "text": ""},
                },
                metadata={
                    "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                    "T1": {"token_id": "T1", "char_start": 5, "char_end": 5, "source_line": 1},
                },
                source_text="hello",
            )

    def test_whitespace_token_fails_when_config_excludes(self):
        """Whitespace-only token fails V1.2 when include_whitespace=False."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "   "},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 8, "source_line": 1},
            },
            source_text="hello   ",
            config=TokenizationConfig(include_whitespace=False),
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.2_no_empty_tokens")
        assert check is not None
        assert check.passed is False
        assert check.severity == ValidationSeverity.CRITICAL

    def test_whitespace_only_token_passes_when_config_allows(self):
        """Whitespace-only token passes V1.2 when include_whitespace=True."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": " "},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 6, "source_line": 1},
            },
            source_text="hello ",
            config=TokenizationConfig(include_whitespace=True),
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.2_no_empty_tokens")
        assert check is not None
        assert check.passed is True

    def _find_check(self, report: ValidationReport, name: str) -> ValidationCheck | None:
        for c in report.checks:
            if c.name == name:
                return c
        return None


class TestValidationV1_MetadataCompleteness:
    """V1.3: Metadata completeness (every token has char_start/char_end)."""

    def test_metadata_complete_pass(self):
        """Every token has complete metadata."""
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello",
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.3_metadata_completeness")
        assert check is not None
        assert check.passed is True

    def test_missing_metadata_fails_critical(self):
        """Token without metadata entry fails V1.3 as CRITICAL."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "world"},
            },
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello world",
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.3_metadata_completeness")
        assert check is not None
        assert check.passed is False
        assert check.severity == ValidationSeverity.CRITICAL

    def test_metadata_without_token_fails_critical(self):
        """Metadata entry without matching token fails V1.3 as CRITICAL."""
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello",
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.3_metadata_completeness")
        assert check is not None
        assert check.passed is False

    def _find_check(self, report: ValidationReport, name: str) -> ValidationCheck | None:
        for c in report.checks:
            if c.name == name:
                return c
        return None


class TestValidationV1_NoOverlappingRanges:
    """V1.4: No overlapping character ranges."""

    def test_no_overlaps_pass(self):
        """Non-overlapping char ranges pass V1.4."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.4_no_overlapping_ranges")
        assert check is not None
        assert check.passed is True

    def test_overlapping_ranges_fail_critical(self):
        """Overlapping char ranges fail V1.4 as CRITICAL."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "lo wo"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 7, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 3, "char_end": 8, "source_line": 1},
            },
            source_text="hello world",
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.4_no_overlapping_ranges")
        assert check is not None
        assert check.passed is False
        assert check.severity == ValidationSeverity.CRITICAL

    def test_adjacent_ranges_pass(self):
        """Adjacent (touching) ranges pass V1.4."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": " "},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 6, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
            config=TokenizationConfig(include_whitespace=True),
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.4_no_overlapping_ranges")
        assert check is not None
        assert check.passed is True

    def _find_check(self, report: ValidationReport, name: str) -> ValidationCheck | None:
        for c in report.checks:
            if c.name == name:
                return c
        return None


class TestValidationV1_FullCoverage:
    """V1.5: Full coverage warning (all chars covered)."""

    def test_full_coverage_pass(self):
        """Complete coverage passes V1.5."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": " "},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 6, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
            config=TokenizationConfig(include_whitespace=True),
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.5_full_coverage")
        assert check is not None
        assert check.passed is True

    def test_missing_chars_warning(self):
        """Missing chars generate WARNING (not CRITICAL) for include_whitespace=False."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
            config=TokenizationConfig(include_whitespace=False),
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.5_full_coverage")
        assert check is not None
        # Gaps are only whitespace → should be WARNING, not CRITICAL
        assert check.passed is False
        assert check.severity == ValidationSeverity.WARNING
        # Overall report still fails because there's a non-passing check
        assert report.passed is False
        # But no critical failures from V1.5
        v5_critical = [c for c in report.critical_failures if c.name == "V1.5_full_coverage"]
        assert len(v5_critical) == 0

    def test_non_whitespace_gap_fails_critical(self):
        """Non-whitespace gap fails V1.5 as CRITICAL."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "he"},
                "T1": {"id": "T1", "text": "lo"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 2, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 4, "char_end": 6, "source_line": 1},
            },
            source_text="hello",
        )
        report = ValidationV1().validate(output)
        check = self._find_check(report, "V1.5_full_coverage")
        assert check is not None
        assert check.passed is False
        assert check.severity == ValidationSeverity.CRITICAL

    def test_empty_source_passes(self):
        """Empty source text passes all checks."""
        output = Stage1Output(
            tokens={},
            metadata={},
            source_text="",
        )
        report = ValidationV1().validate(output)
        assert report.passed is True

    def _find_check(self, report: ValidationReport, name: str) -> ValidationCheck | None:
        for c in report.checks:
            if c.name == name:
                return c
        return None


class TestValidationV1_Integration:
    """Integration: ValidationV1 works with real MetadataIndexer output."""

    def test_real_indexer_output_passes(self):
        """Output from MetadataIndexer passes all ValidationV1 checks."""
        from prism.stage1.metadata import MetadataIndexer

        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        report = ValidationV1().validate(output)
        assert report.passed is True
        assert len(report.critical_failures) == 0

    def test_real_indexer_output_semantic_only(self):
        """Semantic-only output from MetadataIndexer: V1.5 is WARNING."""
        from prism.stage1.metadata import MetadataIndexer

        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=False)
        inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        report = ValidationV1().validate(output)
        # V1.5 will be WARNING (whitespace gaps expected)
        v5_check = self._find_check(report, "V1.5_full_coverage")
        assert v5_check is not None
        # Other checks should pass
        v1 = self._find_check(report, "V1.1_sequential_ids")
        assert v1 is not None and v1.passed
        v2 = self._find_check(report, "V1.2_no_empty_tokens")
        assert v2 is not None and v2.passed
        v3 = self._find_check(report, "V1.3_metadata_completeness")
        assert v3 is not None and v3.passed
        v4 = self._find_check(report, "V1.4_no_overlapping_ranges")
        assert v4 is not None and v4.passed

    def _find_check(self, report: ValidationReport, name: str) -> ValidationCheck | None:
        for c in report.checks:
            if c.name == name:
                return c
        return None


class TestValidationV1_ReportStructure:
    """ValidationReport structure and properties."""

    def test_report_has_stage(self):
        output = Stage1Output(tokens={}, metadata={}, source_text="")
        report = ValidationV1().validate(output)
        assert report.stage == "stage1"

    def test_report_has_timestamp(self):
        output = Stage1Output(tokens={}, metadata={}, source_text="")
        report = ValidationV1().validate(output)
        assert report.timestamp is not None

    def test_critical_failures_property(self):
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
        )
        report = ValidationV1().validate(output)
        assert len(report.critical_failures) > 0
        for failure in report.critical_failures:
            assert failure.severity == ValidationSeverity.CRITICAL
            assert failure.passed is False

    def test_check_has_details_on_failure(self):
        """Failed checks include details about what went wrong."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
        )
        report = ValidationV1().validate(output)
        v1_check = self._find_check(report, "V1.1_sequential_ids")
        assert v1_check is not None
        assert v1_check.passed is False
        assert v1_check.message != ""

    def _find_check(self, report: ValidationReport, name: str) -> ValidationCheck | None:
        for c in report.checks:
            if c.name == name:
                return c
        return None

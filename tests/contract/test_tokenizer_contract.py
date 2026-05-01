"""Contract tests for Stage 1 ProcessingUnit implementations (P1.5).

Verifies that all Stage 1 ProcessingUnit implementations conform to the
ProcessingUnit contract defined in prism.core.processing_unit.

Contracts tested:
1. All implementations return Stage1Output type
2. All implementations accept valid input and reject invalid
3. All implementations have required methods (process, validate_input, validate_output, name, tier)
4. All implementations produce deterministic output for same input
5. ValidationUnit implementations return ValidationReport with required fields
"""

import pytest
from pydantic import BaseModel

from prism.core.processing_unit import ProcessingUnit
from prism.core.validation_unit import ValidationUnit, ValidationReport
from prism.schemas import Stage1Input, Stage1Output, TokenizationConfig
from prism.stage1.metadata import MetadataIndexer
from prism.stage1.tokenizer import SpacyTokenStreamBuilder
from prism.stage1.validation_v1 import ValidationV1


class TestProcessingUnitContract:
    """All Stage 1 ProcessingUnits must implement the ProcessingUnit contract."""

    @pytest.fixture(params=[SpacyTokenStreamBuilder, MetadataIndexer])
    def processing_unit_class(self, request):
        return request.param

    def test_class_implements_processing_unit(self, processing_unit_class):
        """Class is a subclass of ProcessingUnit."""
        assert issubclass(processing_unit_class, ProcessingUnit)

    def test_has_process_method(self, processing_unit_class):
        """Has callable process method."""
        instance = processing_unit_class()
        assert callable(getattr(instance, "process", None))

    def test_has_validate_input_method(self, processing_unit_class):
        """Has callable validate_input method."""
        instance = processing_unit_class()
        assert callable(getattr(instance, "validate_input", None))

    def test_has_validate_output_method(self, processing_unit_class):
        """Has callable validate_output method."""
        instance = processing_unit_class()
        assert callable(getattr(instance, "validate_output", None))

    def test_has_name_method(self, processing_unit_class):
        """Has callable name method returning string."""
        instance = processing_unit_class()
        name = instance.name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_has_tier_property(self, processing_unit_class):
        """Has tier property returning string."""
        instance = processing_unit_class()
        tier = instance.tier
        assert isinstance(tier, str)
        assert tier in ("python_nlp", "ml", "llm")

    def test_returns_stage1_output(self, processing_unit_class):
        """process() returns Stage1Output instance."""
        instance = processing_unit_class()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = instance.process(inp, config)
        assert isinstance(output, Stage1Output)

    def test_accepts_valid_input(self, processing_unit_class):
        """validate_input returns True for valid Stage1Input."""
        instance = processing_unit_class()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
        is_valid, error = instance.validate_input(inp)
        assert is_valid is True
        assert error == ""

    def test_rejects_empty_input(self, processing_unit_class):
        """validate_input returns False for empty input."""
        instance = processing_unit_class()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="", source_type="raw_text", config=config)
        is_valid, error = instance.validate_input(inp)
        assert is_valid is False
        assert error != ""

    def test_accepts_valid_file_input(self, processing_unit_class, tmp_path):
        """validate_input returns True for existing file."""
        f = tmp_path / "test.md"
        f.write_text("hello world", encoding="utf-8")
        instance = processing_unit_class()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=str(f), source_type="file", config=config)
        is_valid, error = instance.validate_input(inp)
        assert is_valid is True
        assert error == ""

    def test_rejects_missing_file(self, processing_unit_class, tmp_path):
        """validate_input returns False for missing file."""
        instance = processing_unit_class()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=str(tmp_path / "no.md"), source_type="file", config=config)
        is_valid, error = instance.validate_input(inp)
        assert is_valid is False
        assert error != ""

    def test_deterministic_output(self, processing_unit_class):
        """Same input produces same output."""
        instance1 = processing_unit_class()
        instance2 = processing_unit_class()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="hello world test", source_type="raw_text", config=config)

        output1 = instance1.process(inp, config)
        output2 = instance2.process(inp, config)

        assert output1.token_count == output2.token_count
        assert list(output1.tokens.keys()) == list(output2.tokens.keys())
        for tid in output1.tokens:
            assert output1.tokens[tid].text == output2.tokens[tid].text


class TestValidationUnitContract:
    """ValidationV1 must implement the ValidationUnit contract."""

    @pytest.fixture
    def validation_unit(self):
        return ValidationV1()

    def test_class_implements_validation_unit(self):
        """ValidationV1 is a subclass of ValidationUnit."""
        assert issubclass(ValidationV1, ValidationUnit)

    def test_has_validate_method(self, validation_unit):
        """Has callable validate method."""
        assert callable(getattr(validation_unit, "validate", None))

    def test_has_name_method(self, validation_unit):
        """Has callable name method returning string."""
        name = validation_unit.name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_validate_returns_validation_report(self, validation_unit):
        """validate() returns ValidationReport instance."""
        output = Stage1Output(tokens={}, metadata={}, source_text="")
        report = validation_unit.validate(output)
        assert isinstance(report, ValidationReport)

    def test_report_has_required_fields(self, validation_unit):
        """ValidationReport has stage, passed, timestamp, checks."""
        output = Stage1Output(tokens={}, metadata={}, source_text="")
        report = validation_unit.validate(output)
        assert report.stage is not None
        assert isinstance(report.passed, bool)
        assert report.timestamp is not None
        assert isinstance(report.checks, list)

    def test_report_has_critical_failures_property(self, validation_unit):
        """ValidationReport.critical_failures is a list."""
        output = Stage1Output(tokens={}, metadata={}, source_text="")
        report = validation_unit.validate(output)
        assert isinstance(report.critical_failures, list)

    def test_accepts_valid_stage1_output(self, validation_unit):
        """validate() works with valid Stage1Output."""
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello",
        )
        report = validation_unit.validate(output)
        assert isinstance(report, ValidationReport)

    def test_handles_invalid_input_gracefully(self, validation_unit):
        """validate() handles non-Stage1Output gracefully."""
        report = validation_unit.validate("not a model")
        assert isinstance(report, ValidationReport)
        assert report.passed is False

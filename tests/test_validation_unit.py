"""Unit tests for ValidationUnit abstract interface (P0.7)."""

import pytest
from datetime import datetime

from pydantic import BaseModel, ValidationError

from prism.core.validation_unit import (
    ValidationUnit,
    ValidationReport,
    ValidationCheck,
    ValidationSeverity,
    StubValidationUnit,
)
from prism.schemas import Stage1Output, GlobalPG


class TestValidationSeverityEnum:
    """Tests for the ValidationSeverity enum."""

    def test_severity_has_critical(self):
        """ValidationSeverity.CRITICAL exists."""
        assert ValidationSeverity.CRITICAL.value == "critical"

    def test_severity_has_warning(self):
        """ValidationSeverity.WARNING exists."""
        assert ValidationSeverity.WARNING.value == "warning"

    def test_severity_has_info(self):
        """ValidationSeverity.INFO exists."""
        assert ValidationSeverity.INFO.value == "info"

    def test_severity_count(self):
        """ValidationSeverity has exactly 3 values."""
        assert len(ValidationSeverity) == 3


class TestValidationCheck:
    """Tests for the ValidationCheck model."""

    def test_valid_check(self):
        """Valid ValidationCheck can be created."""
        check = ValidationCheck(
            id="V1.1",
            name="Sequential IDs",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message="All token IDs are sequential",
            details={"count": 42},
        )
        assert check.id == "V1.1"
        assert check.name == "Sequential IDs"
        assert check.passed is True
        assert check.severity == ValidationSeverity.CRITICAL

    def test_check_defaults(self):
        """ValidationCheck has default values for optional fields."""
        check = ValidationCheck(
            id="V1.1",
            name="Test",
            passed=True,
            severity=ValidationSeverity.INFO,
        )
        assert check.message == ""
        assert check.details == {}

    def test_check_with_all_severity_levels(self):
        """ValidationCheck works with all severity levels."""
        for severity in ValidationSeverity:
            check = ValidationCheck(
                id="V1.0",
                name="Test",
                passed=False,
                severity=severity,
            )
            assert check.severity == severity


class TestValidationReport:
    """Tests for the ValidationReport model."""

    def test_valid_report(self):
        """Valid ValidationReport can be created."""
        report = ValidationReport(
            stage="stage1",
            passed=True,
            checks=[],
        )
        assert report.stage == "stage1"
        assert report.passed is True
        assert isinstance(report.timestamp, datetime)

    def test_report_with_checks(self):
        """ValidationReport can contain checks."""
        checks = [
            ValidationCheck(
                id="V1.1",
                name="Sequential IDs",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
            ),
            ValidationCheck(
                id="V1.2",
                name="No empty tokens",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
            ),
        ]
        report = ValidationReport(
            stage="stage1",
            passed=True,
            checks=checks,
        )
        assert len(report.checks) == 2

    def test_report_timestamp_is_set(self):
        """ValidationReport has a timestamp."""
        report = ValidationReport(stage="stage1", passed=True)
        assert report.timestamp is not None
        assert isinstance(report.timestamp, datetime)

    def test_critical_failures_property_empty(self):
        """critical_failures returns empty list when no failures."""
        checks = [
            ValidationCheck(
                id="V1.1",
                name="Check",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
            ),
        ]
        report = ValidationReport(stage="stage1", passed=True, checks=checks)
        assert len(report.critical_failures) == 0

    def test_critical_failures_property_detects_failure(self):
        """critical_failures returns failed critical checks."""
        checks = [
            ValidationCheck(
                id="V1.1",
                name="Sequential IDs",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
            ),
            ValidationCheck(
                id="V1.2",
                name="Minor issue",
                passed=False,
                severity=ValidationSeverity.WARNING,
            ),
        ]
        report = ValidationReport(stage="stage1", passed=False, checks=checks)
        assert len(report.critical_failures) == 1
        assert report.critical_failures[0].id == "V1.1"

    def test_critical_failures_ignores_non_critical(self):
        """critical_failures only returns CRITICAL severity failures."""
        checks = [
            ValidationCheck(
                id="V1.2",
                name="Warning check",
                passed=False,
                severity=ValidationSeverity.WARNING,
            ),
            ValidationCheck(
                id="V1.3",
                name="Info check",
                passed=False,
                severity=ValidationSeverity.INFO,
            ),
        ]
        report = ValidationReport(stage="stage1", passed=False, checks=checks)
        assert len(report.critical_failures) == 0


class TestValidationUnitAbstract:
    """Tests for the ValidationUnit abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """ValidationUnit cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ValidationUnit()


class TestIncompleteValidationUnit:
    """Tests verifying that incomplete ValidationUnit subclasses fail."""

    def test_missing_validate_raises_typeerror(self):
        """Subclass missing validate() raises TypeError."""
        class IncompleteUnit(ValidationUnit):
            def name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteUnit()

    def test_missing_name_raises_typeerror(self):
        """Subclass missing name() raises TypeError."""
        class IncompleteUnit(ValidationUnit):
            def validate(self, data: BaseModel) -> ValidationReport:
                return ValidationReport(stage="test", passed=True)

        with pytest.raises(TypeError):
            IncompleteUnit()


class TestStubValidationUnit:
    """Tests for the StubValidationUnit concrete implementation."""

    def test_can_instantiate_stub(self):
        """StubValidationUnit can be instantiated."""
        unit = StubValidationUnit()
        assert isinstance(unit, ValidationUnit)

    def test_name_returns_non_empty_string(self):
        """name() returns a non-empty string."""
        unit = StubValidationUnit()
        name = unit.name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_validate_returns_report(self):
        """validate() returns a ValidationReport."""
        unit = StubValidationUnit()
        dummy_data = _DummyModel(value="test")
        report = unit.validate(dummy_data)
        assert isinstance(report, ValidationReport)

    def test_validate_report_passed_is_true(self):
        """Stub validate returns passed=True."""
        unit = StubValidationUnit()
        dummy_data = _DummyModel(value="test")
        report = unit.validate(dummy_data)
        assert report.passed is True

    def test_validate_report_checks_is_empty(self):
        """Stub validate returns empty checks list."""
        unit = StubValidationUnit()
        dummy_data = _DummyModel(value="test")
        report = unit.validate(dummy_data)
        assert report.checks == []

    def test_validate_with_stage1_output(self):
        """Stub validate works with Stage1Output."""
        unit = StubValidationUnit()
        dummy_output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello", "lemma": "hello", "pos": "NN", "ner_label": "O"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello",
        )
        report = unit.validate(dummy_output)
        assert isinstance(report, ValidationReport)
        assert report.passed is True

    def test_isinstance_check(self):
        """StubValidationUnit is an instance of ValidationUnit."""
        unit = StubValidationUnit()
        assert isinstance(unit, ValidationUnit)


class _DummyModel(BaseModel):
    """Minimal Pydantic model for testing."""
    value: str

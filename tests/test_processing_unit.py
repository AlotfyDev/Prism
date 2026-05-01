"""Unit tests for ProcessingUnit abstract interface (P0.6)."""

import pytest

from pydantic import BaseModel
from prism.core.processing_unit import ProcessingUnit, StubProcessingUnit
from prism.schemas import (
    AggregationConfig,
    Stage1Input,
    Stage1Output,
    Stage4Input,
    Stage4Output,
    TokenizationConfig,
)


class TestProcessingUnitAbstract:
    """Tests for the ProcessingUnit abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """ProcessingUnit cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ProcessingUnit()


class TestIncompleteSubclass:
    """Tests verifying that incomplete subclasses cannot be instantiated."""

    def test_missing_process_raises_typeerror(self):
        """Subclass missing process() raises TypeError."""
        class IncompleteUnit(ProcessingUnit):
            def validate_input(self, input_data):
                return True, ""
            def validate_output(self, output_data):
                return True, ""
            def name(self) -> str:
                return "incomplete"
            @property
            def tier(self) -> str:
                return "python_nlp"

        with pytest.raises(TypeError):
            IncompleteUnit()

    def test_missing_validate_input_raises_typeerror(self):
        """Subclass missing validate_input() raises TypeError."""
        class IncompleteUnit(ProcessingUnit):
            def process(self, input_data, config):
                pass
            def validate_output(self, output_data):
                return True, ""
            def name(self) -> str:
                return "incomplete"
            @property
            def tier(self) -> str:
                return "python_nlp"

        with pytest.raises(TypeError):
            IncompleteUnit()

    def test_missing_validate_output_raises_typeerror(self):
        """Subclass missing validate_output() raises TypeError."""
        class IncompleteUnit(ProcessingUnit):
            def process(self, input_data, config):
                pass
            def validate_input(self, input_data):
                return True, ""
            def name(self) -> str:
                return "incomplete"
            @property
            def tier(self) -> str:
                return "python_nlp"

        with pytest.raises(TypeError):
            IncompleteUnit()

    def test_missing_name_raises_typeerror(self):
        """Subclass missing name() raises TypeError."""
        class IncompleteUnit(ProcessingUnit):
            def process(self, input_data, config):
                pass
            def validate_input(self, input_data):
                return True, ""
            def validate_output(self, output_data):
                return True, ""
            @property
            def tier(self) -> str:
                return "python_nlp"

        with pytest.raises(TypeError):
            IncompleteUnit()

    def test_missing_tier_raises_typeerror(self):
        """Subclass missing tier property raises TypeError."""
        class IncompleteUnit(ProcessingUnit):
            def process(self, input_data, config):
                pass
            def validate_input(self, input_data):
                return True, ""
            def validate_output(self, output_data):
                return True, ""
            def name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteUnit()


class TestStubProcessingUnit:
    """Tests for the StubProcessingUnit concrete implementation."""

    def test_can_instantiate_stub(self):
        """StubProcessingUnit can be instantiated."""
        unit = StubProcessingUnit()
        assert isinstance(unit, ProcessingUnit)

    def test_name_returns_non_empty_string(self):
        """name() returns a non-empty string."""
        unit = StubProcessingUnit()
        name = unit.name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_tier_returns_valid_tier(self):
        """tier property returns a valid tier string."""
        unit = StubProcessingUnit()
        valid_tiers = {"python_nlp", "ml", "llm"}
        assert unit.tier in valid_tiers

    def test_validate_input_returns_true_for_valid(self):
        """validate_input returns (True, '') for valid input."""
        unit = StubProcessingUnit()
        dummy_input = _DummyModel(value="test")
        is_valid, error_msg = unit.validate_input(dummy_input)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_output_returns_true_for_valid(self):
        """validate_output returns (True, '') for valid output."""
        unit = StubProcessingUnit()
        dummy_output = _DummyModel(value="test")
        is_valid, error_msg = unit.validate_output(dummy_output)
        assert is_valid is True
        assert error_msg == ""

    def test_process_returns_output(self):
        """process() returns a valid output object."""
        unit = StubProcessingUnit()
        dummy_input = _DummyModel(value="test")
        dummy_config = _DummyModel(value="config")
        result = unit.process(dummy_input, dummy_config)
        assert result is not None

    def test_with_stage1_schema_types(self):
        """StubProcessingUnit works with Stage1 schema types."""
        unit: StubProcessingUnit[Stage1Input, Stage1Output, TokenizationConfig] = (
            StubProcessingUnit()
        )
        assert isinstance(unit.name(), str)
        assert unit.tier in {"python_nlp", "ml", "llm"}

    def test_with_stage4_schema_types(self):
        """StubProcessingUnit works with Stage4 schema types."""
        unit: StubProcessingUnit[Stage4Input, Stage4Output, AggregationConfig] = (
            StubProcessingUnit()
        )
        assert isinstance(unit.name(), str)
        assert unit.tier in {"python_nlp", "ml", "llm"}

    def test_isinstance_check(self):
        unit = StubProcessingUnit()
        assert isinstance(unit, ProcessingUnit)

    def test_version_default(self):
        unit = StubProcessingUnit()
        assert unit.version == "v0.0.0"

    def test_version_is_string(self):
        unit = StubProcessingUnit()
        assert isinstance(unit.version, str)


class _CustomVersionUnit(ProcessingUnit):
    def process(self, input_data, config):
        return _DummyModel(value="test")
    def validate_input(self, input_data):
        return True, ""
    def validate_output(self, output_data):
        return True, ""
    def name(self) -> str:
        return "custom"
    @property
    def tier(self) -> str:
        return "python_nlp"
    @property
    def version(self) -> str:
        return "v2.1.0"


class TestProcessingUnitVersion:
    def test_custom_version_override(self):
        unit = _CustomVersionUnit()
        assert unit.version == "v2.1.0"

    def test_default_version_is_v0(self):
        unit = StubProcessingUnit()
        assert unit.version == "v0.0.0"


class _DummyModel(BaseModel):
    """Minimal Pydantic model for testing generic constraints."""
    value: str

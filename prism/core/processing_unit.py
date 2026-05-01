"""ProcessingUnit abstract interface for all Prism pipeline stages."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)
ConfigT = TypeVar("ConfigT", bound=BaseModel)


class ProcessingUnit(ABC, Generic[InputT, OutputT, ConfigT]):
    """Abstract contract for ALL Prism processing units.

    ANY implementation (spaCy, Stanza, LLM, rule-based, ML) MUST satisfy
    this contract. The pipeline does NOT know which implementation is used —
    it only validates that the output matches the schema.

    Key invariant: Regardless of which implementation tier is used, the
    OutputT type is ALWAYS the same. Swapping implementations NEVER changes
    the data flow.
    """

    @abstractmethod
    def process(self, input_data: InputT, config: ConfigT) -> OutputT:
        """Execute the processing step. Returns output matching the unit's output schema."""
        ...

    @abstractmethod
    def validate_input(self, input_data: InputT) -> tuple[bool, str]:
        """Verify input meets requirements before processing.

        Returns:
            Tuple of (is_valid, error_message).
        """
        ...

    @abstractmethod
    def validate_output(self, output_data: OutputT) -> tuple[bool, str]:
        """Verify output matches the expected schema after processing.

        Returns:
            Tuple of (is_valid, error_message).
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging and debugging."""
        ...

    @property
    @abstractmethod
    def tier(self) -> str:
        """Implementation tier: 'python_nlp', 'ml', or 'llm'."""
        ...

    @property
    def version(self) -> str:
        """Implementation version for tracking and compatibility checks.

        Default is 'v0.0.0' — override in subclasses to track iterations.
        """
        return "v0.0.0"


class _StubOutput(BaseModel):
    """Minimal placeholder output for stub processing."""
    pass


class StubProcessingUnit(ProcessingUnit[InputT, OutputT, ConfigT]):
    """Concrete stub implementation for testing the interface contract.

    Returns pass-through validation and a placeholder output.
    Used to verify that the ProcessingUnit contract is correctly
    implemented and can be subclassed.
    """

    def process(self, input_data: InputT, config: ConfigT) -> OutputT:
        return _StubOutput()  # type: ignore[return-value]

    def validate_input(self, input_data: InputT) -> tuple[bool, str]:
        return True, ""

    def validate_output(self, output_data: OutputT) -> tuple[bool, str]:
        return True, ""

    def name(self) -> str:
        return "StubProcessingUnit"

    @property
    def tier(self) -> str:
        return "python_nlp"

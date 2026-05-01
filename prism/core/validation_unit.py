"""ValidationUnit abstract interface for inter-stage validation gates."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity levels for validation checks."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ValidationCheck(BaseModel):
    """A single validation check result."""
    id: str
    name: str
    passed: bool
    severity: ValidationSeverity
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Aggregated result from a validation gate."""
    stage: str
    passed: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checks: list[ValidationCheck] = Field(default_factory=list)

    @property
    def critical_failures(self) -> list[ValidationCheck]:
        """Return all failed critical checks."""
        return [
            c for c in self.checks
            if c.severity == ValidationSeverity.CRITICAL and not c.passed
        ]


class ValidationUnit(ABC):
    """Abstract contract for inter-stage validation gates (V0–V4).

    Each validation gate inspects the output of a pipeline stage and
    returns a report indicating whether the data is fit to proceed
    to the next stage.
    """

    @abstractmethod
    def validate(self, data: BaseModel) -> ValidationReport:
        """Run all checks against the stage output and return a report."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging and debugging."""
        ...


class StubValidationUnit(ValidationUnit):
    """Concrete stub implementation for testing the ValidationUnit contract.

    Always returns a passing report with no checks.
    """

    def validate(self, data: BaseModel) -> ValidationReport:
        return ValidationReport(stage="stub", passed=True, checks=[])

    def name(self) -> str:
        return "StubValidationUnit"

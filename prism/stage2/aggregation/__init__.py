"""Aggregation package exports."""

from prism.stage2.aggregation.aggregation_models import (
    AssemblyInput,
    CodeBlockIndex,
    CodeLine,
    Conflict,
    CorrelatedReport,
    Correlation,
    HeadingAnomaly,
    HeadingGroup,
    HeadingSequenceReport,
    HeadingViolation,
    IndentationPattern,
    IndentationPatternInfo,
    ListIndex,
    ListItemIndex,
    NestedItem,
    NestingValidationReport,
    NestingViolation,
    TableIndex,
    TokenRangeIndex,
    UnifiedInstance,
)
from prism.stage2.aggregation.aggregation_protocols import IAggregator

__all__ = [
    # Protocols
    "IAggregator",
    # Models
    "AssemblyInput",
    "CodeBlockIndex",
    "CodeLine",
    "Conflict",
    "CorrelatedReport",
    "Correlation",
    "HeadingAnomaly",
    "HeadingGroup",
    "HeadingSequenceReport",
    "HeadingViolation",
    "IndentationPattern",
    "IndentationPatternInfo",
    "ListIndex",
    "ListItemIndex",
    "NestedItem",
    "NestingValidationReport",
    "NestingViolation",
    "TableIndex",
    "TokenRangeIndex",
    "UnifiedInstance",
]

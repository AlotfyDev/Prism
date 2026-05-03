"""Stage 2 pipeline protocols — structural subtyping interfaces.

Defines typing.Protocol classes for each Stage 2 processing step.
No inheritance required — any class matching the signature is compliant.
@runtime_checkable enables isinstance() checks at runtime.

Usage:
    from prism.stage2.protocols import IClassifier
    from prism.stage2.classifier import LayerClassifier

    assert isinstance(LayerClassifier(), IClassifier)  # True
"""

from typing import Protocol, runtime_checkable

from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyTree,
    MarkdownNode,
    PhysicalComponent,
    Stage2Output,
)
from prism.schemas.token import Stage1Output
from prism.stage2.aggregation.aggregation_models import (
    AssemblyInput,
    CodeBlockIndex,
    CorrelatedReport,
    HeadingSequenceReport,
    IndentationPattern,
    ListIndex,
    NestingValidationReport,
    TableIndex,
    TokenRangeIndex,
)
from prism.stage2.pipeline_models import (
    ClassifierInput,
    HierarchyInput,
    MapperInput,
    MapperOutput,
    TokenSpanInput,
    TokenSpanOutput,
    TopologyInput,
)


@runtime_checkable
class IParser(Protocol):
    """Protocol for Markdown → AST parser step."""

    def process(
        self,
        input_data: Stage1Output,
        config: object | None = None,
    ) -> list[MarkdownNode]: ...

    def validate_input(
        self,
        input_data: Stage1Output,
    ) -> tuple[bool, str]: ...

    def validate_output(
        self,
        output_data: list[MarkdownNode],
    ) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class IClassifier(Protocol):
    """Protocol for AST → DetectedLayersReport classifier step."""

    def process(
        self,
        input_data: ClassifierInput,
        config: object | None = None,
    ) -> DetectedLayersReport: ...

    def validate_input(
        self,
        input_data: ClassifierInput,
    ) -> tuple[bool, str]: ...

    def validate_output(
        self,
        output_data: DetectedLayersReport,
    ) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class IHierarchyBuilder(Protocol):
    """Protocol for DetectedLayersReport → HierarchyTree step."""

    def process(
        self,
        input_data: HierarchyInput,
        config: object | None = None,
    ) -> HierarchyTree: ...

    def validate_input(
        self,
        input_data: HierarchyInput,
    ) -> tuple[bool, str]: ...

    def validate_output(
        self,
        output_data: HierarchyTree,
    ) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class IComponentMapper(Protocol):
    """Protocol for HierarchyTree → PhysicalComponents step."""

    def process(
        self,
        input_data: MapperInput,
        config: object | None = None,
    ) -> MapperOutput: ...

    def validate_input(
        self,
        input_data: MapperInput,
    ) -> tuple[bool, str]: ...

    def validate_output(
        self,
        output_data: MapperOutput,
    ) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class ITokenSpanMapper(Protocol):
    """Protocol for PhysicalComponents + Stage1Output → token mapping step."""

    def process(
        self,
        input_data: TokenSpanInput,
        config: object | None = None,
    ) -> TokenSpanOutput: ...

    def validate_input(
        self,
        input_data: TokenSpanInput,
    ) -> tuple[bool, str]: ...

    def validate_output(
        self,
        output_data: TokenSpanOutput,
    ) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class ITopologyBuilder(Protocol):
    """Protocol for PhysicalComponents + token_mapping → Stage2Output step."""

    def process(
        self,
        input_data: TopologyInput,
        config: object | None = None,
    ) -> Stage2Output: ...

    def validate_input(
        self,
        input_data: TopologyInput,
    ) -> tuple[bool, str]: ...

    def validate_output(
        self,
        output_data: Stage2Output,
    ) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


# =============================================================================
# Aggregation Protocols (Phase 4)
# =============================================================================


@runtime_checkable
class IDetectorCorrelator(Protocol):
    """Protocol for cross-detector correlation aggregation."""

    def aggregate(self, input_data: DetectedLayersReport) -> CorrelatedReport: ...

    def validate_input(self, input_data: DetectedLayersReport) -> tuple[bool, str]: ...

    def validate_output(self, output_data: CorrelatedReport) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class ITokenRangeAggregator(Protocol):
    """Protocol for bidirectional Token <-> Component mapping."""

    def aggregate(self, input_data: dict) -> TokenRangeIndex: ...

    def validate_input(self, input_data: dict) -> tuple[bool, str]: ...

    def validate_output(self, output_data: TokenRangeIndex) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class ITableAggregator(Protocol):
    """Protocol for table matrix parsing."""

    def aggregate(self, input_data: list[MarkdownNode]) -> list[TableIndex]: ...

    def validate_input(self, input_data: list[MarkdownNode]) -> tuple[bool, str]: ...

    def validate_output(self, output_data: list[TableIndex]) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class IListAggregator(Protocol):
    """Protocol for list matrix parsing."""

    def aggregate(self, input_data: list[MarkdownNode]) -> list[ListIndex]: ...

    def validate_input(self, input_data: list[MarkdownNode]) -> tuple[bool, str]: ...

    def validate_output(self, output_data: list[ListIndex]) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class ICodeBlockAggregator(Protocol):
    """Protocol for code block line parsing."""

    def aggregate(self, input_data: list[MarkdownNode]) -> list[CodeBlockIndex]: ...

    def validate_input(self, input_data: list[MarkdownNode]) -> tuple[bool, str]: ...

    def validate_output(self, output_data: list[CodeBlockIndex]) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class IHeadingSequenceAnalyzer(Protocol):
    """Protocol for heading sequence validation (spaCy-enhanced)."""

    def aggregate(self, input_data: list) -> HeadingSequenceReport: ...

    def validate_input(self, input_data: list) -> tuple[bool, str]: ...

    def validate_output(self, output_data: HeadingSequenceReport) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class IIndentationAnalyzer(Protocol):
    """Protocol for heading indentation pattern analysis."""

    def aggregate(self, input_data: list) -> IndentationPattern: ...

    def validate_input(self, input_data: list) -> tuple[bool, str]: ...

    def validate_output(self, output_data: IndentationPattern) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class INestingValidator(Protocol):
    """Protocol for nesting validation."""

    def aggregate(self, input_data: dict) -> NestingValidationReport: ...

    def validate_input(self, input_data: dict) -> tuple[bool, str]: ...

    def validate_output(self, output_data: NestingValidationReport) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...


@runtime_checkable
class ITopologyAssembler(Protocol):
    """Protocol for final Stage2Output assembly."""

    def aggregate(self, input_data: AssemblyInput) -> Stage2Output: ...

    def validate_input(self, input_data: AssemblyInput) -> tuple[bool, str]: ...

    def validate_output(self, output_data: Stage2Output) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...

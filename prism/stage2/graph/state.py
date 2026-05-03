"""LangGraph state model for Stage 2 subgraph.

Holds intermediate results between each pipeline step.
Populated progressively as the graph executes.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyTree,
    MarkdownNode,
    PhysicalComponent,
    Stage2Output,
)
from prism.stage2.aggregation.aggregation_models import (
    CodeBlockIndex,
    CorrelatedReport,
    HeadingSequenceReport,
    IndentationPattern,
    ListIndex,
    NestingValidationReport,
    TableIndex,
    TokenRangeIndex,
)


class Stage2GraphState(BaseModel):
    """Accumulated state for Stage 2 LangGraph subgraph.

    Each pipeline step reads from and writes to this state.
    Fields are populated progressively as the graph executes.
    """

    # Input (from Stage 1)
    source_text: str = Field(
        default="",
        description="Original Markdown source",
    )

    # Step 1: Parser
    nodes: list[MarkdownNode] = Field(
        default_factory=list,
        description="AST root nodes",
    )

    # Step 2: Classifier
    report: DetectedLayersReport | None = Field(
        default=None,
        description="Layer detection report",
    )

    # Step 3: HierarchyBuilder
    tree: HierarchyTree | None = Field(
        default=None,
        description="Component hierarchy tree",
    )

    # Step 4: ComponentMapper
    components: list[PhysicalComponent] = Field(
        default_factory=list,
        description="Typed components",
    )

    # Step 5: TokenSpanMapper
    token_mapping: dict[str, list[str]] = Field(
        default_factory=dict,
        description="component_id -> list of global token IDs",
    )

    # Step 6: TopologyBuilder (final output)
    stage2_output: Stage2Output | None = Field(
        default=None,
        description="Final Stage 2 output",
    )

    # Cross-cutting
    errors: list[str] = Field(
        default_factory=list,
        description="Accumulated errors",
    )
    current_step: str = Field(
        default="init",
        description="Current pipeline step name",
    )
    retry_count: dict[str, int] = Field(
        default_factory=dict,
        description="Retry count per step",
    )

    # Aggregation fields (Phase 4)
    correlated_report: CorrelatedReport | None = Field(
        default=None,
        description="Cross-detector correlation report",
    )
    heading_sequence: HeadingSequenceReport | None = Field(
        default=None,
        description="Heading sequence analysis",
    )
    table_indices: dict[str, TableIndex] = Field(
        default_factory=dict,
        description="Table indices by component_id",
    )
    list_indices: dict[str, ListIndex] = Field(
        default_factory=dict,
        description="List indices by component_id",
    )
    codeblock_indices: dict[str, CodeBlockIndex] = Field(
        default_factory=dict,
        description="Code block indices by component_id",
    )
    token_range_index: TokenRangeIndex | None = Field(
        default=None,
        description="Bidirectional token range index",
    )
    indentation_pattern: IndentationPattern | None = Field(
        default=None,
        description="Heading indentation pattern",
    )
    nesting_validation: NestingValidationReport | None = Field(
        default=None,
        description="Nesting validation report",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def has_error(self) -> bool:
        return len(self.errors) > 0

    def last_error(self) -> str | None:
        return self.errors[-1] if self.errors else None

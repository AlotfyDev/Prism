"""Stage 2 Aggregation Output Models.

Pydantic models for all aggregation step outputs.
Consumed by TopologyAssembler to build final Stage2Output.
"""

from typing import Any

from pydantic import BaseModel, Field

from prism.schemas.enums import LayerType
from prism.schemas.physical import HeadingComponent


# =============================================================================
# Heading Sequence Models
# =============================================================================


class HeadingViolation(BaseModel):
    """A heading that breaks the expected sequence pattern."""

    heading: HeadingComponent = Field(
        ...,
        description="The heading component that violates the sequence",
    )
    expected_levels: list[int] = Field(
        default_factory=list,
        description="Expected levels after the previous heading (e.g., [1, 2] for H3 after H1)",
    )
    actual_level: int = Field(
        ...,
        ge=1,
        le=6,
        description="Actual heading level found",
    )
    severity: str = Field(
        ...,
        description="Violation severity: 'skip' or 'jump_back'",
    )


class HeadingGroup(BaseModel):
    """A group of headings under a parent heading."""

    parent: HeadingComponent = Field(
        ...,
        description="The parent heading for this group",
    )
    siblings: list[HeadingComponent] = Field(
        default_factory=list,
        description="Sibling headings at the same level as parent's immediate children",
    )
    children: list["HeadingGroup"] = Field(
        default_factory=list,
        description="Sub-groups (recursive nesting)",
    )
    depth: int = Field(
        default=0,
        ge=0,
        description="Depth in the heading hierarchy (0 = root)",
    )


HeadingGroup.model_rebuild()


class IndentationPatternInfo(BaseModel):
    """Indentation pattern for a single heading."""

    heading_id: str = Field(
        ...,
        description="Component ID of the heading",
    )
    level: int = Field(
        ...,
        ge=1,
        le=6,
        description="Heading level (1-6)",
    )
    indentation: int = Field(
        default=0,
        ge=0,
        description="Leading spaces before heading marker",
    )


class HeadingSequenceReport(BaseModel):
    """Output of HeadingSequenceAnalyzer aggregation step."""

    headings: list[HeadingComponent] = Field(
        default_factory=list,
        description="All heading components sorted by char_start",
    )
    sequence: list[int] = Field(
        default_factory=list,
        description="Sequence of heading levels (e.g., [1, 2, 2, 3, 2, 1])",
    )
    is_valid: bool = Field(
        default=True,
        description="True if no level skips (level[i+1] <= level[i] + 1)",
    )
    violations: list[HeadingViolation] = Field(
        default_factory=list,
        description="List of heading sequence violations",
    )
    groups: list[HeadingGroup] = Field(
        default_factory=list,
        description="Headings grouped by parent heading",
    )
    indentation_pattern: str = Field(
        default="standard",
        description="Pattern type: 'standard', 'indented', or 'mixed'",
    )
    max_depth: int = Field(
        default=0,
        ge=0,
        description="Deepest heading level used in the document",
    )
    total_headings: int = Field(
        default=0,
        ge=0,
        description="Total number of headings",
    )
    spacy_enhanced: bool = Field(
        default=False,
        description="True if spaCy POS analysis was applied",
    )


# =============================================================================
# Cross-Detector Correlation Models
# =============================================================================


class Correlation(BaseModel):
    """A detected correlation between two layer instances."""

    type: str = Field(
        ...,
        description="Correlation type: 'caption', 'diagram', 'table_title', 'figure_content'",
    )
    source_type: LayerType = Field(
        ...,
        description="Primary layer type",
    )
    target_type: LayerType = Field(
        ...,
        description="Correlated layer type",
    )
    source_id: str = Field(
        ...,
        description="Component ID of source instance",
    )
    target_id: str = Field(
        ...,
        description="Component ID of target instance",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Correlation confidence (0.0-1.0)",
    )
    method: str = Field(
        ...,
        description="Detection method: 'proximity', 'keyword', 'embedding', or 'combined'",
    )


class Conflict(BaseModel):
    """Overlapping but incompatible detections."""

    source_id: str = Field(
        ...,
        description="Component ID of first instance",
    )
    target_id: str = Field(
        ...,
        description="Component ID of second instance",
    )
    source_type: LayerType = Field(
        ...,
        description="Layer type of first instance",
    )
    target_type: LayerType = Field(
        ...,
        description="Layer type of second instance",
    )
    reason: str = Field(
        ...,
        description="Conflict reason: 'char_overlap' or 'type_conflict'",
    )
    char_overlap_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of character overlap",
    )
    resolution: str = Field(
        default="keep_larger",
        description="Resolution strategy: 'keep_larger', 'keep_first', or 'flag'",
    )


class UnifiedInstance(BaseModel):
    """A merged instance from correlated detections."""

    primary_id: str = Field(
        ...,
        description="Primary component ID",
    )
    primary_type: LayerType = Field(
        ...,
        description="Primary layer type",
    )
    correlated_ids: list[str] = Field(
        default_factory=list,
        description="IDs of correlated instances",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Enriched attributes from correlation",
    )


class CorrelatedReport(BaseModel):
    """Output of DetectorCorrelation aggregation step."""

    correlations: list[Correlation] = Field(
        default_factory=list,
        description="Detected correlations between instances",
    )
    unified_instances: list[UnifiedInstance] = Field(
        default_factory=list,
        description="Merged instances from correlation",
    )
    conflicts: list[Conflict] = Field(
        default_factory=list,
        description="Overlapping but incompatible detections",
    )
    total_correlations: int = Field(
        default=0,
        ge=0,
        description="Total number of correlations found",
    )
    deduplicated_count: int = Field(
        default=0,
        ge=0,
        description="Number of instances merged via correlation",
    )
    embedding_enhanced: bool = Field(
        default=False,
        description="True if e5-small embeddings were used",
    )


# =============================================================================
# Table Index Models
# =============================================================================


class TableIndex(BaseModel):
    """Structured table index from markdown-it-py AST."""

    component_id: str = Field(
        ...,
        description="Component ID of the table",
    )
    dimensions: tuple[int, int] = Field(
        ...,
        description="(rows, cols) — table dimensions",
    )
    has_header: bool = Field(
        default=False,
        description="True if first row is a header",
    )
    header_cells: list[str] = Field(
        default_factory=list,
        description="Header cell texts",
    )
    cell_matrix: list[list[dict[str, Any]]] = Field(
        default_factory=list,
        description="2D matrix of cell metadata (text, char_start, char_end)",
    )
    raw_markdown: str = Field(
        ...,
        min_length=1,
        description="Original markdown source",
    )


# =============================================================================
# List Index Models
# =============================================================================


class ListItemIndex(BaseModel):
    """A single list item with depth info."""

    item_index: int = Field(
        ...,
        ge=0,
        description="Position in list (0-based)",
    )
    depth: int = Field(
        default=0,
        ge=0,
        description="Nesting depth (0 = top level)",
    )
    text: str = Field(
        default="",
        description="Item text content",
    )
    has_children: bool = Field(
        default=False,
        description="True if item contains a nested list",
    )


class NestedItem(BaseModel):
    """A hierarchical list item with children."""

    item: ListItemIndex = Field(
        ...,
        description="The list item",
    )
    children: list["NestedItem"] = Field(
        default_factory=list,
        description="Child items (recursive)",
    )


NestedItem.model_rebuild()


class ListIndex(BaseModel):
    """Structured list index with nesting hierarchy."""

    component_id: str = Field(
        ...,
        description="Component ID of the list",
    )
    style: str = Field(
        default="unordered",
        description="List style: 'ordered' or 'unordered'",
    )
    total_items: int = Field(
        default=0,
        ge=0,
        description="All items (including nested)",
    )
    top_level_items: int = Field(
        default=0,
        ge=0,
        description="Direct children only",
    )
    max_depth: int = Field(
        default=0,
        ge=0,
        description="Deepest nesting level",
    )
    items: list[ListItemIndex] = Field(
        default_factory=list,
        description="Flat list with depth info",
    )
    nesting_tree: list[NestedItem] = Field(
        default_factory=list,
        description="Hierarchical structure",
    )
    indentation_levels: list[int] = Field(
        default_factory=list,
        description="Indentation levels found (e.g., [0, 2, 4])",
    )


# =============================================================================
# Code Block Index Models
# =============================================================================


class CodeLine(BaseModel):
    """A single line within a code block."""

    line_number: int = Field(
        ...,
        ge=0,
        description="Line number (0-based)",
    )
    content: str = Field(
        ...,
        description="Line content",
    )
    is_empty: bool = Field(
        default=False,
        description="True if line is empty or whitespace only",
    )
    indentation: int = Field(
        default=0,
        ge=0,
        description="Leading spaces/tabs",
    )


class CodeBlockIndex(BaseModel):
    """Structured code block index with line numbers."""

    component_id: str = Field(
        ...,
        description="Component ID of the code block",
    )
    language: str = Field(
        default="",
        description="Programming language (e.g., 'python', 'mermaid')",
    )
    total_lines: int = Field(
        default=0,
        ge=0,
        description="Total number of lines",
    )
    non_empty_lines: int = Field(
        default=0,
        ge=0,
        description="Number of non-empty lines",
    )
    lines: list[CodeLine] = Field(
        default_factory=list,
        description="Line-by-line breakdown",
    )
    indentation_pattern: list[int] = Field(
        default_factory=list,
        description="Indentation per line",
    )
    has_syntax_markers: bool = Field(
        default=False,
        description="True if line numbers or highlights detected",
    )


# =============================================================================
# Token Range Index Models
# =============================================================================


class TokenRangeIndex(BaseModel):
    """Bidirectional Token <-> Component index."""

    # Forward: component -> tokens
    component_to_tokens: dict[str, list[str]] = Field(
        default_factory=dict,
        description="component_id -> list of token IDs",
    )

    # Reverse: token -> component
    token_to_component: dict[str, str] = Field(
        default_factory=dict,
        description="token_id -> component_id",
    )

    # Gaps
    unassigned_tokens: list[str] = Field(
        default_factory=list,
        description="Token IDs not belonging to any component",
    )

    # Coverage
    coverage_pct: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Percentage of tokens assigned to components",
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total number of tokens",
    )
    assigned_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens assigned to components",
    )


# =============================================================================
# Indentation Analysis Models
# =============================================================================


class HeadingAnomaly(BaseModel):
    """A heading with inconsistent indentation."""

    heading_id: str = Field(
        ...,
        description="Component ID of the anomalous heading",
    )
    expected_indent: int = Field(
        default=0,
        ge=0,
        description="Expected indentation based on pattern",
    )
    actual_indent: int = Field(
        default=0,
        ge=0,
        description="Actual indentation found",
    )
    level: int = Field(
        ...,
        ge=1,
        le=6,
        description="Heading level",
    )


class IndentationPattern(BaseModel):
    """Output of IndentationAnalyzer aggregation step."""

    headings: list[IndentationPatternInfo] = Field(
        default_factory=list,
        description="Headings with their indentation info",
    )
    is_consistent: bool = Field(
        default=True,
        description="True if all headings use same indentation style",
    )
    levels: list[int] = Field(
        default_factory=list,
        description="Unique indentation levels found (e.g., [0, 2, 4])",
    )
    pattern_type: str = Field(
        default="standard",
        description="Pattern type: 'standard', 'indented', or 'mixed'",
    )
    groups_by_indent: dict[int, list[str]] = Field(
        default_factory=dict,
        description="Indentation level -> list of heading IDs",
    )
    anomalies: list[HeadingAnomaly] = Field(
        default_factory=list,
        description="Headings that break the indentation pattern",
    )
    total_headings: int = Field(
        default=0,
        ge=0,
        description="Total headings analyzed",
    )


# =============================================================================
# Nesting Validation Models
# =============================================================================


class NestingViolation(BaseModel):
    """A single nesting rule violation."""

    parent_id: str = Field(
        ...,
        description="Parent component ID",
    )
    child_id: str = Field(
        ...,
        description="Child component ID",
    )
    parent_type: LayerType = Field(
        ...,
        description="Parent layer type",
    )
    child_type: LayerType = Field(
        ...,
        description="Child layer type",
    )
    reason: str = Field(
        ...,
        description="Violation reason",
    )


class NestingValidationReport(BaseModel):
    """Output of NestingValidator aggregation step."""

    is_valid: bool = Field(
        default=True,
        description="True if no nesting violations found",
    )
    violations: list[NestingViolation] = Field(
        default_factory=list,
        description="List of nesting violations",
    )
    max_depth: int = Field(
        default=0,
        ge=0,
        description="Maximum nesting depth in hierarchy",
    )
    total_components: int = Field(
        default=0,
        ge=0,
        description="Total components validated",
    )
    depth_distribution: dict[int, int] = Field(
        default_factory=dict,
        description="Depth -> count of components at that depth",
    )
    container_stats: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-container: children_count, types",
    )


# =============================================================================
# Topology Assembly Input/Output
# =============================================================================


class AssemblyInput(BaseModel):
    """Input for TopologyAssembler aggregation step."""

    components: dict[str, Any] = Field(
        default_factory=dict,
        description="component_id -> PhysicalComponent (as dict for flexibility)",
    )
    heading_sequence: HeadingSequenceReport | None = Field(
        default=None,
        description="Heading sequence analysis result",
    )
    correlations: CorrelatedReport | None = Field(
        default=None,
        description="Cross-detector correlation result",
    )
    token_range_index: TokenRangeIndex | None = Field(
        default=None,
        description="Bidirectional token range index",
    )
    nesting_validation: NestingValidationReport | None = Field(
        default=None,
        description="Nesting validation result",
    )
    indentation_pattern: IndentationPattern | None = Field(
        default=None,
        description="Indentation pattern analysis",
    )

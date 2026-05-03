"""Stage 2 pipeline Input/Output wrapper models.

Provides Pydantic models that wrap the inputs and outputs of each
Stage 2 processing step, ensuring uniform signatures:
    process(input: InputModel, config) -> OutputModel

This enables:
- Single-parameter input/output for all steps
- Consistent Protocol compliance
- LangGraph StateGraph state accumulation
"""

from pydantic import BaseModel, Field

from prism.schemas.physical import (
    DetectedLayersReport,
    HierarchyTree,
    MarkdownNode,
    PhysicalComponent,
    Stage2Output,
)
from prism.schemas.token import Stage1Output


# =============================================================================
# Parser Wrappers
# =============================================================================

class ParserOutput(BaseModel):
    """Wraps list[MarkdownNode] for IParser output."""

    nodes: list[MarkdownNode] = Field(
        default_factory=list,
        description="AST root nodes from parser",
    )

    @property
    def node_count(self) -> int:
        return len(self.nodes)


# =============================================================================
# Classifier Wrappers
# =============================================================================

class ClassifierInput(BaseModel):
    """Wraps multi-param input for IClassifier.process()."""

    nodes: list[MarkdownNode] = Field(
        default_factory=list,
        description="AST root nodes from parser",
    )
    source_text: str = Field(
        default="",
        description="Original Markdown source text",
    )


# =============================================================================
# HierarchyBuilder Wrappers
# =============================================================================

class HierarchyInput(BaseModel):
    """Wraps input for IHierarchyBuilder.process()."""

    report: DetectedLayersReport = Field(
        ...,
        description="Layer detection report from classifier",
    )


# =============================================================================
# ComponentMapper Wrappers
# =============================================================================

class MapperInput(BaseModel):
    """Wraps input for IComponentMapper.process()."""

    tree: HierarchyTree = Field(
        ...,
        description="Hierarchy tree from HierarchyBuilder",
    )


class MapperOutput(BaseModel):
    """Wraps list[PhysicalComponent] for IComponentMapper output."""

    components: list[PhysicalComponent] = Field(
        default_factory=list,
        description="Typed physical components",
    )

    @property
    def component_count(self) -> int:
        return len(self.components)


# =============================================================================
# TokenSpanMapper Wrappers
# =============================================================================

class TokenSpanInput(BaseModel):
    """Wraps multi-param input for ITokenSpanMapper.process()."""

    components: list[PhysicalComponent] = Field(
        ...,
        description="Typed components to map",
    )
    stage1_output: Stage1Output = Field(
        ...,
        description="Stage 1 tokens and metadata for char→token mapping",
    )


class TokenSpanOutput(BaseModel):
    """Wraps dict[str, list[str]] for ITokenSpanMapper output."""

    component_to_tokens: dict[str, list[str]] = Field(
        default_factory=dict,
        description="component_id -> list of global token IDs",
    )


# =============================================================================
# TopologyBuilder Wrappers
# =============================================================================

class TopologyInput(BaseModel):
    """Wraps multi-param input for ITopologyBuilder.process()."""

    components: list[PhysicalComponent] = Field(
        ...,
        description="Typed physical components",
    )
    token_mapping: dict[str, list[str]] = Field(
        default_factory=dict,
        description="component_id -> list of global token IDs",
    )

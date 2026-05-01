"""Physical component schema models for Stage 2 (Physical Topology)."""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from prism.schemas.enums import LayerType


_COMPONENT_ID_PATTERN = re.compile(r"^[a-z_]+:.+$")


class PhysicalComponent(BaseModel):
    """A discovered physical layer component (paragraph, table, list, etc.).

    Component IDs follow the pattern `{layer_type}:{identifier}`.
    """

    component_id: str = Field(
        ...,
        description="Unique ID in format `{layer_type}:{identifier}`",
    )
    layer_type: LayerType = Field(
        ...,
        description="Physical layer type",
    )
    raw_content: str = Field(
        ...,
        min_length=1,
        description="Raw Markdown content of this component",
    )
    token_span: Optional[tuple[int, int]] = Field(
        default=None,
        description="Global token ID range (start, end) inclusive",
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="Parent component_id (for nested structures)",
    )
    children: list[str] = Field(
        default_factory=list,
        description="List of child component_ids",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Extra attributes (e.g., heading level, list style)",
    )

    @field_validator("component_id")
    @classmethod
    def validate_component_id_pattern(cls, v: str) -> str:
        if not _COMPONENT_ID_PATTERN.match(v):
            raise ValueError(
                f"component_id must match `{{layer_type}}:{{identifier}}` pattern, got: {v!r}"
            )
        return v

    @model_validator(mode="after")
    def validate_id_matches_layer_type(self) -> "PhysicalComponent":
        expected_prefix = f"{self.layer_type.value}:"
        if not self.component_id.startswith(expected_prefix):
            raise ValueError(
                f"component_id must start with layer type prefix '{expected_prefix}', "
                f"got: {self.component_id!r}"
            )
        return self

    @property
    def token_range(self) -> tuple[int, int]:
        if self.token_span is None:
            raise ValueError("token_span not set")
        return self.token_span

    @property
    def token_count(self) -> int:
        if self.token_span is None:
            return 0
        start, end = self.token_span
        return max(0, end - start + 1)


class TopologyConfig(BaseModel):
    """Configuration for the Stage 2 physical topology analysis."""

    layer_types_to_detect: list[LayerType] = Field(
        default=list(LayerType),
        description="Layer types to detect (default: all)",
    )
    nesting_depth_limit: int = Field(
        default=10,
        ge=1,
        description="Maximum nesting depth before raising warning",
    )


class Stage2Input(BaseModel):
    """Input schema for the physical topology stage.

    Requires Stage 1 output plus optional topology configuration.
    """

    source_text: str = Field(..., description="Original source text from Stage 1")
    token_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of global token IDs from Stage 1",
    )
    config: TopologyConfig = Field(default_factory=TopologyConfig)


class Stage2Output(BaseModel):
    """Output schema for the physical topology stage."""

    discovered_layers: dict[str, PhysicalComponent] = Field(
        default_factory=dict,
        description="Map of component_id -> PhysicalComponent",
    )
    layer_types: set[LayerType] = Field(
        default_factory=set,
        description="Set of unique layer types found in the document",
    )
    is_single_layer: bool = Field(
        default=True,
        description="True if the document contains only one layer type",
    )
    component_to_tokens: dict[str, tuple[int, int]] = Field(
        default_factory=dict,
        description="Map of component_id -> (token_start, token_end)",
    )

    @property
    def component_count(self) -> int:
        return len(self.discovered_layers)

    @model_validator(mode="after")
    def compute_layer_properties(self) -> "Stage2Output":
        """Derive layer_types and is_single_layer from discovered_layers."""
        if self.discovered_layers:
            self.layer_types = {
                comp.layer_type for comp in self.discovered_layers.values()
            }
            self.is_single_layer = len(self.layer_types) == 1
        return self

    @model_validator(mode="after")
    def build_component_to_tokens(self) -> "Stage2Output":
        """Build component_to_tokens mapping from discovered_layers."""
        self.component_to_tokens = {}
        for comp_id, comp in self.discovered_layers.items():
            if comp.token_span is not None:
                self.component_to_tokens[comp_id] = comp.token_span
        return self

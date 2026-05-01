"""Physical component schema models for Stage 2 (Physical Topology)."""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from prism.schemas.enums import LayerType


class NodeType(str, Enum):
    """AST node types produced by MarkdownItParser.

    Maps to LayerType for physical topology classification.
    Inline, HR, and LIST_ITEM are parser-level concepts, not physical layers.
    """

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    HR = "hr"
    INLINE = "inline"

    def to_layer_type(self) -> Optional[LayerType]:
        """Convert NodeType to LayerType if applicable.

        Returns None for parser-only types (inline, hr, list_item).
        """
        mapping = {
            NodeType.HEADING: LayerType.HEADING,
            NodeType.PARAGRAPH: LayerType.PARAGRAPH,
            NodeType.TABLE: LayerType.TABLE,
            NodeType.LIST: LayerType.LIST,
            NodeType.LIST_ITEM: None,
            NodeType.CODE_BLOCK: LayerType.CODE_BLOCK,
            NodeType.BLOCKQUOTE: LayerType.BLOCKQUOTE,
            NodeType.HR: None,
            NodeType.INLINE: None,
        }
        return mapping.get(self)


class MarkdownNode(BaseModel):
    """A node in the parsed Markdown AST.

    Produced by MarkdownItParser. Consumed by LayerClassifier (P2.2)
    which maps NodeType → PhysicalComponent.
    """

    node_type: NodeType = Field(
        ...,
        description="AST node type",
    )
    raw_content: str = Field(
        ...,
        min_length=1,
        description="Raw Markdown text for this node",
    )
    char_start: Optional[int] = Field(
        default=None,
        description="Character offset in source text (start, inclusive)",
    )
    char_end: Optional[int] = Field(
        default=None,
        description="Character offset in source text (end, exclusive)",
    )
    level: Optional[int] = Field(
        default=None,
        description="Heading level (1-6), or nesting depth for lists",
    )
    children: list["MarkdownNode"] = Field(
        default_factory=list,
        description="Child nodes in the AST tree",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Extra attributes (e.g., language for code blocks)",
    )


# Resolve forward reference
MarkdownNode.model_rebuild()


class LayerInstance(BaseModel):
    """A single detected instance of a physical layer type.

    Produced by Stage 2a (Detection). Consumed by Stage 2b (Classifier)
    which converts instances into PhysicalComponent objects.
    """

    layer_type: LayerType = Field(
        ...,
        description="Physical layer type of this instance",
    )
    char_start: int = Field(
        ...,
        ge=0,
        description="Character offset in source text (start, inclusive)",
    )
    char_end: int = Field(
        ...,
        ge=0,
        description="Character offset in source text (end, exclusive)",
    )
    line_start: int = Field(
        ...,
        ge=0,
        description="Line number in source text (0-indexed, inclusive)",
    )
    line_end: int = Field(
        ...,
        ge=0,
        description="Line number in source text (0-indexed, exclusive)",
    )
    raw_content: str = Field(
        ...,
        min_length=1,
        description="Raw Markdown content of this instance",
    )
    depth: int = Field(
        default=0,
        ge=0,
        description="Nesting depth (0 = root, 1 = first level nested, etc.)",
    )
    sibling_index: int = Field(
        default=0,
        ge=0,
        description="Position among siblings at the same nesting level",
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="ID of parent instance (None for root-level instances)",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Extra attributes (e.g., heading_level=2, language=python, style=unordered)",
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> "LayerInstance":
        if self.char_end <= self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must be > char_start ({self.char_start})"
            )
        if self.line_end <= self.line_start:
            raise ValueError(
                f"line_end ({self.line_end}) must be >= line_start ({self.line_start})"
            )
        return self


# =============================================================================
# NESTING MATRIX — Validation rules for parent-child hierarchy
# =============================================================================

# Leaf types: cannot contain any children
_LEAF_TYPES: frozenset[LayerType] = frozenset({
    LayerType.CODE_BLOCK,
    LayerType.DIAGRAM,
    LayerType.FIGURE,
    LayerType.METADATA,
})

# Container types: can contain children, with max_depth limits
# max_depth: 1 = no recursive nesting of same type, -1 = unlimited
_CONTAINER_RULES: dict[LayerType, tuple[set[LayerType], int]] = {
    LayerType.HEADING: (
        {
            LayerType.PARAGRAPH,
            LayerType.LIST,
            LayerType.TABLE,
            LayerType.CODE_BLOCK,
            LayerType.BLOCKQUOTE,
            LayerType.FIGURE,
            LayerType.DIAGRAM,
        },
        1,  # heading cannot contain another heading
    ),
    LayerType.PARAGRAPH: (
        {LayerType.FIGURE},  # inline images only
        1,
    ),
    LayerType.LIST: (
        {
            LayerType.PARAGRAPH,
            LayerType.LIST,       # recursive: sub-lists
            LayerType.CODE_BLOCK,
            LayerType.FIGURE,
        },
        -1,  # unlimited sub-list depth
    ),
    LayerType.TABLE: (
        {LayerType.FIGURE},  # images inside cells
        1,
    ),
    LayerType.BLOCKQUOTE: (
        {
            LayerType.HEADING,
            LayerType.PARAGRAPH,
            LayerType.LIST,
            LayerType.TABLE,
            LayerType.CODE_BLOCK,
            LayerType.BLOCKQUOTE,  # recursive: nested quotes
            LayerType.FIGURE,
        },
        -1,  # unlimited quote nesting
    ),
    LayerType.FOOTNOTE: (
        {LayerType.PARAGRAPH, LayerType.FIGURE},
        1,
    ),
}


class NestingRule(BaseModel):
    """A single parent-child nesting rule."""

    parent: LayerType = Field(..., description="The container type")
    allowed_children: set[LayerType] = Field(
        default_factory=set,
        description="Types this parent can contain",
    )
    max_depth: int = Field(
        default=1,
        description="Max recursive depth (-1 = unlimited)",
    )

    @property
    def is_leaf(self) -> bool:
        """True if this type cannot contain any children."""
        return len(self.allowed_children) == 0

    @property
    def allows_recursive_nesting(self) -> bool:
        """True if this type allows unlimited nesting depth."""
        return self.max_depth == -1


class NestingMatrix(BaseModel):
    """Complete nesting validation rules for all 10 LayerType values.

    This is the source of truth for parent-child hierarchy validation.
    Read by LayerClassifier to validate component hierarchies.
    Not embedded in PhysicalComponent — it's a read-only rule set.
    """

    rules: dict[LayerType, NestingRule] = Field(
        default_factory=dict,
        description="LayerType -> its nesting rule",
    )

    @classmethod
    def default(cls) -> "NestingMatrix":
        """Build the canonical nesting matrix from _CONTAINER_RULES and _LEAF_TYPES."""
        rules: dict[LayerType, NestingRule] = {}

        # Container types
        for lt, (children, max_depth) in _CONTAINER_RULES.items():
            rules[lt] = NestingRule(
                parent=lt,
                allowed_children=children,
                max_depth=max_depth,
            )

        # Leaf types
        for lt in _LEAF_TYPES:
            rules[lt] = NestingRule(
                parent=lt,
                allowed_children=set(),
                max_depth=0,
            )

        return cls(rules=rules)

    def can_contain(self, parent: LayerType, child: LayerType) -> bool:
        """Check if a parent type can contain a child type."""
        rule = self.rules.get(parent)
        if rule is None:
            return False
        return child in rule.allowed_children

    def is_leaf(self, layer_type: LayerType) -> bool:
        """Check if a type is a leaf (cannot contain children)."""
        rule = self.rules.get(layer_type)
        if rule is None:
            return True
        return rule.is_leaf

    def max_depth_for(self, layer_type: LayerType) -> int:
        """Get the max nesting depth for a type."""
        rule = self.rules.get(layer_type)
        if rule is None:
            return 0
        return rule.max_depth

    def get_valid_children(self, parent: LayerType) -> set[LayerType]:
        """Get all types that can be children of the given parent."""
        rule = self.rules.get(parent)
        if rule is None:
            return set()
        return rule.allowed_children

    def get_valid_parents(self, child: LayerType) -> set[LayerType]:
        """Get all types that can contain the given child."""
        return {
            lt
            for lt, rule in self.rules.items()
            if child in rule.allowed_children
        }

    def validate_hierarchy(
        self,
        children: list[tuple[LayerType, int]],
        parent_type: LayerType,
        parent_depth: int = 0,
    ) -> tuple[bool, str]:
        """Validate a list of (child_type, child_depth) against nesting rules.

        Returns (is_valid, error_message).
        """
        rule = self.rules.get(parent_type)
        if rule is None:
            return False, f"Unknown parent type: {parent_type}"

        if rule.is_leaf:
            return False, f"LayerType '{parent_type.value}' is a leaf — cannot contain children"

        for child_type, child_depth in children:
            if child_type not in rule.allowed_children:
                return False, (
                    f"LayerType '{parent_type.value}' cannot contain "
                    f"'{child_type.value}'"
                )

            if rule.max_depth != -1 and child_depth > rule.max_depth:
                return False, (
                    f"LayerType '{child_type.value}' nesting depth {child_depth} "
                    f"exceeds max_depth {rule.max_depth} under '{parent_type.value}'"
                )

        return True, ""


# Global nesting matrix instance
NESTING_MATRIX: NestingMatrix = NestingMatrix.default()


class DetectedLayersReport(BaseModel):
    """Output of Stage 2a: Detection/Exploration phase.

    Reports which layer types exist in the document and where each
    instance is located. All 10 LayerType values are discoverable.

    All 10 LayerType values are supported:
    - paragraph, heading, list, table, code_block, blockquote
      (detected directly by markdown-it-py)
    - metadata (YAML front matter via front_matter plugin)
    - footnote (via footnote plugin)
    - diagram (mermaid/graphviz code blocks, detected by classifier rule)
    - figure (image blocks, detected by classifier rule)
    """

    source_text: str = Field(
        ...,
        description="Original source text from Stage 1",
    )
    detected_types: set[LayerType] = Field(
        default_factory=set,
        description="Layer types found in the document",
    )
    instances: dict[LayerType, list[LayerInstance]] = Field(
        default_factory=dict,
        description="Layer type -> list of detected instances",
    )

    @model_validator(mode="after")
    def sync_detected_types(self) -> "DetectedLayersReport":
        """Ensure detected_types matches instances keys."""
        self.detected_types = set(self.instances.keys())
        return self

    @property
    def total_instances(self) -> int:
        """Total number of detected instances across all layer types."""
        return sum(len(v) for v in self.instances.values())

    def instances_of(self, layer_type: LayerType) -> list[LayerInstance]:
        """Get all instances of a specific layer type."""
        return self.instances.get(layer_type, [])

    def has_type(self, layer_type: LayerType) -> bool:
        """Check if a specific layer type was detected."""
        return layer_type in self.detected_types

    def layer_counts(self) -> dict[str, int]:
        """Return count per layer type name."""
        return {lt.value: len(instances) for lt, instances in self.instances.items()}


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

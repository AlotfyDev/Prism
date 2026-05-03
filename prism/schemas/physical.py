"""Physical component schema models for Stage 2 (Physical Topology)."""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from prism.schemas.enums import LayerType


class NodeType(str, Enum):
    """AST node types produced by MarkdownItParser.

    Maps to LayerType for physical topology classification.
    Inline, HR, LIST_ITEM, METADATA, and FOOTNOTE are parser-level concepts, not physical layers.
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
    METADATA = "metadata"
    FOOTNOTE = "footnote"

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
            NodeType.METADATA: LayerType.METADATA,
            NodeType.FOOTNOTE: LayerType.FOOTNOTE,
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
    LayerType.INLINE_CODE,
    LayerType.EMPHASIS,
    LayerType.LINK,
    LayerType.HTML_BLOCK,
    LayerType.HTML_INLINE,
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
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        },
        1,
    ),
    LayerType.PARAGRAPH: (
        {
            LayerType.FIGURE,
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        },
        1,
    ),
    LayerType.LIST: (
        {
            LayerType.PARAGRAPH,
            LayerType.LIST,
            LayerType.TABLE,
            LayerType.CODE_BLOCK,
            LayerType.BLOCKQUOTE,
            LayerType.FIGURE,
            LayerType.DIAGRAM,
            LayerType.HEADING,
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        },
        -1,
    ),
    LayerType.TABLE: (
        {
            LayerType.PARAGRAPH,
            LayerType.LIST,
            LayerType.TABLE,
            LayerType.CODE_BLOCK,
            LayerType.BLOCKQUOTE,
            LayerType.FIGURE,
            LayerType.DIAGRAM,
            LayerType.HEADING,
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        },
        1,
    ),
    LayerType.BLOCKQUOTE: (
        {
            LayerType.HEADING,
            LayerType.PARAGRAPH,
            LayerType.LIST,
            LayerType.TABLE,
            LayerType.CODE_BLOCK,
            LayerType.BLOCKQUOTE,
            LayerType.FIGURE,
            LayerType.HTML_BLOCK,
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        },
        -1,
    ),
    LayerType.FOOTNOTE: (
        {
            LayerType.PARAGRAPH,
            LayerType.FIGURE,
            LayerType.INLINE_CODE,
            LayerType.EMPHASIS,
            LayerType.LINK,
            LayerType.HTML_INLINE,
        },
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


class HierarchyNode(BaseModel):
    """A node in the component hierarchy tree.

    Produced by HierarchyBuilder (Stage 2.2c). Links a LayerInstance
    to its parent and children within the validated hierarchy.
    """

    instance: LayerInstance = Field(
        ...,
        description="The layer instance at this hierarchy position",
    )
    children: list["HierarchyNode"] = Field(
        default_factory=list,
        description="Child hierarchy nodes (validated against NestingMatrix)",
    )

    @property
    def component_id(self) -> str:
        """Stable ID derived from layer type and position."""
        return f"{self.instance.layer_type.value}:depth{self.instance.depth}_sib{self.instance.sibling_index}"

    @property
    def depth(self) -> int:
        """Tree depth (root = 0)."""
        return self.instance.depth

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0


HierarchyNode.model_rebuild()


class HierarchyTree(BaseModel):
    """Root-level hierarchy tree of all detected layer instances.

    Produced by HierarchyBuilder (Stage 2.2c). Validates parent-child
    relationships against NestingMatrix and assigns component IDs.

    Consumed by ComponentMapper (Stage 2.2d) to produce typed components.
    """

    root_nodes: list[HierarchyNode] = Field(
        default_factory=list,
        description="Root-level hierarchy nodes (depth=0)",
    )
    total_nodes: int = Field(
        default=0,
        ge=0,
        description="Total number of nodes in the tree (computed)",
    )
    max_depth: int = Field(
        default=0,
        ge=0,
        description="Maximum nesting depth in the tree (computed)",
    )

    @model_validator(mode="after")
    def compute_tree_properties(self) -> "HierarchyTree":
        """Count total nodes and compute max depth."""
        count = 0
        max_d = 0

        def _walk(node: HierarchyNode) -> None:
            nonlocal count, max_d
            count += 1
            max_d = max(max_d, node.depth)
            for child in node.children:
                _walk(child)

        for root in self.root_nodes:
            _walk(root)

        self.total_nodes = count
        self.max_depth = max_d
        return self

    def flatten(self) -> list[LayerInstance]:
        """Return all LayerInstance objects in tree order."""
        result: list[LayerInstance] = []

        def _walk(node: HierarchyNode) -> None:
            result.append(node.instance)
            for child in node.children:
                _walk(child)

        for root in self.root_nodes:
            _walk(root)

        return result

    def get_node_by_id(self, target_id: str) -> Optional[HierarchyNode]:
        """Find a node by its component_id."""

        def _walk(nodes: list[HierarchyNode]) -> Optional[HierarchyNode]:
            for node in nodes:
                if node.component_id == target_id:
                    return node
                result = _walk(node.children)
                if result:
                    return result
            return None

        return _walk(self.root_nodes)


# =============================================================================
# PHYSICAL COMPONENT — typed layer components
# =============================================================================

_COMPONENT_ID_PATTERN = re.compile(r"^[a-z_]+:.+$")


class PhysicalComponent(BaseModel):
    """A discovered physical layer component (paragraph, table, list, etc.).

    Component IDs follow the pattern `{layer_type}:{identifier}`.
    Char offsets are transferred from LayerInstance to enable
    TokenSpanMapper to map components to global token IDs.
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
    char_start: int = Field(
        ...,
        ge=0,
        description="Character offset in source text (start, inclusive). Transferred from LayerInstance.",
    )
    char_end: int = Field(
        ...,
        ge=0,
        description="Character offset in source text (end, exclusive). Transferred from LayerInstance.",
    )
    token_span: Optional[tuple[int, int]] = Field(
        default=None,
        description="Global token ID range (start, end) inclusive. Populated by TokenSpanMapper.",
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

    @model_validator(mode="after")
    def validate_char_offsets(self) -> "PhysicalComponent":
        if self.char_end <= self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must be > char_start ({self.char_start})"
            )
        return self

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
    def char_length(self) -> int:
        return self.char_end - self.char_start

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


# =============================================================================
# TYPED COMPONENT MODELS — One per LayerType (P2.6)
# =============================================================================


class EmphasisType(str, Enum):
    """Type of emphasis detected."""

    BOLD = "bold"
    ITALIC = "italic"
    STRIKETHROUGH = "strikethrough"
    BOLD_ITALIC = "bold_italic"


class LinkType(str, Enum):
    """Type of link detected."""

    INLINE = "inline"
    REFERENCE = "reference"
    IMAGE = "image"
    AUTO = "auto"


class HeadingComponent(PhysicalComponent):
    """A heading physical component with level and text."""

    level: int = Field(
        ...,
        ge=1,
        le=6,
        description="Heading level (1-6)",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Heading text without markdown symbols",
    )
    anchor_id: Optional[str] = Field(
        default=None,
        description="Generated anchor ID for the heading",
    )


class ParagraphComponent(PhysicalComponent):
    """A paragraph physical component."""

    word_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Word count of the paragraph",
    )


class CodeBlockComponent(PhysicalComponent):
    """A code block physical component with language info."""

    language: Optional[str] = Field(
        default=None,
        description="Programming language of the code block",
    )
    has_lines: bool = Field(
        default=False,
        description="Whether line numbers are shown",
    )


class DiagramComponent(PhysicalComponent):
    """A diagram physical component (mermaid, graphviz, etc.)."""

    diagram_type: str = Field(
        ...,
        min_length=1,
        description="Diagram type (mermaid, graphviz, etc.)",
    )
    title: Optional[str] = Field(
        default=None,
        description="Diagram title",
    )


class FootnoteComponent(PhysicalComponent):
    """A footnote physical component."""

    footnote_id: str = Field(
        ...,
        min_length=1,
        description="Footnote identifier",
    )
    has_url: bool = Field(
        default=False,
        description="Whether the footnote contains URLs",
    )


class MetadataComponent(PhysicalComponent):
    """A metadata/front-matter physical component."""

    format: str = Field(
        ...,
        description="Metadata format (yaml, toml)",
    )
    keys: list[str] = Field(
        default_factory=list,
        description="Metadata keys found in front matter",
    )


class FigureComponent(PhysicalComponent):
    """A figure/image physical component."""

    image_url: str = Field(
        ...,
        min_length=1,
        description="URL or path of the image",
    )
    alt_text: str = Field(
        default="",
        description="Alt text for the image",
    )
    width: Optional[int] = Field(
        default=None,
        gt=0,
        description="Image width in pixels",
    )
    height: Optional[int] = Field(
        default=None,
        gt=0,
        description="Image height in pixels",
    )


class BlockquoteComponent(PhysicalComponent):
    """A blockquote physical component."""

    style: str = Field(
        default="blockquote",
        description="Blockquote style (blockquote, note, tip, warning, etc.)",
    )
    quote_level: int = Field(
        default=1,
        ge=1,
        description="Nesting depth of the blockquote (1 = single >)",
    )
    attribution: Optional[str] = Field(
        default=None,
        description="Attribution/source of the quote",
    )


class InlineCodeComponent(PhysicalComponent):
    """An inline code physical component."""

    content: str = Field(
        ...,
        min_length=1,
        description="Code content without backticks",
    )
    language_hint: Optional[str] = Field(
        default=None,
        description="Hint about the code language",
    )
    syntax_category: Optional[str] = Field(
        default=None,
        description="Syntax category (variable, function, command, etc.)",
    )


class EmphasisComponent(PhysicalComponent):
    """An emphasis (bold/italic/strikethrough) physical component."""

    emphasis_type: EmphasisType = Field(
        ...,
        description="Type of emphasis",
    )
    marker: str = Field(
        ...,
        min_length=1,
        description="Markdown marker used (**, *, __, _, ~~)",
    )


class LinkComponent(PhysicalComponent):
    """A link physical component."""

    link_type: LinkType = Field(
        ...,
        description="Type of link",
    )
    text: str = Field(
        ...,
        description="Link text or alt text",
    )
    url: str = Field(
        ...,
        min_length=1,
        description="Target URL or reference identifier",
    )
    is_external: Optional[bool] = Field(
        default=None,
        description="Whether the link points to an external resource",
    )
    domain: Optional[str] = Field(
        default=None,
        description="Domain extracted from the URL",
    )


class HtmlBlockComponent(PhysicalComponent):
    """An HTML block physical component."""

    tag_name: str = Field(
        ...,
        min_length=1,
        description="HTML tag name",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="HTML attributes as key-value pairs",
    )
    is_semantic: bool = Field(
        default=False,
        description="Whether the tag is a semantic HTML5 element",
    )


class HtmlInlineComponent(PhysicalComponent):
    """An HTML inline physical component."""

    tag_name: str = Field(
        ...,
        min_length=1,
        description="HTML tag name",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="HTML attributes as key-value pairs",
    )
    is_self_closing: bool = Field(
        default=False,
        description="Whether the element is self-closing",
    )


# =============================================================================
# NESTED OBJECT SCHEMAS — Table and List internal structure
# =============================================================================


class CellPosition(BaseModel):
    """Position of a component inside a table cell."""

    row: int = Field(
        ...,
        ge=0,
        description="Row index (0-based)",
    )
    col: int = Field(
        ...,
        ge=0,
        description="Column index (0-based)",
    )
    is_header: bool = Field(
        default=False,
        description="True if this cell is in the header row",
    )


class ListStyle(str, Enum):
    """List rendering style."""

    ORDERED = "ordered"
    UNORDERED = "unordered"


class ListItem(BaseModel):
    """A single item within a list component.

    List items are structural elements (not LayerTypes). Each item
    can contain child PhysicalComponents (paragraphs, sub-lists,
    code blocks, figures, etc.).
    """

    item_index: int = Field(
        ...,
        ge=0,
        description="Position in parent list (0-based)",
    )
    children: list[str] = Field(
        default_factory=list,
        description="Child PhysicalComponent IDs (paragraphs, sub-lists, code blocks, etc.)",
    )
    char_start: Optional[int] = Field(
        default=None,
        description="Character offset in source text (start, inclusive)",
    )
    char_end: Optional[int] = Field(
        default=None,
        description="Character offset in source text (end, exclusive)",
    )


class TableCell(BaseModel):
    """A single cell within a table row.

    Table cells are structural elements (not LayerTypes). Each cell
    can contain child PhysicalComponents (paragraphs, lists, code blocks,
    figures, diagrams, etc.).
    """

    position: CellPosition = Field(
        ...,
        description="Row and column position of this cell",
    )
    children: list[str] = Field(
        default_factory=list,
        description="Child PhysicalComponent IDs within this cell",
    )
    char_start: Optional[int] = Field(
        default=None,
        description="Character offset in source text (start, inclusive)",
    )
    char_end: Optional[int] = Field(
        default=None,
        description="Character offset in source text (end, exclusive)",
    )


class TableRow(BaseModel):
    """A single row within a table component."""

    row_index: int = Field(
        ...,
        ge=0,
        description="Row index (0-based)",
    )
    cells: list[TableCell] = Field(
        default_factory=list,
        description="Cells in this row (length must match table num_cols)",
    )


class TableComponent(PhysicalComponent):
    """A table physical component with structured row/cell layout.

    Extends PhysicalComponent with explicit table structure:
    - rows: organized by TableRow → TableCell → child components
    - num_cols: column count (validated for consistency)
    - has_header: whether first row is a header

    The inherited `children` field holds all child component IDs (flat),
    while `rows` provides the structured hierarchical view.
    """

    rows: list[TableRow] = Field(
        default_factory=list,
        description="Table rows with cells and their child components",
    )
    num_cols: int = Field(
        default=0,
        ge=0,
        description="Number of columns (auto-set from rows if 0)",
    )
    has_header: bool = Field(
        default=False,
        description="True if the first row is a header row",
    )

    @model_validator(mode="after")
    def validate_table_structure(self) -> "TableComponent":
        if self.rows:
            # Auto-detect num_cols from first row if not set
            if self.num_cols == 0:
                self.num_cols = len(self.rows[0].cells)

            # Validate all rows have consistent column count
            for row in self.rows:
                if len(row.cells) != self.num_cols:
                    raise ValueError(
                        f"Table {self.component_id}: row {row.row_index} has "
                        f"{len(row.cells)} cells, expected {self.num_cols}"
                    )

            # Validate cell positions match row/cell indices
            for row in self.rows:
                for cell in row.cells:
                    if cell.position.row != row.row_index:
                        raise ValueError(
                            f"Table {self.component_id}: cell at ({cell.position.row}, "
                            f"{cell.position.col}) has row mismatch with parent row {row.row_index}"
                        )
                    expected_col = row.cells.index(cell)
                    if cell.position.col != expected_col:
                        raise ValueError(
                            f"Table {self.component_id}: cell at row {row.row_index} "
                            f"has col {cell.position.col}, expected {expected_col}"
                        )

            # Validate header row position flag
            for row in self.rows:
                for cell in row.cells:
                    expected_header = self.has_header and row.row_index == 0
                    if cell.position.is_header != expected_header:
                        raise ValueError(
                            f"Table {self.component_id}: cell ({cell.position.row}, "
                            f"{cell.position.col}) is_header={cell.position.is_header} "
                            f"doesn't match expected={expected_header}"
                        )

        return self


class ListComponent(PhysicalComponent):
    """A list physical component with structured item layout.

    Extends PhysicalComponent with explicit list structure:
    - items: organized by ListItem → child components
    - style: ordered (numbered) or unordered (bulleted)

    The inherited `children` field holds all child component IDs (flat),
    while `items` provides the structured hierarchical view.
    """

    items: list[ListItem] = Field(
        default_factory=list,
        description="List items with their child components",
    )
    style: ListStyle = Field(
        default=ListStyle.UNORDERED,
        description="List rendering style (ordered or unordered)",
    )

    @model_validator(mode="after")
    def validate_list_structure(self) -> "ListComponent":
        if self.items:
            # Validate item indices are sequential
            for i, item in enumerate(self.items):
                if item.item_index != i:
                    raise ValueError(
                        f"List {self.component_id}: item at position {i} has "
                        f"item_index={item.item_index}, expected {i}"
                    )
        return self


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


# =============================================================================
# TYPED COMPONENT UNION — Union of all 15 typed component models (P2.6)
# =============================================================================

TypedComponent = (
    HeadingComponent
    | ParagraphComponent
    | CodeBlockComponent
    | DiagramComponent
    | FootnoteComponent
    | MetadataComponent
    | FigureComponent
    | BlockquoteComponent
    | InlineCodeComponent
    | EmphasisComponent
    | LinkComponent
    | HtmlBlockComponent
    | HtmlInlineComponent
    | TableComponent
    | ListComponent
)


class Stage2Output(BaseModel):
    """Output schema for the physical topology stage.

    ``discovered_layers`` accepts any of the 15 typed component models
    (all subclasses of PhysicalComponent). The ``TypedComponent`` union
    type alias is provided for type hints and IDE autocomplete.
    """

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
        """Build component_to_tokens mapping from discovered_layers.

        Only derives from component.token_span when component_to_tokens
        was not pre-populated (e.g., by TopologyBuilder via TokenSpanMapper).
        """
        if self.component_to_tokens:
            return self
        for comp_id, comp in self.discovered_layers.items():
            if comp.token_span is not None:
                self.component_to_tokens[comp_id] = comp.token_span
        return self

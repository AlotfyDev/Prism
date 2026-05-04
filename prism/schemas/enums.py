"""Shared enums and type definitions for Prism schemas."""

from enum import Enum


class LayerType(str, Enum):
    """Known physical layer types in a Markdown document."""

    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    DIAGRAM = "diagram"
    HEADING = "heading"
    CODE_BLOCK = "code_block"
    FOOTNOTE = "footnote"
    METADATA = "metadata"
    FIGURE = "figure"
    BLOCKQUOTE = "blockquote"
    INLINE_CODE = "inline_code"
    EMPHASIS = "emphasis"
    LINK = "link"
    HTML_BLOCK = "html_block"
    HTML_INLINE = "html_inline"
    TASK_LIST = "task_list"
    HORIZONTAL_RULE = "horizontal_rule"
    INDENTED_CODE_BLOCK = "indented_code_block"
    FOOTNOTE_REF = "footnote_ref"


class EntityType(str, Enum):
    """Known entity types for semantic extraction."""

    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "LOC"
    DATE = "DATE"
    CONCEPT = "CONCEPT"
    EVENT = "EVENT"
    PRODUCT = "PRODUCT"
    CUSTOM = "CUSTOM"


class SemanticLevel(str, Enum):
    """Hierarchical level of a semantic tree node."""

    DOCUMENT = "document"
    SECTION = "section"
    LAYER = "layer"
    UNIT = "unit"


class RelationType(str, Enum):
    """Canonical relation taxonomy (frozen for v1)."""

    CAUSES = "CAUSES"
    DEPENDS_ON = "DEPENDS_ON"
    PART_OF = "PART_OF"
    LOCATED_IN = "LOCATED_IN"
    TEMPORAL = "TEMPORAL"
    ARGUMENT_FOR = "ARGUMENT_FOR"
    ARGUMENT_AGAINST = "ARGUMENT_AGAINST"
    CONDITIONAL = "CONDITIONAL"
    OTHER = "OTHER"


class ExtractionTier(str, Enum):
    """Processing tier that produced a result."""

    PYTHON_NLP = "python_nlp"
    ML_MODEL = "ml_model"
    LLM = "llm"


class EntityMergeStrategy(str, Enum):
    """Strategy for merging entities across layers."""

    UNION = "union"
    INTERSECTION = "intersection"
    WEIGHTED = "weighted"


class ConflictResolution(str, Enum):
    """Strategy for resolving contradictory relationships."""

    CONFIDENCE_VOTE = "confidence_vote"
    LLM_ADJUDICATE = "llm_adjudicate"
    RULE_PRIORITY = "rule_priority"


class TopicClustering(str, Enum):
    """Method for clustering topics across layers."""

    EMBEDDING = "embedding"
    LEXICAL = "lexical"
    LLM = "llm"


class ConfidenceScorer(str, Enum):
    """Method for computing confidence scores."""

    STATISTICAL = "statistical"
    LLM = "llm"


class TokenType(str, Enum):
    """Token origin classification for downstream stage routing.

    Semantic tokens carry linguistic meaning (words, punctuation, symbols).
    Structural tokens represent layout/spacing (whitespace, newlines, indentation).

    P2 Physical Topology uses this to skip structural tokens when building
    semantic components, while still having access to paragraph break info
    from structural token metadata.
    """

    SEMANTIC = "semantic"
    STRUCTURAL = "structural"


class LLMProvider(str, Enum):
    """Supported LLM providers in priority chain."""

    OPENCODE = "opencode"
    KILOCODE = "kilocode"
    CLINE = "cline"
    OPENROUTER = "openrouter"
    CODEX = "codex"

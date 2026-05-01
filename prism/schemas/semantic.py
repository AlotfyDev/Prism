"""Semantic schema models for Stage 3 (Semantic Topology / MiniPG)."""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from prism.schemas.enums import EntityType, ExtractionTier, RelationType, SemanticLevel


_ENTITY_ID_PATTERN = re.compile(r"^E_[A-Z]+_\d+$")
_RELATION_ID_PATTERN = re.compile(r"^R_\d+$")
_PREDICATE_FRAME_PATTERN = re.compile(r"^[a-z_]+$")


class MiniTopic(BaseModel):
    """A sub-topic detected within a physical layer."""

    topic_id: str = Field(..., description="Unique topic identifier")
    label: str = Field(..., min_length=1, description="Human-readable topic label")
    token_span: tuple[int, int] = Field(
        ...,
        description="Global token ID range (start, end) inclusive",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in topic detection",
    )

    @field_validator("token_span")
    @classmethod
    def validate_token_span(cls, v: tuple[int, int]) -> tuple[int, int]:
        start, end = v
        if end < start:
            raise ValueError(f"token_span end ({end}) must be >= start ({start})")
        return v


class PredicateFrame(BaseModel):
    """A semantic predicate frame extracted via SRL.

    Represents: predicate(agent, patient, instrument, location, time)
    """

    predicate: str = Field(
        ...,
        min_length=1,
        description="Predicate lemma (e.g., 'cause', 'affect')",
    )
    agent: Optional[str] = Field(default=None, description="Agent/subject text")
    patient: Optional[str] = Field(default=None, description="Patient/object text")
    instrument: Optional[str] = Field(default=None, description="Instrument text")
    location: Optional[str] = Field(default=None, description="Location text")
    time: Optional[str] = Field(default=None, description="Time expression text")
    source_tokens: list[str] = Field(
        default_factory=list,
        description="Global token IDs involved in this frame",
    )
    source_layer: str = Field(
        ...,
        description="Component ID of the source physical layer",
    )

    @field_validator("predicate")
    @classmethod
    def validate_predicate(cls, v: str) -> str:
        if not _PREDICATE_FRAME_PATTERN.match(v):
            raise ValueError(
                f"Predicate must be lowercase with underscores, got: {v!r}"
            )
        return v

    @property
    def argument_count(self) -> int:
        """Count of non-None semantic arguments."""
        return sum(
            1 for arg in [self.agent, self.patient, self.instrument, self.location, self.time]
            if arg is not None
        )


class Entity(BaseModel):
    """A named entity extracted within a layer scope.

    Entity IDs follow the pattern E_{TYPE}_{N} (e.g., E_PERSON_0, E_ORG_1).
    """

    id: str = Field(
        ...,
        description="Unique entity ID (E_{TYPE}_{N})",
    )
    label: EntityType = Field(..., description="Entity type")
    mentions: list[str] = Field(
        ...,
        min_length=1,
        description="List of global token IDs that mention this entity",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Extra attributes (e.g., salience, frequency)",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in entity extraction",
    )
    source_component: str = Field(
        ...,
        description="Component ID where this entity was extracted",
    )

    @field_validator("id")
    @classmethod
    def validate_entity_id(cls, v: str) -> str:
        if not _ENTITY_ID_PATTERN.match(v):
            raise ValueError(
                f"Entity ID must match E_{{TYPE}}_{{N}} pattern, got: {v!r}"
            )
        return v

    @property
    def mention_count(self) -> int:
        return len(self.mentions)


class AlternativeHypothesis(BaseModel):
    """An alternative interpretation of a relationship."""

    relation_type: RelationType = Field(..., description="Alternative relation type")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this alternative",
    )
    evidence: str = Field(default="", description="Textual evidence for this hypothesis")


class Relationship(BaseModel):
    """A typed relationship between two entities.

    Relationship IDs follow the pattern R_{N} (e.g., R_0, R_1).
    """

    id: str = Field(
        ...,
        description="Unique relationship ID (R_{N})",
    )
    source_entity_id: str = Field(
        ...,
        description="Source entity ID",
    )
    target_entity_id: str = Field(
        ...,
        description="Target entity ID",
    )
    relation_type: RelationType = Field(
        ...,
        description="Canonical relation type",
    )
    predicate_text: str = Field(
        default="",
        description="Natural language description of the relation",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this relationship",
    )
    evidence_tokens: list[str] = Field(
        default_factory=list,
        description="Global token IDs supporting this relationship",
    )
    alternative_hypotheses: list[AlternativeHypothesis] = Field(
        default_factory=list,
        description="Alternative interpretations of this relation",
    )
    tier: ExtractionTier = Field(
        default=ExtractionTier.PYTHON_NLP,
        description="Processing tier that extracted this relationship",
    )

    @field_validator("id")
    @classmethod
    def validate_relation_id(cls, v: str) -> str:
        if not _RELATION_ID_PATTERN.match(v):
            raise ValueError(
                f"Relationship ID must match R_{{N}} pattern, got: {v!r}"
            )
        return v

    @field_validator("target_entity_id")
    @classmethod
    def validate_no_self_loop(cls, v: str, info) -> str:
        if "source_entity_id" in info.data and v == info.data["source_entity_id"]:
            raise ValueError("Relationship cannot have same source and target entity")
        return v


class MiniPG(BaseModel):
    """Mini Property Graph for a single physical layer.

    This is the core output of Stage 3 per-layer analysis.
    """

    layer_id: str = Field(..., description="Unique identifier for this layer")
    parent_layer_id: Optional[str] = Field(
        default=None,
        description="Parent layer ID (for nested structures)",
    )
    topic_label: str = Field(
        ...,
        min_length=1,
        description="Primary topic label for this layer",
    )
    mini_topics: list[MiniTopic] = Field(
        default_factory=list,
        description="Sub-topics within this layer",
    )
    entities: dict[str, Entity] = Field(
        default_factory=dict,
        description="Map of entity_id -> Entity",
    )
    predicates: list[PredicateFrame] = Field(
        default_factory=list,
        description="Extracted predicate frames",
    )
    relationships: dict[str, Relationship] = Field(
        default_factory=dict,
        description="Map of relationship_id -> Relationship",
    )
    child_pg_ids: list[str] = Field(
        default_factory=list,
        description="IDs of child MiniPGs (for nested layers)",
    )

    @model_validator(mode="after")
    def validate_entity_ids_unique(self) -> "MiniPG":
        """Ensure all entity IDs are unique (dict keys already enforce this)."""
        return self

    @model_validator(mode="after")
    def validate_relationship_refs(self) -> "MiniPG":
        """Ensure all relationship source/target refs exist in entities."""
        for rel_id, rel in self.relationships.items():
            if rel.source_entity_id not in self.entities:
                raise ValueError(
                    f"Relationship {rel_id} references non-existent "
                    f"source entity {rel.source_entity_id}"
                )
            if rel.target_entity_id not in self.entities:
                raise ValueError(
                    f"Relationship {rel_id} references non-existent "
                    f"target entity {rel.target_entity_id}"
                )
        return self

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    @property
    def predicate_count(self) -> int:
        return len(self.predicates)


class SemanticTreeNode(BaseModel):
    """A node in the semantic hierarchy tree.

    Links MiniPGs into a document-level semantic tree.
    """

    node_id: str = Field(..., description="Unique node identifier")
    level: SemanticLevel = Field(..., description="Hierarchical level")
    children: list[str] = Field(
        default_factory=list,
        description="Child node IDs",
    )
    data_ref: Optional[str] = Field(
        default=None,
        description="Reference to associated MiniPG layer_id",
    )


class SemanticConfig(BaseModel):
    """Configuration for the Stage 3 semantic analysis."""

    topic_extractor: str = Field(
        default="heading",
        description="Topic extraction method: 'heading' or 'keybert'",
    )
    predicate_extractor: str = Field(
        default="stanza_srl",
        description="Predicate extraction engine",
    )
    entity_extractor: str = Field(
        default="spacy_ner",
        description="Entity extraction engine: 'spacy_ner' or 'gliner'",
    )
    relationship_extractor: str = Field(
        default="llm",
        description="Relationship extraction engine: 'llm' or 'pattern'",
    )
    entity_resolver: str = Field(
        default="stanza_coref",
        description="Entity resolution engine",
    )
    segmentation_threshold_words: int = Field(
        default=150,
        ge=50,
        description="Word count threshold for semantic paragraph splitting",
    )


class Stage3Input(BaseModel):
    """Input schema for the semantic topology stage.

    Requires Stage 2 output plus Stage 1 token metadata for token mapping.
    """

    source_text: str = Field(..., description="Original source text")
    component_id: str = Field(..., description="Physical component to analyze")
    component_content: str = Field(..., description="Raw content of the component")
    token_ids: list[str] = Field(
        default_factory=list,
        description="Global token IDs belonging to this component",
    )
    config: SemanticConfig = Field(default_factory=SemanticConfig)


class Stage3Output(BaseModel):
    """Output schema for the semantic topology stage."""

    mini_pgs: dict[str, MiniPG] = Field(
        default_factory=dict,
        description="Map of layer_id -> MiniPG",
    )
    semantic_tree: dict[str, SemanticTreeNode] = Field(
        default_factory=dict,
        description="Semantic hierarchy nodes",
    )
    total_entities: int = Field(
        default=0,
        ge=0,
        description="Total entities extracted across all MiniPGs",
    )
    total_relationships: int = Field(
        default=0,
        ge=0,
        description="Total relationships extracted across all MiniPGs",
    )

    @model_validator(mode="after")
    def compute_totals(self) -> "Stage3Output":
        """Compute total_entities and total_relationships from mini_pgs."""
        self.total_entities = sum(pg.entity_count for pg in self.mini_pgs.values())
        self.total_relationships = sum(pg.relationship_count for pg in self.mini_pgs.values())
        return self

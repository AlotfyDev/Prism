"""Global PG and configuration schema models for Stage 4 and pipeline."""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from prism.schemas.enums import (
    ConflictResolution,
    ConfidenceScorer,
    EntityMergeStrategy,
    EntityType,
    LLMProvider,
    RelationType,
    TopicClustering,
)
from prism.schemas.semantic import Entity, PredicateFrame, Relationship


_CLUSTER_ID_PATTERN = re.compile(r"^TC_\d+$")


class TopicCluster(BaseModel):
    """A cluster of semantically related paragraphs across different layers."""

    cluster_id: str = Field(
        ...,
        description="Unique cluster ID (TC_{N})",
    )
    topic_label: str = Field(
        ...,
        min_length=1,
        description="Human-readable topic label for this cluster",
    )
    component_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Physical layer component IDs in this cluster",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Global entity IDs in this cluster",
    )
    centroid_embedding: Optional[list[float]] = Field(
        default=None,
        description="Cluster centroid vector from e5-base embedding",
    )

    @field_validator("cluster_id")
    @classmethod
    def validate_cluster_id(cls, v: str) -> str:
        if not _CLUSTER_ID_PATTERN.match(v):
            raise ValueError(
                f"Cluster ID must match TC_{{N}} pattern, got: {v!r}"
            )
        return v

    @property
    def embedding_dim(self) -> Optional[int]:
        if self.centroid_embedding is None:
            return None
        return len(self.centroid_embedding)


class MergedEntity(Entity):
    """An entity merged across multiple layers (extends Entity with layers field)."""

    layers: list[str] = Field(
        default_factory=list,
        description="All physical layer/component IDs where this entity appears",
    )
    aggregated_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Aggregated confidence from all layers",
    )


class ConfidenceSummary(BaseModel):
    """Aggregate confidence statistics for the GlobalPG."""

    entity_avg: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average entity confidence",
    )
    relationship_avg: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average relationship confidence",
    )
    predicate_avg: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average predicate confidence",
    )
    total_entities: int = Field(default=0, ge=0)
    total_relationships: int = Field(default=0, ge=0)
    total_predicates: int = Field(default=0, ge=0)


class GlobalPG(BaseModel):
    """Global Property Graph — the final output of the Prism pipeline.

    Merged from all MiniPGs with resolved entities, relationships, and topics.
    """

    entities: dict[str, MergedEntity] = Field(
        default_factory=dict,
        description="Global merged entities (cross-layer), keyed by entity ID",
    )
    relationships: list[Relationship] = Field(
        default_factory=list,
        description="All resolved relationships across layers",
    )
    predicates: list[PredicateFrame] = Field(
        default_factory=list,
        description="All predicate frames across layers",
    )
    topic_clusters: list[TopicCluster] = Field(
        default_factory=list,
        description="Cross-layer topic clusters",
    )
    confidence_summary: Optional[ConfidenceSummary] = Field(
        default=None,
        description="Aggregated confidence statistics",
    )
    provenance: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Element ID -> list of source layer IDs",
    )

    @model_validator(mode="after")
    def validate_relationship_entity_refs(self) -> "GlobalPG":
        """Ensure all relationship entity refs exist in global entities."""
        for rel in self.relationships:
            if rel.source_entity_id not in self.entities:
                raise ValueError(
                    f"Relationship {rel.id} references non-existent "
                    f"source entity {rel.source_entity_id}"
                )
            if rel.target_entity_id not in self.entities:
                raise ValueError(
                    f"Relationship {rel.id} references non-existent "
                    f"target entity {rel.target_entity_id}"
                )
        return self

    @model_validator(mode="after")
    def validate_cluster_entity_refs(self) -> "GlobalPG":
        """Ensure all cluster entity refs exist in global entities."""
        for cluster in self.topic_clusters:
            for eid in cluster.entities:
                if eid not in self.entities:
                    raise ValueError(
                        f"Cluster {cluster.cluster_id} references non-existent "
                        f"entity {eid}"
                    )
        return self

    @model_validator(mode="after")
    def validate_provenance_completeness(self) -> "GlobalPG":
        """If provenance is set, it should cover entities and relationships."""
        if not self.provenance:
            return self
        for eid in self.entities:
            if eid not in self.provenance:
                raise ValueError(
                    f"Entity {eid} missing from provenance"
                )
        for rel in self.relationships:
            if rel.id not in self.provenance:
                raise ValueError(
                    f"Relationship {rel.id} missing from provenance"
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

    @property
    def cluster_count(self) -> int:
        return len(self.topic_clusters)


class AggregationConfig(BaseModel):
    """Configuration for Stage 4 aggregation."""

    entity_merge_strategy: EntityMergeStrategy = Field(
        default=EntityMergeStrategy.WEIGHTED,
        description="How to merge same entities across layers",
    )
    conflict_resolution: ConflictResolution = Field(
        default=ConflictResolution.CONFIDENCE_VOTE,
        description="How to resolve contradictory relationships",
    )
    topic_clustering: TopicClustering = Field(
        default=TopicClustering.EMBEDDING,
        description="Method for clustering related paragraphs",
    )
    confidence_scorer: ConfidenceScorer = Field(
        default=ConfidenceScorer.STATISTICAL,
        description="Method for computing confidence scores",
    )
    min_confidence_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Filter out elements below this confidence",
    )
    embedding_model: str = Field(
        default="multilingual-e5-base",
        description="Embedding model name for clustering/similarity",
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENCODE,
        description="Primary LLM provider for fallback operations",
    )


class Stage4Input(BaseModel):
    """Input schema for the aggregation stage.

    Requires Stage 3 output from all layers plus Stage 1 token metadata.
    """

    mini_pgs: dict[str, str] = Field(
        default_factory=dict,
        description="Map of layer_id -> serialized MiniPG content",
    )
    source_text: str = Field(default="", description="Original source text")
    token_ids: list[str] = Field(
        default_factory=list,
        description="All global token IDs from Stage 1",
    )
    config: AggregationConfig = Field(default_factory=AggregationConfig)


class Stage4Output(BaseModel):
    """Output schema for the aggregation stage."""

    global_pg: GlobalPG = Field(
        default_factory=GlobalPG,
        description="The final merged Global Property Graph",
    )


class PipelineConfig(BaseModel):
    """Top-level pipeline configuration combining all stage configs.

    This is the master config loaded from YAML/JSON/TOML.
    """

    # Stage 1
    tokenizer: str = Field(
        default="spacy",
        description="Tokenization engine",
    )
    tokenizer_include_whitespace: bool = Field(
        default=False,
        description="Include whitespace tokens",
    )
    language: str = Field(
        default="en",
        description="Document language (ISO 639-1)",
    )

    # Stage 2
    nesting_depth_limit: int = Field(
        default=10,
        ge=1,
        description="Maximum physical layer nesting depth",
    )

    # Stage 3
    topic_extractor: str = Field(
        default="heading",
        description="Topic extraction method",
    )
    predicate_extractor: str = Field(
        default="stanza_srl",
        description="Predicate extraction engine",
    )
    entity_extractor: str = Field(
        default="spacy_ner",
        description="Entity extraction engine",
    )
    relationship_extractor: str = Field(
        default="llm",
        description="Relationship extraction engine",
    )
    entity_resolver: str = Field(
        default="stanza_coref",
        description="Entity resolution engine",
    )
    segmentation_threshold_words: int = Field(
        default=150,
        ge=50,
        description="Word count threshold for semantic splitting",
    )

    # Stage 4
    aggregation: AggregationConfig = Field(
        default_factory=AggregationConfig,
        description="Stage 4 aggregation configuration",
    )

    # Global
    embedding_model: str = Field(
        default="multilingual-e5-base",
        description="Primary embedding model",
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENCODE,
        description="Primary LLM provider",
    )
    min_confidence_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Global confidence threshold",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Path for LangGraph SQLite checkpointer",
    )

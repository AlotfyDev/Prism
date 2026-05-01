"""Unit tests for Stage 4 schema models (GlobalPG, Config) and PipelineConfig."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import (
    ConflictResolution,
    ConfidenceScorer,
    EntityMergeStrategy,
    EntityType,
    LLMProvider,
    RelationType,
    TopicClustering,
)
from prism.schemas.global_pg import (
    AggregationConfig,
    ConfidenceSummary,
    GlobalPG,
    MergedEntity,
    PipelineConfig,
    Stage4Input,
    Stage4Output,
    TopicCluster,
)
from prism.schemas.semantic import Entity, PredicateFrame, Relationship


def _make_entity(eid: str = "E_PERSON_0") -> Entity:
    return Entity(
        id=eid,
        label=EntityType.PERSON,
        mentions=["T0"],
        source_component="paragraph:p1",
    )


def _make_merged_entity(eid: str = "E_PERSON_0", layers: list[str] | None = None) -> MergedEntity:
    return MergedEntity(
        id=eid,
        label=EntityType.PERSON,
        mentions=["T0"],
        source_component="paragraph:p1",
        layers=layers or ["paragraph:p1"],
    )


def _make_rel(
    rid: str = "R_0",
    src: str = "E_PERSON_0",
    tgt: str = "E_ORG_0",
) -> Relationship:
    return Relationship(
        id=rid,
        source_entity_id=src,
        target_entity_id=tgt,
        relation_type=RelationType.PART_OF,
    )


class TestTopicCluster:
    def test_valid_minimal(self):
        cluster = TopicCluster(
            cluster_id="TC_0",
            topic_label="Climate impacts",
            component_ids=["paragraph:p1", "table:t1"],
        )
        assert cluster.cluster_id == "TC_0"
        assert len(cluster.component_ids) == 2
        assert cluster.entities == []
        assert cluster.centroid_embedding is None

    def test_valid_with_entities(self):
        cluster = TopicCluster(
            cluster_id="TC_1",
            topic_label="Economy",
            component_ids=["list:l1"],
            entities=["E_ORG_0", "E_CONCEPT_1"],
        )
        assert len(cluster.entities) == 2

    def test_valid_with_embedding(self):
        embedding = [0.1] * 768
        cluster = TopicCluster(
            cluster_id="TC_0",
            topic_label="Test",
            component_ids=["paragraph:p1"],
            centroid_embedding=embedding,
        )
        assert cluster.embedding_dim == 768

    def test_invalid_cluster_id_bad_pattern(self):
        with pytest.raises(ValidationError, match="TC_"):
            TopicCluster(
                cluster_id="cluster_0",
                topic_label="X",
                component_ids=["p1"],
            )

    def test_invalid_empty_component_ids(self):
        with pytest.raises(ValidationError, match="at least 1 item"):
            TopicCluster(
                cluster_id="TC_0",
                topic_label="X",
                component_ids=[],
            )

    def test_invalid_empty_topic_label(self):
        with pytest.raises(ValidationError):
            TopicCluster(
                cluster_id="TC_0",
                topic_label="",
                component_ids=["p1"],
            )

    def test_embedding_dim_returns_none_when_unset(self):
        cluster = TopicCluster(
            cluster_id="TC_0",
            topic_label="X",
            component_ids=["p1"],
        )
        assert cluster.embedding_dim is None


class TestMergedEntity:
    def test_valid_minimal(self):
        entity = MergedEntity(
            id="E_PERSON_0",
            label=EntityType.PERSON,
            mentions=["T0"],
            source_component="paragraph:p1",
        )
        assert entity.layers == []
        assert entity.aggregated_confidence == 1.0

    def test_valid_with_layers(self):
        entity = MergedEntity(
            id="E_ORG_0",
            label=EntityType.ORGANIZATION,
            mentions=["T5", "T20"],
            source_component="table:t1",
            layers=["paragraph:p1", "table:t1", "list:l1"],
            aggregated_confidence=0.92,
        )
        assert len(entity.layers) == 3
        assert entity.aggregated_confidence == 0.92

    def test_valid_inherits_entity_id_validation(self):
        with pytest.raises(ValidationError, match="E_"):
            MergedEntity(
                id="bad_id",
                label=EntityType.PERSON,
                mentions=["T0"],
                source_component="paragraph:p1",
            )

    def test_valid_inherits_entity_mentions_validation(self):
        with pytest.raises(ValidationError, match="at least 1 item"):
            MergedEntity(
                id="E_PERSON_0",
                label=EntityType.PERSON,
                mentions=[],
                source_component="paragraph:p1",
            )


class TestConfidenceSummary:
    def test_defaults(self):
        summary = ConfidenceSummary()
        assert summary.entity_avg == 0.0
        assert summary.relationship_avg == 0.0
        assert summary.predicate_avg == 0.0
        assert summary.total_entities == 0
        assert summary.total_relationships == 0
        assert summary.total_predicates == 0

    def test_valid_full(self):
        summary = ConfidenceSummary(
            entity_avg=0.85,
            relationship_avg=0.72,
            predicate_avg=0.91,
            total_entities=10,
            total_relationships=15,
            total_predicates=8,
        )
        assert summary.entity_avg == 0.85
        assert summary.total_entities == 10

    def test_invalid_avg_above_one(self):
        with pytest.raises(ValidationError):
            ConfidenceSummary(entity_avg=1.5)

    def test_invalid_negative_total(self):
        with pytest.raises(ValidationError):
            ConfidenceSummary(total_entities=-1)


class TestGlobalPG:
    def test_empty_output(self):
        pg = GlobalPG()
        assert pg.entity_count == 0
        assert pg.relationship_count == 0
        assert pg.predicate_count == 0
        assert pg.cluster_count == 0
        assert pg.provenance == {}
        assert pg.confidence_summary is None

    def test_with_entities_and_relationships(self):
        entities = {
            "E_PERSON_0": _make_merged_entity("E_PERSON_0", ["paragraph:p1"]),
            "E_ORG_0": _make_merged_entity("E_ORG_0", ["table:t1"]),
        }
        rels = [_make_rel("R_0", "E_PERSON_0", "E_ORG_0")]
        pg = GlobalPG(
            entities=entities,
            relationships=rels,
        )
        assert pg.entity_count == 2
        assert pg.relationship_count == 1

    def test_with_predicates(self):
        predicates = [
            PredicateFrame(predicate="cause", source_layer="paragraph:p1"),
        ]
        pg = GlobalPG(predicates=predicates)
        assert pg.predicate_count == 1

    def test_with_topic_clusters(self):
        clusters = [
            TopicCluster(
                cluster_id="TC_0",
                topic_label="Test",
                component_ids=["paragraph:p1"],
            ),
        ]
        pg = GlobalPG(topic_clusters=clusters)
        assert pg.cluster_count == 1

    def test_with_provenance(self):
        entities = {
            "E_PERSON_0": _make_merged_entity("E_PERSON_0"),
        }
        pg = GlobalPG(
            entities=entities,
            provenance={"E_PERSON_0": ["paragraph:p1"]},
        )
        assert "E_PERSON_0" in pg.provenance

    def test_invalid_relationship_refs_nonexistent_entity(self):
        entities = {"E_PERSON_0": _make_merged_entity("E_PERSON_0")}
        rels = [_make_rel("R_0", "E_PERSON_0", "E_MISSING_99")]
        with pytest.raises(ValidationError, match="non-existent"):
            GlobalPG(entities=entities, relationships=rels)

    def test_invalid_cluster_refs_nonexistent_entity(self):
        entities = {"E_PERSON_0": _make_merged_entity("E_PERSON_0")}
        clusters = [
            TopicCluster(
                cluster_id="TC_0",
                topic_label="Test",
                component_ids=["p1"],
                entities=["E_MISSING_99"],
            ),
        ]
        with pytest.raises(ValidationError, match="non-existent"):
            GlobalPG(entities=entities, topic_clusters=clusters)

    def test_invalid_provenance_missing_entity(self):
        entities = {
            "E_PERSON_0": _make_merged_entity("E_PERSON_0"),
            "E_ORG_0": _make_merged_entity("E_ORG_0"),
        }
        with pytest.raises(ValidationError, match="missing from provenance"):
            GlobalPG(
                entities=entities,
                provenance={"E_PERSON_0": ["p1"]},
            )

    def test_invalid_provenance_missing_relationship(self):
        entities = {
            "E_PERSON_0": _make_merged_entity("E_PERSON_0"),
            "E_ORG_0": _make_merged_entity("E_ORG_0"),
        }
        rels = [_make_rel("R_0", "E_PERSON_0", "E_ORG_0")]
        with pytest.raises(ValidationError, match="missing from provenance"):
            GlobalPG(
                entities=entities,
                relationships=rels,
                provenance={
                    "E_PERSON_0": ["p1"],
                    "E_ORG_0": ["p1"],
                },
            )

    def test_full_global_pg(self):
        entities = {
            "E_PERSON_0": _make_merged_entity("E_PERSON_0", ["paragraph:p1"]),
            "E_ORG_0": _make_merged_entity("E_ORG_0", ["table:t1"]),
            "E_LOC_0": MergedEntity(
                id="E_LOC_0",
                label=EntityType.LOCATION,
                mentions=["T30"],
                source_component="paragraph:p2",
                layers=["paragraph:p2"],
            ),
        }
        rels = [
            _make_rel("R_0", "E_PERSON_0", "E_ORG_0"),
            _make_rel("R_1", "E_ORG_0", "E_LOC_0"),
        ]
        predicates = [
            PredicateFrame(predicate="work_for", source_layer="paragraph:p1"),
        ]
        clusters = [
            TopicCluster(
                cluster_id="TC_0",
                topic_label="Organizations",
                component_ids=["paragraph:p1", "table:t1"],
                entities=["E_PERSON_0", "E_ORG_0"],
            ),
        ]
        summary = ConfidenceSummary(
            entity_avg=0.9,
            relationship_avg=0.8,
            predicate_avg=0.95,
            total_entities=3,
            total_relationships=2,
            total_predicates=1,
        )
        provenance = {
            "E_PERSON_0": ["paragraph:p1"],
            "E_ORG_0": ["table:t1"],
            "E_LOC_0": ["paragraph:p2"],
            "R_0": ["paragraph:p1"],
            "R_1": ["table:t1"],
        }
        pg = GlobalPG(
            entities=entities,
            relationships=rels,
            predicates=predicates,
            topic_clusters=clusters,
            confidence_summary=summary,
            provenance=provenance,
        )
        assert pg.entity_count == 3
        assert pg.relationship_count == 2
        assert pg.predicate_count == 1
        assert pg.cluster_count == 1
        assert pg.confidence_summary.entity_avg == 0.9
        assert len(pg.provenance) == 5


class TestAggregationConfig:
    def test_defaults(self):
        config = AggregationConfig()
        assert config.entity_merge_strategy == EntityMergeStrategy.WEIGHTED
        assert config.conflict_resolution == ConflictResolution.CONFIDENCE_VOTE
        assert config.topic_clustering == TopicClustering.EMBEDDING
        assert config.confidence_scorer == ConfidenceScorer.STATISTICAL
        assert config.min_confidence_threshold == 0.0
        assert config.embedding_model == "multilingual-e5-base"
        assert config.llm_provider == LLMProvider.OPENCODE

    def test_custom_values(self):
        config = AggregationConfig(
            entity_merge_strategy=EntityMergeStrategy.UNION,
            conflict_resolution=ConflictResolution.LLM_ADJUDICATE,
            topic_clustering=TopicClustering.LEXICAL,
            min_confidence_threshold=0.5,
            llm_provider=LLMProvider.OPENROUTER,
        )
        assert config.entity_merge_strategy == EntityMergeStrategy.UNION
        assert config.min_confidence_threshold == 0.5

    def test_invalid_threshold_above_one(self):
        with pytest.raises(ValidationError):
            AggregationConfig(min_confidence_threshold=1.5)

    def test_invalid_threshold_negative(self):
        with pytest.raises(ValidationError):
            AggregationConfig(min_confidence_threshold=-0.1)


class TestStage4Input:
    def test_valid_minimal(self):
        inp = Stage4Input()
        assert inp.mini_pgs == {}
        assert inp.source_text == ""
        assert inp.token_ids == []
        assert isinstance(inp.config, AggregationConfig)

    def test_valid_with_data(self):
        inp = Stage4Input(
            mini_pgs={"layer:p1": '{"layer_id": "p1"}', "layer:p2": '{"layer_id": "p2"}'},
            source_text="Hello world",
            token_ids=["T0", "T1", "T2"],
            config=AggregationConfig(min_confidence_threshold=0.3),
        )
        assert len(inp.mini_pgs) == 2
        assert len(inp.token_ids) == 3
        assert inp.config.min_confidence_threshold == 0.3


class TestStage4Output:
    def test_empty_output(self):
        output = Stage4Output()
        assert output.global_pg.entity_count == 0
        assert output.global_pg.relationship_count == 0

    def test_with_global_pg(self):
        entities = {
            "E_PERSON_0": _make_merged_entity("E_PERSON_0", ["paragraph:p1"]),
        }
        pg = GlobalPG(entities=entities)
        output = Stage4Output(global_pg=pg)
        assert output.global_pg.entity_count == 1


class TestPipelineConfig:
    def test_defaults(self):
        config = PipelineConfig()
        assert config.tokenizer == "spacy"
        assert config.language == "en"
        assert config.nesting_depth_limit == 10
        assert config.topic_extractor == "heading"
        assert config.predicate_extractor == "stanza_srl"
        assert config.entity_extractor == "spacy_ner"
        assert config.relationship_extractor == "llm"
        assert config.entity_resolver == "stanza_coref"
        assert config.segmentation_threshold_words == 150
        assert config.embedding_model == "multilingual-e5-base"
        assert config.llm_provider == LLMProvider.OPENCODE
        assert config.min_confidence_threshold == 0.0
        assert config.checkpoint_path is None
        assert isinstance(config.aggregation, AggregationConfig)

    def test_custom_stage1(self):
        config = PipelineConfig(
            tokenizer="nltk",
            tokenizer_include_whitespace=True,
            language="ar",
        )
        assert config.tokenizer == "nltk"
        assert config.tokenizer_include_whitespace is True

    def test_custom_stage3(self):
        config = PipelineConfig(
            topic_extractor="keybert",
            entity_extractor="gliner",
            relationship_extractor="pattern",
            segmentation_threshold_words=200,
        )
        assert config.topic_extractor == "keybert"
        assert config.segmentation_threshold_words == 200

    def test_custom_stage4(self):
        config = PipelineConfig(
            aggregation=AggregationConfig(
                entity_merge_strategy=EntityMergeStrategy.UNION,
                conflict_resolution=ConflictResolution.RULE_PRIORITY,
                min_confidence_threshold=0.7,
            ),
            llm_provider=LLMProvider.CLINE,
        )
        assert config.aggregation.entity_merge_strategy == EntityMergeStrategy.UNION
        assert config.llm_provider == LLMProvider.CLINE

    def test_custom_embedding(self):
        config = PipelineConfig(
            embedding_model="multilingual-e5-small",
        )
        assert config.embedding_model == "multilingual-e5-small"

    def test_invalid_nesting_depth(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            PipelineConfig(nesting_depth_limit=0)

    def test_invalid_segmentation_threshold(self):
        with pytest.raises(ValidationError, match="greater than or equal to 50"):
            PipelineConfig(segmentation_threshold_words=10)

    def test_invalid_confidence_threshold(self):
        with pytest.raises(ValidationError):
            PipelineConfig(min_confidence_threshold=-0.5)

    def test_checkpoint_path(self):
        config = PipelineConfig(checkpoint_path="/tmp/prism/checkpoint.db")
        assert config.checkpoint_path == "/tmp/prism/checkpoint.db"

    def test_all_llm_providers(self):
        for provider in LLMProvider:
            config = PipelineConfig(llm_provider=provider)
            assert config.llm_provider == provider

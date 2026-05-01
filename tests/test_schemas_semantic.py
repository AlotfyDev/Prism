"""Unit tests for Stage 3 schema models (Semantic / MiniPG)."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import EntityType, ExtractionTier, RelationType, SemanticLevel
from prism.schemas.semantic import (
    AlternativeHypothesis,
    Entity,
    MiniPG,
    MiniTopic,
    PredicateFrame,
    Relationship,
    SemanticConfig,
    SemanticTreeNode,
    Stage3Input,
    Stage3Output,
)


class TestMiniTopic:
    def test_valid_minimal(self):
        topic = MiniTopic(
            topic_id="t0",
            label="Climate change",
            token_span=(0, 5),
        )
        assert topic.topic_id == "t0"
        assert topic.label == "Climate change"
        assert topic.token_span == (0, 5)
        assert topic.confidence == 1.0

    def test_valid_custom_confidence(self):
        topic = MiniTopic(
            topic_id="t1",
            label="Economy",
            token_span=(10, 20),
            confidence=0.85,
        )
        assert topic.confidence == 0.85

    def test_invalid_span_reversed(self):
        with pytest.raises(ValidationError, match="end"):
            MiniTopic(topic_id="t0", label="X", token_span=(10, 5))

    def test_invalid_confidence_above_one(self):
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            MiniTopic(topic_id="t0", label="X", token_span=(0, 1), confidence=1.5)

    def test_invalid_confidence_negative(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            MiniTopic(topic_id="t0", label="X", token_span=(0, 1), confidence=-0.1)

    def test_invalid_empty_label(self):
        with pytest.raises(ValidationError):
            MiniTopic(topic_id="t0", label="", token_span=(0, 1))


class TestPredicateFrame:
    def test_valid_minimal(self):
        frame = PredicateFrame(
            predicate="cause",
            source_layer="paragraph:p1",
        )
        assert frame.predicate == "cause"
        assert frame.argument_count == 0
        assert frame.source_tokens == []

    def test_valid_full_arguments(self):
        frame = PredicateFrame(
            predicate="affect",
            agent="temperature",
            patient="agriculture",
            instrument="drought",
            location="tropical regions",
            time="recent years",
            source_tokens=["T10", "T11", "T12"],
            source_layer="paragraph:p2",
        )
        assert frame.argument_count == 5

    def test_valid_partial_arguments(self):
        frame = PredicateFrame(
            predicate="rise",
            agent="emissions",
            source_layer="paragraph:p1",
        )
        assert frame.argument_count == 1

    def test_invalid_predicate_uppercase(self):
        with pytest.raises(ValidationError, match="lowercase"):
            PredicateFrame(predicate="Cause", source_layer="paragraph:p1")

    def test_invalid_predicate_with_spaces(self):
        with pytest.raises(ValidationError, match="lowercase"):
            PredicateFrame(predicate="climate change", source_layer="paragraph:p1")

    def test_valid_predicate_with_underscores(self):
        frame = PredicateFrame(
            predicate="cause_effect",
            source_layer="paragraph:p1",
        )
        assert frame.predicate == "cause_effect"


class TestEntity:
    def test_valid_minimal(self):
        entity = Entity(
            id="E_PERSON_0",
            label=EntityType.PERSON,
            mentions=["T5"],
            source_component="paragraph:p1",
        )
        assert entity.id == "E_PERSON_0"
        assert entity.label == EntityType.PERSON
        assert entity.mention_count == 1
        assert entity.confidence == 1.0

    def test_valid_multiple_mentions(self):
        entity = Entity(
            id="E_ORG_1",
            label=EntityType.ORGANIZATION,
            mentions=["T10", "T25", "T40"],
            source_component="table:t1",
            confidence=0.95,
        )
        assert entity.mention_count == 3

    def test_valid_with_attributes(self):
        entity = Entity(
            id="E_LOC_0",
            label=EntityType.LOCATION,
            mentions=["T3"],
            source_component="paragraph:p1",
            attributes={"salience": "high", "frequency": "5"},
        )
        assert entity.attributes["salience"] == "high"

    def test_invalid_id_bad_pattern_no_e_prefix(self):
        with pytest.raises(ValidationError, match="E_"):
            Entity(
                id="PERSON_0",
                label=EntityType.PERSON,
                mentions=["T0"],
                source_component="paragraph:p1",
            )

    def test_invalid_id_bad_pattern_no_number(self):
        with pytest.raises(ValidationError, match="E_"):
            Entity(
                id="E_PERSON",
                label=EntityType.PERSON,
                mentions=["T0"],
                source_component="paragraph:p1",
            )

    def test_invalid_id_lowercase_type(self):
        with pytest.raises(ValidationError, match="E_"):
            Entity(
                id="E_person_0",
                label=EntityType.PERSON,
                mentions=["T0"],
                source_component="paragraph:p1",
            )

    def test_invalid_empty_mentions(self):
        with pytest.raises(ValidationError, match="at least 1 item"):
            Entity(
                id="E_PERSON_0",
                label=EntityType.PERSON,
                mentions=[],
                source_component="paragraph:p1",
            )

    def test_all_entity_types(self):
        for et in EntityType:
            entity = Entity(
                id=f"E_{et.value}_0",
                label=et,
                mentions=["T0"],
                source_component="paragraph:p1",
            )
            assert entity.label == et


class TestAlternativeHypothesis:
    def test_valid_minimal(self):
        alt = AlternativeHypothesis(relation_type=RelationType.CAUSES)
        assert alt.relation_type == RelationType.CAUSES
        assert alt.confidence == 0.0
        assert alt.evidence == ""

    def test_valid_full(self):
        alt = AlternativeHypothesis(
            relation_type=RelationType.DEPENDS_ON,
            confidence=0.6,
            evidence="contextual hint in paragraph",
        )
        assert alt.confidence == 0.6


class TestRelationship:
    def test_valid_minimal(self):
        rel = Relationship(
            id="R_0",
            source_entity_id="E_PERSON_0",
            target_entity_id="E_ORG_1",
            relation_type=RelationType.PART_OF,
        )
        assert rel.id == "R_0"
        assert rel.relation_type == RelationType.PART_OF
        assert rel.confidence == 1.0
        assert rel.tier == ExtractionTier.PYTHON_NLP
        assert rel.alternative_hypotheses == []

    def test_valid_with_evidence(self):
        rel = Relationship(
            id="R_1",
            source_entity_id="E_LOC_0",
            target_entity_id="E_LOC_1",
            relation_type=RelationType.LOCATED_IN,
            predicate_text="is located within",
            confidence=0.9,
            evidence_tokens=["T15", "T16", "T17"],
            tier=ExtractionTier.LLM,
        )
        assert rel.predicate_text == "is located within"
        assert rel.tier == ExtractionTier.LLM

    def test_valid_with_alternatives(self):
        rel = Relationship(
            id="R_2",
            source_entity_id="E_CONCEPT_0",
            target_entity_id="E_CONCEPT_1",
            relation_type=RelationType.CAUSES,
            alternative_hypotheses=[
                AlternativeHypothesis(
                    relation_type=RelationType.DEPENDS_ON,
                    confidence=0.4,
                ),
            ],
        )
        assert len(rel.alternative_hypotheses) == 1

    def test_invalid_id_bad_pattern(self):
        with pytest.raises(ValidationError, match="R_"):
            Relationship(
                id="relation_0",
                source_entity_id="E_A_0",
                target_entity_id="E_B_0",
                relation_type=RelationType.OTHER,
            )

    def test_invalid_self_loop(self):
        with pytest.raises(ValidationError, match="same source and target"):
            Relationship(
                id="R_0",
                source_entity_id="E_PERSON_0",
                target_entity_id="E_PERSON_0",
                relation_type=RelationType.OTHER,
            )

    def test_all_relation_types(self):
        for i, rt in enumerate(RelationType):
            rel = Relationship(
                id=f"R_{i}",
                source_entity_id="E_A_0",
                target_entity_id="E_B_0",
                relation_type=rt,
            )
            assert rel.relation_type == rt

    def test_invalid_confidence_above_one(self):
        with pytest.raises(ValidationError):
            Relationship(
                id="R_0",
                source_entity_id="E_A_0",
                target_entity_id="E_B_0",
                relation_type=RelationType.OTHER,
                confidence=2.0,
            )


class TestMiniPG:
    def _make_entity(self, eid: str = "E_PERSON_0") -> Entity:
        return Entity(
            id=eid,
            label=EntityType.PERSON,
            mentions=["T0"],
            source_component="paragraph:p1",
        )

    def _make_rel(self, rid: str = "R_0", src: str = "E_PERSON_0", tgt: str = "E_ORG_1") -> Relationship:
        return Relationship(
            id=rid,
            source_entity_id=src,
            target_entity_id=tgt,
            relation_type=RelationType.PART_OF,
        )

    def test_valid_empty_minipg(self):
        pg = MiniPG(
            layer_id="layer:paragraph:p1",
            topic_label="Climate",
        )
        assert pg.entity_count == 0
        assert pg.relationship_count == 0
        assert pg.predicate_count == 0
        assert pg.child_pg_ids == []

    def test_valid_with_entities(self):
        entities = {
            "E_PERSON_0": self._make_entity("E_PERSON_0"),
            "E_ORG_1": self._make_entity("E_ORG_1"),
        }
        pg = MiniPG(
            layer_id="layer:p1",
            topic_label="People and orgs",
            entities=entities,
        )
        assert pg.entity_count == 2

    def test_valid_with_relationships(self):
        entities = {
            "E_PERSON_0": self._make_entity("E_PERSON_0"),
            "E_ORG_1": self._make_entity("E_ORG_1"),
        }
        rels = {
            "R_0": self._make_rel("R_0", "E_PERSON_0", "E_ORG_1"),
        }
        pg = MiniPG(
            layer_id="layer:p1",
            topic_label="Relations",
            entities=entities,
            relationships=rels,
        )
        assert pg.relationship_count == 1

    def test_valid_with_predicates(self):
        predicates = [
            PredicateFrame(predicate="cause", source_layer="paragraph:p1"),
            PredicateFrame(predicate="affect", source_layer="paragraph:p1"),
        ]
        pg = MiniPG(
            layer_id="layer:p1",
            topic_label="Actions",
            predicates=predicates,
        )
        assert pg.predicate_count == 2

    def test_valid_nested_layer(self):
        pg = MiniPG(
            layer_id="layer:list:l1_item1",
            topic_label="Nested item",
            parent_layer_id="layer:list:l1",
        )
        assert pg.parent_layer_id == "layer:list:l1"

    def test_invalid_relationship_refs_nonexistent_entity(self):
        entities = {"E_PERSON_0": self._make_entity("E_PERSON_0")}
        rels = {
            "R_0": self._make_rel("R_0", "E_PERSON_0", "E_MISSING_99"),
        }
        with pytest.raises(ValidationError, match="non-existent"):
            MiniPG(
                layer_id="layer:p1",
                topic_label="Bad refs",
                entities=entities,
                relationships=rels,
            )

    def test_invalid_empty_topic_label(self):
        with pytest.raises(ValidationError):
            MiniPG(layer_id="layer:p1", topic_label="")

    def test_full_minipg(self):
        entities = {
            "E_PERSON_0": self._make_entity("E_PERSON_0"),
            "E_ORG_1": self._make_entity("E_ORG_1"),
            "E_LOC_0": Entity(
                id="E_LOC_0",
                label=EntityType.LOCATION,
                mentions=["T20"],
                source_component="paragraph:p1",
            ),
        }
        rels = {
            "R_0": self._make_rel("R_0", "E_PERSON_0", "E_ORG_1"),
            "R_1": self._make_rel("R_1", "E_ORG_1", "E_LOC_0"),
        }
        predicates = [
            PredicateFrame(predicate="work_for", agent="Alice", patient="Acme", source_layer="paragraph:p1"),
        ]
        topics = [
            MiniTopic(topic_id="t0", label="Employment", token_span=(0, 10)),
        ]
        pg = MiniPG(
            layer_id="layer:full",
            parent_layer_id="layer:doc",
            topic_label="Full layer",
            mini_topics=topics,
            entities=entities,
            predicates=predicates,
            relationships=rels,
            child_pg_ids=[],
        )
        assert pg.entity_count == 3
        assert pg.relationship_count == 2
        assert pg.predicate_count == 1
        assert len(pg.mini_topics) == 1


class TestSemanticTreeNode:
    def test_valid_minimal(self):
        node = SemanticTreeNode(
            node_id="n0",
            level=SemanticLevel.DOCUMENT,
        )
        assert node.node_id == "n0"
        assert node.level == SemanticLevel.DOCUMENT
        assert node.children == []
        assert node.data_ref is None

    def test_valid_with_children(self):
        node = SemanticTreeNode(
            node_id="root",
            level=SemanticLevel.DOCUMENT,
            children=["n1", "n2", "n3"],
            data_ref="layer:doc",
        )
        assert len(node.children) == 3

    def test_all_levels(self):
        for level in SemanticLevel:
            node = SemanticTreeNode(node_id=f"n_{level.value}", level=level)
            assert node.level == level


class TestSemanticConfig:
    def test_defaults(self):
        config = SemanticConfig()
        assert config.topic_extractor == "heading"
        assert config.predicate_extractor == "stanza_srl"
        assert config.entity_extractor == "spacy_ner"
        assert config.relationship_extractor == "llm"
        assert config.entity_resolver == "stanza_coref"
        assert config.segmentation_threshold_words == 150

    def test_custom_values(self):
        config = SemanticConfig(
            topic_extractor="keybert",
            entity_extractor="gliner",
            relationship_extractor="pattern",
            segmentation_threshold_words=200,
        )
        assert config.topic_extractor == "keybert"
        assert config.segmentation_threshold_words == 200

    def test_invalid_threshold_too_low(self):
        with pytest.raises(ValidationError, match="greater than or equal to 50"):
            SemanticConfig(segmentation_threshold_words=10)


class TestStage3Input:
    def test_valid_minimal(self):
        inp = Stage3Input(
            source_text="Hello world",
            component_id="paragraph:p1",
            component_content="Hello world",
        )
        assert inp.source_text == "Hello world"
        assert inp.config.segmentation_threshold_words == 150

    def test_valid_with_tokens(self):
        inp = Stage3Input(
            source_text="Hello world",
            component_id="table:t1",
            component_content="|A|B|",
            token_ids=["T5", "T6", "T7", "T8"],
        )
        assert len(inp.token_ids) == 4

    def test_missing_source_text(self):
        with pytest.raises(ValidationError):
            Stage3Input(component_id="p1", component_content="text")

    def test_missing_component_id(self):
        with pytest.raises(ValidationError):
            Stage3Input(source_text="text", component_content="text")


class TestStage3Output:
    def test_empty_output(self):
        output = Stage3Output()
        assert output.total_entities == 0
        assert output.total_relationships == 0
        assert output.mini_pgs == {}
        assert output.semantic_tree == {}

    def test_with_single_minipg(self):
        entity = Entity(
            id="E_PERSON_0",
            label=EntityType.PERSON,
            mentions=["T0"],
            source_component="paragraph:p1",
        )
        pg = MiniPG(
            layer_id="layer:p1",
            topic_label="Test",
            entities={"E_PERSON_0": entity},
        )
        output = Stage3Output(mini_pgs={"layer:p1": pg})
        assert output.total_entities == 1
        assert output.total_relationships == 0

    def test_with_multiple_minipgs(self):
        def _make_pg(layer_id: str, n_entities: int) -> MiniPG:
            entities = {}
            for i in range(n_entities):
                eid = f"E_PERSON_{i}"
                entities[eid] = Entity(
                    id=eid,
                    label=EntityType.PERSON,
                    mentions=[f"T{i}"],
                    source_component="paragraph:p1",
                )
            return MiniPG(layer_id=layer_id, topic_label=f"Layer {layer_id}", entities=entities)

        output = Stage3Output(
            mini_pgs={
                "layer:p1": _make_pg("layer:p1", 3),
                "layer:p2": _make_pg("layer:p2", 5),
            }
        )
        assert output.total_entities == 8
        assert output.total_relationships == 0

    def test_with_relationships_totals(self):
        entity = Entity(
            id="E_PERSON_0",
            label=EntityType.PERSON,
            mentions=["T0"],
            source_component="paragraph:p1",
        )
        entity2 = Entity(
            id="E_ORG_0",
            label=EntityType.ORGANIZATION,
            mentions=["T1"],
            source_component="paragraph:p1",
        )
        rel = Relationship(
            id="R_0",
            source_entity_id="E_PERSON_0",
            target_entity_id="E_ORG_0",
            relation_type=RelationType.PART_OF,
        )
        pg = MiniPG(
            layer_id="layer:p1",
            topic_label="Test",
            entities={"E_PERSON_0": entity, "E_ORG_0": entity2},
            relationships={"R_0": rel},
        )
        output = Stage3Output(mini_pgs={"layer:p1": pg})
        assert output.total_entities == 2
        assert output.total_relationships == 1

# 04_SCHEMA_PROTOCOL — Prism Unified Interface Protocol

## Philosophy

> **The pipeline is stable. The implementations are swappable.**
>
> Every Processing Unit — whether spaCy, Stanza, LLM, or rule-based — MUST produce the same output schema from the same input schema. The pipeline does not know or care WHICH unit processed the data. It only validates that the output matches the contract.

---

## Schema Versioning

All schemas are versioned. Breaking changes increment the major version.

```
prism-schema/v1/
├── token.json
├── metadata.json
├── physical_component.json
├── entity.json
├── predicate_frame.json
├── relationship.json
├── mini_pg.json
├── global_pg.json
├── topic_cluster.json
└── validation_report.json
```

---

## Stage 1 Schemas — Holistic Tokenization

### 1.1 Input Schema: `Stage1Input`

```json
{
  "$schema": "prism-schema/v1/stage1_input.json",
  "type": "object",
  "required": ["source", "source_type"],
  "properties": {
    "source": {
      "type": "string",
      "description": "File path or raw content string"
    },
    "source_type": {
      "type": "string",
      "enum": ["pdf", "docx", "pptx", "md", "txt"]
    },
    "config": {
      "type": "object",
      "properties": {
        "tokenizer": { "type": "string", "default": "spacy" },
        "include_whitespace": { "type": "boolean", "default": false },
        "language": { "type": "string", "default": "en" }
      }
    }
  }
}
```

### 1.2 Output Schema: `Stage1Output`

```json
{
  "$schema": "prism-schema/v1/stage1_output.json",
  "type": "object",
  "required": ["tokens", "metadata", "source_text"],
  "properties": {
    "tokens": {
      "type": "object",
      "description": "Global token ID → Token object",
      "additionalProperties": { "$ref": "#/definitions/Token" }
    },
    "metadata": {
      "type": "object",
      "description": "Token ID → Metadata",
      "additionalProperties": { "$ref": "#/definitions/TokenMetadata" }
    },
    "source_text": { "type": "string" }
  },
  "definitions": {
    "Token": {
      "type": "object",
      "required": ["id", "text"],
      "properties": {
        "id": { "type": "string", "pattern": "^T\\d+$", "description": "Global sequential ID: T0, T1, ..." },
        "text": { "type": "string" },
        "lemma": { "type": ["string", "null"], "default": null },
        "pos": { "type": ["string", "null"], "default": null },
        "ner_label": { "type": ["string", "null"], "default": null }
      }
    },
    "TokenMetadata": {
      "type": "object",
      "required": ["token_id", "char_start", "char_end"],
      "properties": {
        "token_id": { "type": "string" },
        "char_start": { "type": "integer", "minimum": 0 },
        "char_end": { "type": "integer", "minimum": 0 },
        "source_line": { "type": ["integer", "null"], "default": null },
        "bounding_box": {
          "type": ["object", "null"],
          "properties": {
            "x0": { "type": "number" },
            "y0": { "type": "number" },
            "x1": { "type": "number" },
            "y1": { "type": "number" }
          },
          "default": null
        }
      }
    }
  }
}
```

**Invariant Rules:**
- Token IDs MUST be sequential with no gaps: `T0, T1, T2, ... TN`
- Every token MUST have metadata with `char_start` and `char_end`
- `char_end` of token `Ti` MUST equal or precede `char_start` of token `Ti+1`
- No two tokens may overlap in character range

---

## Stage 2 Schemas — Physical Topology Analyzer

### 2.1 Input Schema: `Stage2Input`

```json
{
  "$schema": "prism-schema/v1/stage2_input.json",
  "type": "object",
  "required": ["stage1_output", "config"],
  "properties": {
    "stage1_output": { "$ref": "stage1_output.json" },
    "config": {
      "type": "object",
      "properties": {
        "layer_types_to_detect": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["paragraph", "list", "table", "diagram", "heading", "code_block", "footnote", "metadata", "figure", "blockquote"]
          }
        },
        "nesting_depth_limit": { "type": "integer", "default": 3 }
      }
    }
  }
}
```

### 2.2 Output Schema: `Stage2Output`

```json
{
  "$schema": "prism-schema/v1/stage2_output.json",
  "type": "object",
  "required": ["discovered_layers", "layer_types", "is_single_layer", "component_to_tokens"],
  "properties": {
    "discovered_layers": {
      "type": "object",
      "description": "Layer type → list of PhysicalComponents",
      "additionalProperties": {
        "type": "array",
        "items": { "$ref": "#/definitions/PhysicalComponent" }
      }
    },
    "layer_types": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of layer types found in this document"
    },
    "is_single_layer": {
      "type": "boolean",
      "description": "True if only 'paragraph' layer exists"
    },
    "component_to_tokens": {
      "type": "object",
      "description": "Component ID → list of global token IDs",
      "additionalProperties": {
        "type": "array",
        "items": { "type": "string", "pattern": "^T\\d+$" }
      }
    }
  },
  "definitions": {
    "PhysicalComponent": {
      "type": "object",
      "required": ["component_id", "layer_type", "raw_content"],
      "properties": {
        "component_id": { "type": "string", "pattern": "^[a-z]+:[a-z0-9_]+$", "examples": ["para:p3", "tbl:tbl1", "list:l2"] },
        "layer_type": { "type": "string" },
        "raw_content": { "type": "string" },
        "token_span": {
          "type": "array",
          "items": { "type": "string", "pattern": "^T\\d+$" },
          "description": "Global token IDs contained in this component"
        },
        "parent_id": { "type": ["string", "null"], "default": null },
        "children": {
          "type": "array",
          "items": { "type": "string" },
          "default": [],
          "description": "Child component IDs (for nested structures)"
        },
        "attributes": {
          "type": "object",
          "default": {},
          "description": "Layer-specific attributes (e.g., table: {rows: 5, cols: 3, headers: [...]})"
        }
      }
    }
  }
}
```

**Invariant Rules:**
- Every global token from Stage 1 MUST be assigned to at least one physical component
- `component_id` MUST follow the pattern `{layer_type}:{identifier}`
- `parent_id` and `children` MUST form a valid tree (no cycles)
- `token_span` MUST be a non-empty subset of global tokens

---

## Stage 3 Schemas — Semantic Topology Analyzer (per layer)

### 3.1 Input Schema: `Stage3Input`

```json
{
  "$schema": "prism-schema/v1/stage3_input.json",
  "type": "object",
  "required": ["stage2_output", "stage1_output", "config"],
  "properties": {
    "stage2_output": { "$ref": "stage2_output.json" },
    "stage1_output": { "$ref": "stage1_output.json" },
    "config": {
      "type": "object",
      "properties": {
        "topic_detection": { "type": "string", "enum": ["heading", "keybert", "yake", "llm"], "default": "heading" },
        "entity_extractor": { "type": "string", "enum": ["spacy", "gliner", "stanza", "llm"], "default": "spacy" },
        "entity_resolver": { "type": "string", "enum": ["stanza_coref", "neuralcoref", "rule_based", "llm"], "default": "stanza_coref" },
        "predicate_extractor": { "type": "string", "enum": ["stanza_srl", "allennlp_srl", "spacy_heuristic", "llm"], "default": "stanza_srl" },
        "relationship_extractor": { "type": "string", "enum": ["llm", "dep_patterns", "taxonomy", "ml_classifier"], "default": "llm" },
        "language": { "type": "string", "default": "en" },
        "recursion_depth": { "type": "integer", "default": 1 },
        "llm_provider": { "type": "string", "enum": ["opencode", "kilocode", "cline", "openrouter", "codex"], "default": "opencode" }
      }
    }
  }
}
```

### 3.2 Output Schema: `Stage3Output`

```json
{
  "$schema": "prism-schema/v1/stage3_output.json",
  "type": "object",
  "required": ["mini_pgs", "semantic_tree"],
  "properties": {
    "mini_pgs": {
      "type": "object",
      "description": "Physical component ID → MiniPG",
      "additionalProperties": { "$ref": "#/definitions/MiniPG" }
    },
    "semantic_tree": {
      "type": "object",
      "description": "Physical component ID → SemanticTreeNode",
      "additionalProperties": { "$ref": "#/definitions/SemanticTreeNode" }
    }
  },
  "definitions": {
    "MiniTopic": {
      "type": "object",
      "required": ["topic_id", "label", "token_span"],
      "properties": {
        "topic_id": { "type": "string" },
        "label": { "type": "string" },
        "token_span": {
          "type": "array",
          "items": { "type": "string", "pattern": "^T\\d+$" }
        },
        "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0, "default": 1.0 }
      }
    },
    "PredicateFrame": {
      "type": "object",
      "required": ["predicate", "source_tokens", "source_layer"],
      "properties": {
        "predicate": { "type": "string", "description": "Main verb or relation word" },
        "agent": { "type": ["string", "null"], "default": null, "description": "Who/what performs the action" },
        "patient": { "type": ["string", "null"], "default": null, "description": "Who/what receives the action" },
        "instrument": { "type": ["string", "null"], "default": null, "description": "By what means" },
        "location": { "type": ["string", "null"], "default": null, "description": "Where" },
        "time": { "type": ["string", "null"], "default": null, "description": "When" },
        "source_tokens": {
          "type": "array",
          "items": { "type": "string", "pattern": "^T\\d+$" },
          "description": "Global token IDs that formed this predicate"
        },
        "source_layer": { "type": "string", "description": "Physical component ID" }
      }
    },
    "Entity": {
      "type": "object",
      "required": ["id", "label", "mentions", "source_component"],
      "properties": {
        "id": { "type": "string", "pattern": "^E_[A-Z]+_\\d+$", "examples": ["E_PROJECT_001", "E_PERSON_003"] },
        "label": { "type": "string", "description": "Entity type (PROJECT, PERSON, ORG, etc.)" },
        "mentions": {
          "type": "array",
          "items": { "type": "string", "pattern": "^T\\d+$" },
          "minItems": 1,
          "description": "Global token IDs referencing this entity"
        },
        "attributes": {
          "type": "object",
          "default": {},
          "description": "Resolved attributes (name, date, etc.)"
        },
        "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0, "default": 1.0 },
        "source_component": { "type": "string", "description": "Physical component where first detected" }
      }
    },
    "Relationship": {
      "type": "object",
      "required": ["id", "source_entity_id", "target_entity_id", "relation_type"],
      "properties": {
        "id": { "type": "string", "pattern": "^R_\\d+$" },
        "source_entity_id": { "type": "string", "pattern": "^E_[A-Z]+_\\d+$" },
        "target_entity_id": { "type": "string", "pattern": "^E_[A-Z]+_\\d+$" },
        "relation_type": {
          "type": "string",
          "enum": ["CAUSES", "DEPENDS_ON", "PART_OF", "LOCATED_IN", "TEMPORAL", "ARGUMENT_FOR", "ARGUMENT_AGAINST", "CONDITIONAL", "OTHER"],
          "description": "Predefined relation taxonomy"
        },
        "predicate_text": { "type": ["string", "null"], "default": null, "description": "Source predicate text that yielded this relation" },
        "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0, "default": 1.0 },
        "evidence_tokens": {
          "type": "array",
          "items": { "type": "string", "pattern": "^T\\d+$" },
          "default": [],
          "description": "Global token IDs supporting this relationship"
        },
        "alternative_hypotheses": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "relation_type": { "type": "string" },
              "confidence": { "type": "number" },
              "evidence_tokens": { "type": "array", "items": { "type": "string" } }
            }
          },
          "default": [],
          "description": "Conflicting relationships (populated in Stage 4)"
        }
      }
    },
    "MiniPG": {
      "type": "object",
      "required": ["layer_id", "topic_label", "entities", "predicates", "relationships"],
      "properties": {
        "layer_id": { "type": "string", "description": "Physical component ID" },
        "parent_layer_id": { "type": ["string", "null"], "default": null, "description": "If this is a sub-component" },
        "topic_label": { "type": "string" },
        "mini_topics": {
          "type": "array",
          "items": { "$ref": "#/definitions/MiniTopic" },
          "default": []
        },
        "entities": {
          "type": "object",
          "additionalProperties": { "$ref": "#/definitions/Entity" }
        },
        "predicates": {
          "type": "array",
          "items": { "$ref": "#/definitions/PredicateFrame" }
        },
        "relationships": {
          "type": "array",
          "items": { "$ref": "#/definitions/Relationship" }
        },
        "child_pg_ids": {
          "type": "array",
          "items": { "type": "string" },
          "default": [],
          "description": "Sub-component MiniPG IDs"
        }
      }
    },
    "SemanticTreeNode": {
      "type": "object",
      "required": ["node_id", "level"],
      "properties": {
        "node_id": { "type": "string" },
        "level": {
          "type": "string",
          "enum": ["topic", "paragraph", "predicate", "entity"]
        },
        "children": {
          "type": "array",
          "items": { "type": "string" },
          "default": [],
          "description": "Child node IDs"
        },
        "data_ref": { "type": "string", "description": "Reference to data in MiniPG (e.g., 'entities.E_PROJECT_001')" }
      }
    }
  }
}
```

**Invariant Rules:**
- Entity IDs MUST be unique within a MiniPG
- Every entity reference in a Relationship MUST exist in the same MiniPG's entities
- Every `source_tokens` in PredicateFrame MUST be valid global token IDs from Stage 1
- `parent_layer_id` and `child_pg_ids` MUST form a valid tree

---

## Stage 4 Schemas — Aggregation Layer

### 4.1 Input Schema: `Stage4Input`

```json
{
  "$schema": "prism-schema/v1/stage4_input.json",
  "type": "object",
  "required": ["stage3_output", "stage1_output", "config"],
  "properties": {
    "stage3_output": { "$ref": "stage3_output.json" },
    "stage1_output": { "$ref": "stage1_output.json" },
    "config": {
      "type": "object",
      "properties": {
        "entity_merge_strategy": { "type": "string", "enum": ["union", "intersection", "weighted"], "default": "weighted" },
        "conflict_resolution": { "type": "string", "enum": ["confidence_vote", "llm_adjudicate", "rule_priority"], "default": "confidence_vote" },
        "topic_clustering": { "type": "string", "enum": ["embedding", "lexical", "llm"], "default": "embedding" },
        "confidence_scorer": { "type": "string", "enum": ["statistical", "llm"], "default": "statistical" },
        "min_confidence_threshold": { "type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.0 },
        "embedding_model": { "type": "string", "default": "multilingual-e5-base" },
        "llm_provider": { "type": "string", "enum": ["opencode", "kilocode", "cline", "openrouter", "codex"], "default": "opencode" }
      }
    }
  }
}
```

### 4.2 Output Schema: `Stage4Output`

```json
{
  "$schema": "prism-schema/v1/stage4_output.json",
  "type": "object",
  "required": ["global_pg"],
  "properties": {
    "global_pg": { "$ref": "#/definitions/GlobalPG" }
  },
  "definitions": {
    "TopicCluster": {
      "type": "object",
      "required": ["cluster_id", "topic_label", "component_ids"],
      "properties": {
        "cluster_id": { "type": "string", "pattern": "^TC_\\d+$" },
        "topic_label": { "type": "string" },
        "component_ids": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 1,
          "description": "Physical layer component IDs in this cluster"
        },
        "entities": {
          "type": "array",
          "items": { "type": "string", "pattern": "^E_[A-Z]+_\\d+$" },
          "default": [],
          "description": "Global entity IDs in this cluster"
        },
        "centroid_embedding": {
          "type": ["array", "null"],
          "items": { "type": "number" },
          "default": null,
          "description": "Cluster centroid vector (from e5-base)"
        }
      }
    },
    "GlobalPG": {
      "type": "object",
      "required": ["entities", "relationships", "predicates", "topic_clusters", "provenance"],
      "properties": {
        "entities": {
          "type": "object",
          "description": "Global merged entities (cross-layer)",
          "additionalProperties": {
            "allOf": [
              { "$ref": "stage3_output.json#/definitions/Entity" },
              {
                "type": "object",
                "properties": {
                  "layers": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "All physical layer IDs where this entity appears"
                  }
                }
              }
            ]
          }
        },
        "relationships": {
          "type": "array",
          "items": { "$ref": "stage3_output.json#/definitions/Relationship" }
        },
        "predicates": {
          "type": "array",
          "items": { "$ref": "stage3_output.json#/definitions/PredicateFrame" }
        },
        "topic_clusters": {
          "type": "array",
          "items": { "$ref": "#/definitions/TopicCluster" }
        },
        "confidence_summary": {
          "type": "object",
          "properties": {
            "entity_avg": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "relationship_avg": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "predicate_avg": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "total_entities": { "type": "integer" },
            "total_relationships": { "type": "integer" },
            "total_predicates": { "type": "integer" }
          }
        },
        "provenance": {
          "type": "object",
          "description": "Node/edge ID → list of source layer IDs",
          "additionalProperties": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    }
  }
}
```

**Invariant Rules:**
- No duplicate entities in GlobalPG (post cross-layer ER)
- All relationship `source_entity_id` and `target_entity_id` MUST exist in GlobalPG.entities
- All conflicts MUST be resolved (no two relationships with same source+target+conflicting types without one having `alternative_hypotheses`)
- `provenance` MUST cover every entity and relationship
- `confidence_summary` values MUST be consistent with individual entity/relationship confidence scores

---

## Validation Unit Schemas

### V0: Pre-Tokenization Validation

```json
{
  "$schema": "prism-schema/v1/validation_v0.json",
  "name": "pre_tokenization",
  "checks": [
    {
      "id": "V0.1",
      "name": "source_exists",
      "description": "Source file exists and is readable",
      "severity": "critical"
    },
    {
      "id": "V0.2",
      "name": "source_type_supported",
      "description": "Source type is in supported list",
      "severity": "critical"
    },
    {
      "id": "V0.3",
      "name": "source_not_empty",
      "description": "Source content is not empty",
      "severity": "critical"
    }
  ]
}
```

### V1: Token Integrity Validation (after Stage 1)

```json
{
  "$schema": "prism-schema/v1/validation_v1.json",
  "name": "token_integrity",
  "checks": [
    {
      "id": "V1.1",
      "name": "sequential_ids",
      "description": "Token IDs are sequential with no gaps (T0, T1, ... TN)",
      "severity": "critical"
    },
    {
      "id": "V1.2",
      "name": "no_empty_tokens",
      "description": "No token has empty text",
      "severity": "critical"
    },
    {
      "id": "V1.3",
      "name": "metadata_completeness",
      "description": "Every token has metadata with char_start and char_end",
      "severity": "critical"
    },
    {
      "id": "V1.4",
      "name": "no_overlap",
      "description": "No two tokens have overlapping char ranges",
      "severity": "critical"
    },
    {
      "id": "V1.5",
      "name": "full_coverage",
      "description": "All source text characters are covered by token ranges",
      "severity": "warning"
    }
  ]
}
```

### V2: Layer Coverage Validation (after Stage 2)

```json
{
  "$schema": "prism-schema/v1/validation_v2.json",
  "name": "layer_coverage",
  "checks": [
    {
      "id": "V2.1",
      "name": "all_tokens_assigned",
      "description": "Every global token is assigned to at least one physical component",
      "severity": "critical"
    },
    {
      "id": "V2.2",
      "name": "no_empty_components",
      "description": "No physical component has empty token_span",
      "severity": "critical"
    },
    {
      "id": "V2.3",
      "name": "valid_hierarchy",
      "description": "Parent-child relationships form a valid tree (no cycles)",
      "severity": "critical"
    },
    {
      "id": "V2.4",
      "name": "component_id_format",
      "description": "All component IDs match pattern {layer_type}:{identifier}",
      "severity": "critical"
    }
  ]
}
```

### V3: Mini-PG Completeness Validation (after Stage 3)

```json
{
  "$schema": "prism-schema/v1/validation_v3.json",
  "name": "mini_pg_completeness",
  "checks": [
    {
      "id": "V3.1",
      "name": "topic_exists",
      "description": "Each MiniPG has a non-empty topic_label",
      "severity": "critical"
    },
    {
      "id": "V3.2",
      "name": "unique_entity_ids",
      "description": "Entity IDs are unique within each MiniPG",
      "severity": "critical"
    },
    {
      "id": "V3.3",
      "name": "valid_entity_refs",
      "description": "All relationship entity_refs exist in the same MiniPG",
      "severity": "critical"
    },
    {
      "id": "V3.4",
      "name": "valid_token_refs",
      "description": "All token references in entities/predicates/relationships are valid Stage 1 IDs",
      "severity": "critical"
    },
    {
      "id": "V3.5",
      "name": "valid_child_refs",
      "description": "All child_pg_ids reference existing MiniPGs",
      "severity": "warning"
    }
  ]
}
```

### V4: Merge Consistency Validation (after Stage 4)

```json
{
  "$schema": "prism-schema/v1/validation_v4.json",
  "name": "merge_consistency",
  "checks": [
    {
      "id": "V4.1",
      "name": "no_duplicate_entities",
      "description": "No duplicate entities in GlobalPG",
      "severity": "critical"
    },
    {
      "id": "V4.2",
      "name": "all_conflicts_resolved",
      "description": "No unresolved contradictory relationships",
      "severity": "critical"
    },
    {
      "id": "V4.3",
      "name": "provenance_complete",
      "description": "Every entity and relationship has provenance entries",
      "severity": "critical"
    },
    {
      "id": "V4.4",
      "name": "confidence_consistency",
      "description": "confidence_summary values are consistent with individual scores",
      "severity": "critical"
    },
    {
      "id": "V4.5",
      "name": "valid_relationship_refs",
      "description": "All relationship source/target entity IDs exist in GlobalPG.entities",
      "severity": "critical"
    }
  ]
}
```

### Validation Report Schema (output from any ValidationUnit)

```json
{
  "$schema": "prism-schema/v1/validation_report.json",
  "type": "object",
  "required": ["stage", "passed", "checks", "timestamp"],
  "properties": {
    "stage": { "type": "string", "description": "Stage identifier (e.g., 'stage1', 'stage2')" },
    "passed": { "type": "boolean", "description": "True if all critical checks passed" },
    "timestamp": { "type": "string", "format": "date-time" },
    "checks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "passed", "severity"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "passed": { "type": "boolean" },
          "severity": { "type": "string", "enum": ["critical", "warning", "info"] },
          "message": { "type": "string", "default": "" },
          "details": { "type": "object", "default": {} }
        }
      }
    }
  }
}
```

**Rule:** If ANY check with `severity: "critical"` fails → pipeline HALTS. Warning-level failures are logged but do not halt.

---

## Unified Processing Unit Contract

All Processing Units implement this Python interface:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)
ConfigT = TypeVar("ConfigT", bound=BaseModel)

class ProcessingUnit(ABC, Generic[InputT, OutputT, ConfigT]):
    """
    Abstract contract for ALL Prism processing units.
    
    ANY implementation (spaCy, Stanza, LLM, rule-based, ML) MUST satisfy this contract.
    The pipeline does NOT know which implementation is used — it only validates
    that the output matches the schema.
    """

    @abstractmethod
    def process(self, input_data: InputT, config: ConfigT) -> OutputT:
        """Execute the processing step. Returns output matching the unit's output schema."""
        ...

    @abstractmethod
    def validate_input(self, input_data: InputT) -> tuple[bool, str]:
        """
        Verify input meets requirements before processing.
        Returns: (is_valid, error_message)
        """
        ...

    @abstractmethod
    def validate_output(self, output_data: OutputT) -> tuple[bool, str]:
        """
        Verify output matches the expected schema after processing.
        Returns: (is_valid, error_message)
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging and debugging."""
        ...

    @property
    def tier(self) -> str:
        """Implementation tier: 'python_nlp', 'ml', 'llm'."""
        ...
```

**Key invariant:** Regardless of which implementation tier is used, the `OutputT` type is ALWAYS the same. Swapping implementations NEVER changes the data flow.

---

## Relation Type Taxonomy (Canonical)

All RelationshipExtractor units MUST use this fixed set of relation types:

| Type | Meaning | Example |
|------|---------|---------|
| `CAUSES` | A directly causes B | "The bug caused the crash" |
| `DEPENDS_ON` | A requires B to exist/function | "Module A depends on Library B" |
| `PART_OF` | A is a component/subset of B | "Chapter 3 is part of the report" |
| `LOCATED_IN` | A is physically or logically in B | "The server is located in DC-1" |
| `TEMPORAL` | A occurs before/after/during B | "The meeting was before the deadline" |
| `ARGUMENT_FOR` | A provides evidence/support for B | "The data argues for the hypothesis" |
| `ARGUMENT_AGAINST` | A provides evidence against B | "The counterexample argues against the claim" |
| `CONDITIONAL` | A happens only if B is true | "The feature works if the user is admin" |
| `OTHER` | Semantic relation not in taxonomy | Fallback for novel relations |

**Rule:** LLM-based extractors MUST be constrained to this taxonomy via prompt. They cannot invent new types.

---

## LLM Provider Interface

All LLM-based Processing Units use this unified provider interface:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 1000) -> str:
        ...

    @abstractmethod
    def name(self) -> str:
        ...

class OpenCodeProvider(LLMProvider): ...
class KiloCodeProvider(LLMProvider): ...
class ClineProvider(LLMProvider): ...
class OpenRouterProvider(LLMProvider): ...
class CodexProvider(LLMProvider): ...
```

**Provider selection order** (configurable in pipeline config):
1. `opencode` → try first
2. `kilocode` → if opencode fails
3. `cline` → if kilocode fails
4. `openrouter` → if cline fails
5. `codex` → last resort

---

## Schema Stability Guarantee

The following schemas are **frozen for v1** and will NOT change between patch releases:

- `Stage1Output` (Token + Metadata)
- `Stage2Output` (PhysicalComponent + topology)
- `Stage3Output` (MiniPG + SemanticTreeNode)
- `Stage4Output` (GlobalPG + TopicCluster)
- `ValidationReport`
- `Relation Type Taxonomy`

Changes to these schemas require a **major version bump** (`v1 → v2`).

The following may change in **minor versions** (backward-compatible additions):
- Config schemas (new optional fields)
- New Processing Unit implementations (same I/O, different internal logic)
- LLM provider implementations (same interface, different API)

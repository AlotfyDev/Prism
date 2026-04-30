# PLAN — Prism: Architecture & Implementation Plan

## Guiding Principles

| Principle | Meaning |
|-----------|---------|
| **Modularity** | Each stage is an independent unit with defined contracts. No stage knows the internals of another. |
| **Scalability** | Processing units can be parallelized, distributed, or swapped without changing the pipeline topology. |
| **Swappability** | Every processing step is behind an abstract interface. spaCy can be swapped for Stanza, LLM-based ER for rule-based ER — the pipeline topology remains unchanged. |

## Architectural Pattern: Processing Unit Abstraction

Every processing step in the pipeline follows this contract:

```
┌─────────────────────────────────┐
│         Processing Unit         │
│                                 │
│  Input:  T[StageInput]          │
│  Output: T[StageOutput]         │
│  Config: T[StageConfig]         │
│                                 │
│  Process(config, input) → output│
└─────────────────────────────────┘
```

**Rules:**
1. No unit directly accesses files, databases, or external services — all through dependency injection.
2. Every unit is testable in isolation with mock inputs.
3. Every unit declares its dependencies (other stages' output types).
4. Swapping a unit only requires the replacement to satisfy the same Input/Output types.

---

## Stage Decomposition

### Stage 1: Holistic Document Tokenization

#### Processing Units

| Unit | Role | Swappable Implementations |
|------|------|--------------------------|
| `DocumentConverter` | Raw document → Structured Markdown | Docling, Pandoc, custom parser |
| `TokenStreamBuilder` | Markdown → Sequential token stream | Whitespace tokenizer, SentencePiece, spaCy tokenizer, regex-based |
| `MetadataIndexer` | Build positional metadata per token | Char-offset indexer, Line-based indexer, BBox-aware indexer |

#### Input Schema

```python
class Stage1Input:
    source: str                    # File path or raw content
    source_type: str               # "pdf", "docx", "md", "pptx"
    config: TokenizationConfig
```

#### Output Schema

```python
class Stage1Output:
    tokens: dict[str, Token]       # {"T0": Token(...), "T1": Token(...)}
    metadata: TokenMetadataIndex   # Token ID → metadata dict
    source_text: str               # Full text for reference
```

#### Shared Schemas

```python
class Token:
    id: str                        # "T0", "T1", ...
    text: str
    lemma: str                     # Populated later by linguistic units
    pos: str | None                # Populated later
    ner_label: str | None          # Populated later

class TokenMetadata:
    token_id: str
    char_start: int
    char_end: int
    source_line: int | None
    bounding_box: tuple | None

class TokenizationConfig:
    tokenizer: str                 # "whitespace", "spacy", "sentencepiece"
    include_whitespace: bool       # Whether whitespace tokens are included
    language: str                  # "ar", "en", "auto"
```

---

### Stage 2: Physical Topology Analyzer

#### Processing Units

| Unit | Role | Swappable Implementations |
|------|------|--------------------------|
| `MarkdownParser` | Markdown → AST Tree | markdown-it-py, mistune, CommonMark |
| `LayerClassifier` | AST nodes → Physical layer types | Rule-based classifier, ML-based classifier |
| `ComponentMapper` | Components → Global token ID ranges | Char-span mapper, Line-based mapper |
| `TopologyBuilder` | Assemble PhysicalTopologyReport | Tree builder, Flat index builder |

#### Input Schema

```python
class Stage2Input:
    stage1_output: Stage1Output
    config: TopologyConfig
```

#### Output Schema

```python
class Stage2Output:
    discovered_layers: dict[str, list[PhysicalComponent]]
    layer_types: list[str]           # Which types were found
    is_single_layer: bool            # True if only paragraphs exist
    component_to_tokens: dict[str, list[str]]  # Component ID → [T0, T5, ...]
```

#### Shared Schemas

```python
class PhysicalComponent:
    component_id: str                # "para:p3", "tbl:tbl1", "list:l2"
    layer_type: str                  # "paragraph", "table", "list", ...
    raw_content: str                 # Raw markdown content
    token_span: list[str]            # ["T14", "T15", ..., "T89"]
    parent_id: str | None            # Parent component (for nested structures)
    children: list[str]              # Child component IDs
    attributes: dict                 # Layer-specific (e.g., table: {rows, cols, headers})

class TopologyConfig:
    layer_types_to_detect: list[str]  # Which layer types to look for
    nesting_depth_limit: int          # Max recursion depth for nested components
```

---

### Stage 3: Semantic Topology Analyzer

#### Processing Units

| Unit | Role | Swappable Implementations |
|------|------|--------------------------|
| `TopicDetector` | Detect topic for a physical layer | Heading-based, BERTopic, LLM-based, keyword-based |
| `SemanticParagraphSegmenter` | Detect semantic paragraph units | Rule-based (line breaks), semantic similarity clustering, NLP-based |
| `PredicateExtractor` | Extract predicate frames from sentences | spaCy SRL, Stanza SRL, LLM-based, pattern-based |
| `EntityExtractor` | Extract entities within layer scope | spaCy NER, Stanza NER, LLM-based, regex/keyword-based |
| `EntityResolver` | Resolve entity ambiguity within layer | spaCy coref, rule-based alias resolution, LLM-based, embedding similarity |
| `RelationshipExtractor` | Extract relationships between entities | Pattern-based, LLM-based, dependency-tree traversal |
| `MiniPGBuilder` | Assemble Mini-PG from all outputs | NetworkX builder, custom graph builder |

#### Input Schema

```python
class Stage3Input:
    stage2_output: Stage2Output
    stage1_output: Stage1Output      # Access to tokens + text
    config: SemanticConfig
```

#### Output Schema

```python
class Stage3Output:
    mini_pgs: dict[str, MiniPG]      # Physical component ID → MiniPG
    semantic_tree: dict[str, SemanticTreeNode]  # Tree structure per layer
```

#### Shared Schemas

```python
class MiniTopic:
    topic_id: str                    # "tbl1:cell(2,1)", "list2:item3"
    label: str                       # Detected topic label
    token_span: list[str]            # Global token IDs in this mini-topic
    confidence: float

class PredicateFrame:
    predicate: str                   # Main verb/relation
    agent: str | None                # Who performs
    patient: str | None              # Who receives
    instrument: str | None           # By what means
    location: str | None             # Where
    time: str | None                 # When
    source_tokens: list[str]         # Global token IDs
    source_layer: str                # Physical component ID

class Entity:
    id: str                          # "E_PROJECT_001" (local scope)
    label: str                       # Entity type
    mentions: list[str]              # Global token IDs
    attributes: dict
    confidence: float
    source_component: str            # Physical component where first detected

class Relationship:
    id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str               # "CAUSES", "DEPENDS_ON", "PART_OF", ...
    predicate_text: str
    confidence: float
    evidence_tokens: list[str]       # Global token IDs supporting this

class MiniPG:
    layer_id: str                    # Physical component ID
    parent_layer_id: str | None      # If sub-component
    topic_label: str
    mini_topics: list[MiniTopic]
    entities: dict[str, Entity]      # Entity ID → Entity
    predicates: list[PredicateFrame]
    relationships: list[Relationship]
    child_pg_ids: list[str]          # Sub-component MiniPG IDs

class SemanticTreeNode:
    node_id: str
    level: str                       # "topic", "paragraph", "predicate", "entity"
    children: list[str]              # Child node IDs
    data: dict                       # Level-specific data reference

class SemanticConfig:
    topic_detection: str             # "heading", "bertopic", "llm", "keyword"
    entity_extractor: str            # "spacy", "stanza", "llm", "regex"
    entity_resolver: str             # "spacy_coref", "embedding", "llm", "rule_based"
    predicate_extractor: str         # "spacy_srl", "stanza_srl", "llm", "pattern"
    language: str
    recursion_depth: int             # Max depth for sub-component analysis
```

---

### Stage 4: Aggregation Layer

#### Processing Units

| Unit | Role | Swappable Implementations |
|------|------|--------------------------|
| `CrossLayerEntityResolver` | Merge same entity across layers | Embedding similarity, LLM-based, rule-based alias matching |
| `MiniPGMerger` | Merge all MiniPGs into GlobalPG | Union merger, intersection merger, weighted merger |
| `ConflictResolver` | Resolve contradictory relationships | Confidence-weighted voting, LLM adjudication, rule-based priority |
| `CrossLayerLinker` | Build cross-topological links | Causal chain detector, argument structure detector, conditional relation detector |
| `TopicClusterer` | Cluster semantically related paragraphs across layers | Embedding-based clustering, lexical overlap, LLM-based |
| `ConfidenceScorer` | Assign confidence to all graph elements | Statistical model, LLM-based, rule-based |
| `GlobalPGBuilder` | Assemble final Global Property Graph | NetworkX builder, Neo4j builder, JSON builder |

#### Input Schema

```python
class Stage4Input:
    stage3_output: Stage3Output
    stage1_output: Stage1Output      # Access to tokens for evidence tracking
    config: AggregationConfig
```

#### Output Schema

```python
class Stage4Output:
    global_pg: GlobalPG
```

#### Shared Schemas

```python
class TopicCluster:
    cluster_id: str
    topic_label: str
    component_ids: list[str]         # Physical layers in this cluster
    entities: list[str]              # Entity IDs in this cluster
    centroid_embedding: list[float] | None

class GlobalPG:
    entities: dict[str, Entity]      # Merged entities (cross-layer)
    relationships: list[Relationship]  # Conflict-resolved
    predicates: list[PredicateFrame] # All predicates
    topic_clusters: list[TopicCluster]
    confidence_summary: dict         # {entity_avg, relationship_avg, ...}
    provenance: dict                 # {node_id/edge_id: [source_layer_ids]}

class AggregationConfig:
    entity_merge_strategy: str       # "union", "intersection", "weighted"
    conflict_resolution: str         # "confidence_vote", "llm_adjudicate", "rule_priority"
    topic_clustering: str            # "embedding", "lexical", "llm"
    confidence_scorer: str           # "statistical", "llm", "rule_based"
    min_confidence_threshold: float  # Minimum confidence to include in output
```

---

## Processing Unit Interface Contract

All processing units implement this abstract interface:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
ConfigT = TypeVar("ConfigT")

class ProcessingUnit(ABC, Generic[InputT, OutputT, ConfigT]):
    """Abstract contract for all Prism processing units."""

    @abstractmethod
    def process(self, input_data: InputT, config: ConfigT) -> OutputT:
        """Execute the processing step."""
        ...

    @abstractmethod
    def validate_input(self, input_data: InputT) -> bool:
        """Verify input meets requirements before processing."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging and debugging."""
        ...
```

**This means:** Any implementation — whether spaCy, Stanza, LLM, or custom rule-based — MUST satisfy this contract. The pipeline does not care HOW the unit processes data, only that it produces the correct output type from the correct input type.

---

## Pipeline Orchestrator

The orchestrator wires stages together using the contracts:

```python
class PipelineOrchestrator:
    def __init__(self, config: PipelineConfig):
        self.stage1: ProcessingUnit[Stage1Input, Stage1Output, TokenizationConfig]
        self.stage2: ProcessingUnit[Stage2Input, Stage2Output, TopologyConfig]
        self.stage3: ProcessingUnit[Stage3Input, Stage3Output, SemanticConfig]
        self.stage4: ProcessingUnit[Stage4Input, Stage4Output, AggregationConfig]
        # Units are injected at runtime — not hardcoded

    def run(self, source: str, source_type: str) -> Stage4Output:
        # Stage 1
        s1_out = self.stage1.process(Stage1Input(source, source_type, self.config.s1), self.config.s1)
        # Stage 2
        s2_out = self.stage2.process(Stage2Input(s1_out, self.config.s2), self.config.s2)
        # Stage 3
        s3_out = self.stage3.process(Stage3Input(s2_out, s1_out, self.config.s3), self.config.s3)
        # Stage 4
        s4_out = self.stage4.process(Stage4Input(s3_out, s1_out, self.config.s4), self.config.s4)
        return s4_out
```

**Scalability Points:**
- Stage 3 (Semantic Analyzer) can run **in parallel** for each physical layer — each layer is independent.
- Stage 4 units can be **pipelined** — CrossLayerEntityResolver feeds MiniPGMerger feeds ConflictResolver, etc.
- Processing units can be **distributed** — each unit could be a microservice, a local process, or a cloud function.

---

## Dependency Graph

```
Stage1: Tokenization                    ← Must run first (produces token stream)
  │
  ├──→ Stage2: Physical Topology         ← Depends on Stage1 output (tokens)
  │      │
  │      └──→ Stage3: Semantic Analysis  ← Depends on Stage1 + Stage2 output
  │             │
  │             ├── Layer 1: para:p3     ← [PARALLEL]
  │             ├── Layer 2: tbl:tbl1    ← [PARALLEL]
  │             ├── Layer 3: list:l1     ← [PARALLEL]
  │             └── Layer N: ...         ← [PARALLEL]
  │                    │
  │                    └──→ Stage4: Aggregation  ← Depends on all Stage3 outputs
```

---

## Implementation Order (Phased)

| Phase | What | Why First |
|-------|------|-----------|
| **P0: Schema & Contracts** | Define all input/output schemas, ProcessingUnit interface | Everything else depends on these types |
| **P1: Stage 1 (Tokenization)** | DocumentConverter, TokenStreamBuilder, MetadataIndexer | Foundation — all stages need token IDs |
| **P2: Stage 2 (Physical Topology)** | MarkdownParser, LayerClassifier, ComponentMapper | Needed before Semantic Analysis |
| **P3: Stage 3 (Semantic)** | TopicDetector, EntityExtractor, PredicateExtractor, MiniPGBuilder | Core NLP logic |
| **P4: Stage 4 (Aggregation)** | CrossLayerEntityResolver, MiniPGMerger, ConflictResolver, GlobalPGBuilder | Final assembly |
| **P5: Pipeline Orchestrator** | Wire stages together, config management, error handling | Integration |
| **P6: Verification** | End-to-end tests, benchmark documents, performance profiling | Prove it works |

---

## Parallelism Strategy

### Stage 3 Parallelization (Map)

```python
from concurrent.futures import ThreadPoolExecutor

def run_semantic_analysis(layers: list[PhysicalComponent], config: SemanticConfig) -> dict[str, MiniPG]:
    results = {}
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {
            executor.submit(process_single_layer, layer, config): layer.component_id
            for layer in layers
        }
        for future in as_completed(futures):
            component_id = futures[future]
            results[component_id] = future.result()
    return results
```

**This works because:**
- Each physical layer is independent during Stage 3
- No shared mutable state between layer analyses
- MiniPGs are pure data objects — no side effects

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema changes break downstream units | High | Version schemas; units declare required schema version |
| Processing unit produces malformed output | High | `validate_input` + `validate_output` gates between stages |
| Parallel Stage 3 causes resource exhaustion | Medium | Configurable `max_workers`; backpressure mechanism |
| Entity resolution produces false merges | Medium | Confidence thresholds; provenance tracking for audit |
| Conflict resolution loses valid alternatives | Low | Store `alternative_hypotheses` alongside primary |

---

## Verification Checkpoints

| Checkpoint | After Stage | Verification Method |
|------------|-------------|---------------------|
| CP1: Token Integrity | Stage 1 | All source text tokens have global IDs; no gaps; metadata matches char offsets |
| CP2: Layer Coverage | Stage 2 | Every token is assigned to at least one physical component; no orphan tokens |
| CP3: Mini-PG Completeness | Stage 3 | Each MiniPG has: topic, entities, predicates, relationships; entity IDs are unique within layer |
| CP4: Merge Consistency | Stage 4 | No duplicate entities in GlobalPG; all conflicts resolved; provenance complete |
| CP5: End-to-End | Full Pipeline | Run against benchmark document; compare output against expected graph structure |

---

## Resolved Decisions (Post Gap Analysis)

### Tool Stack (English-primary, priority-ordered)

| Priority Tier | Tools | Role |
|---------------|-------|------|
| **1. Python NLP** (default) | spaCy, Stanza, NLTK, GLiNER | Tokenization, POS, NER, SRL, Coref, Segmentation |
| **2. ML Models** (if needed) | HuggingFace free models, AllenNLP | Enhanced SRL, embeddings |
| **3. LLMs** (reasoning only) | OpenCode → KiloCode → Cline → OpenRouter → Codex | Semantic disambiguation, argument mining, cross-layer inference |

### Language Support

- **Primary:** English
- **Secondary:** Arabic (future phase)

### Conflict Resolution Formula

```
score = confidence × (evidence_token_count / max_tokens_in_source_layer)

Tiebreaker rules (in order):
1. Prefer relationship from richer layer (Table > List > Paragraph)
2. Prefer relationship with more predicate support
3. If still tied: both kept at 0.7 × original confidence, marked as `confidence_vote = tie`
```

### Validation Units

Checkpoints CP1-CP5 converted to mandatory `ValidationUnit` Processing Units:
- Runs AFTER each stage completes
- Fails the pipeline if checks don't pass
- Produces a validation report (pass/fail per check)

### Embedding Models (Self-Contained)

Prism bundles ONNX embedding models locally — no downloads required at runtime:

| Model | Dimensions | Size | Location | Use Case |
|-------|-----------|------|----------|----------|
| `multilingual-e5-base` | 768d | ~1.1GB | `data/models/multilingual-e5-base/` | Topic Clustering (4.5), Cross-Layer ER (4.1), Cross-Linking (4.4) |
| `multilingual-e5-small` | 384d | ~470MB (standard) + 235MB (quantized) | `data/models/multilingual-e5-small/` | Semantic Segmentation fallback (3.2), lightweight similarity ops |

Both models use ONNX format, compatible with `fastembed` Python library (`pip install fastembed`).
Quantized variant (`model_O4.onnx`) available for faster inference with minimal accuracy loss.

### Cross-Cutting Cascade Pattern

For any step with uncertainty, use 3-tier cascade:
```
Tier 1: Rule-based / Python NLP library  ← Fast, deterministic, free
Tier 2: ML model (if NLP library insufficient)  ← Still offline, reasonable cost
Tier 3: LLM API (only if 1+2 fail)  ← Last resort, reasoning/disambiguation only
```

---

## e5-base Capability Scope & Fallback Matrix

### What e5-base CAN do

| Capability | Processing Unit | Coverage |
|------------|----------------|----------|
| Semantic Similarity (text ↔ text) | CrossLayerEntityResolver (4.1) | Partial — similarity score only |
| Topic Clustering (vector clustering) | TopicClusterer (4.5) | Full |
| Explicit semantic linking | CrossLayerLinker (4.4) | Partial — explicit links only |

### What e5-base CANNOT do (12 gaps)

> `e5-base` is an embedding model — it produces vectors, not structured outputs. It cannot tokenize, classify, extract, reason, or resolve.

#### Gap 1: Tokenization (Unit 1.2 — TokenStreamBuilder)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | spaCy tokenizer | `nlp.tokenizer(text)` → list of Token objects | Free, offline, ~1ms/page |
| **2** | NLTK word_tokenize | `nltk.word_tokenize(text)` | Free, offline, lighter |
| **3** | Regex tokenizer | `re.findall(r'\b\w+\b', text)` | Zero deps, least accurate |

#### Gap 2: POS Tagging + Dependency Parsing

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | spaCy `en_core_web_trf` | `nlp(text)` → `token.pos_`, `token.dep_`, `token.head` | Free, offline, ~50ms/sentence |
| **2** | Stanza English | `stanza.Pipeline('en', processors='token,pos,depparse')` | Free, offline, ~100ms/sentence |
| **3** | NLTK taggers | `nltk.pos_tag(tokens)` | Free, offline, less accurate |

#### Gap 3: NER — Entity Extraction (Unit 3.4 — EntityExtractor)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | spaCy NER | `nlp(text).ents` → 18 built-in label types | Free, offline |
| **2** | GLiNER (zero-shot) | `GLiNER.from_pretrained("urchade/gliner_multi_v2.1")` — custom labels without training | Free, offline, ~200ms/doc |
| **3** | Stanza NER | `stanza.Pipeline('en', processors='ner')` | Free, offline |
| **4** | LLM (OpenCode API) | Prompt: `"Extract all named entities with types from: [text]"` | API call, slowest |

#### Gap 4: SRL — Predicate Extraction (Unit 3.3 — PredicateExtractor)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | Stanza SRL | `stanza.Pipeline('en', processors='srl')` → PROPBANK frames | Free, offline, ~150ms/sentence |
| **2** | AllenNLP SRL | `Predictor.from_path("structured-prediction-srl-conll2012")` | Free, offline, heavier |
| **3** | spaCy dep-parse heuristic | Extract ROOT verb + nsubj + dobj/dobj manually from dependency tree | Free, offline, partial coverage |
| **4** | LLM (OpenCode API) | Prompt: `"Extract predicate frames (verb, agent, patient, instrument, location, time) from: [sentence]"` | API call |

#### Gap 5: Coreference Resolution (Unit 3.5 — EntityResolver)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | Stanza Coref | `stanza.Pipeline('en', processors='coref')` → cluster mentions | Free, offline, ~200ms/doc |
| **2** | NeuralCoref (spaCy) | `neuralcoref.add_to_pipe(nlp)` → clusters on doc | Free, offline, deprecated but functional |
| **3** | Rule-based | Same exact name OR pronoun + proximity within 3 sentences | Free, offline, high false-negative |
| **4** | LLM (OpenCode API) | Prompt: `"Resolve all pronouns and references in: [text]. Return entity each refers to."` | API call |

#### Gap 6: Topic Label Generation (Unit 3.1 — TopicDetector)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | Heading-based | If physical heading exists → use as topic label | Free, zero compute |
| **2** | KeyBERT | `KeyBERT().extract_keywords(text, top_n=3)` → use top phrase as label | Free, offline, ~50ms |
| **3** | YAKE! | `yake.KeywordExtractor(lan="en").extract_keywords(text)` | Free, offline, no model needed |
| **4** | e5-base + clustering | Cluster token embeddings → KeyBERT names the cluster | Free, offline |
| **5** | LLM (OpenCode API) | Prompt: `"What is the topic of this section? Answer in one phrase."` | API call |

#### Gap 7: Semantic Paragraph Segmentation (Unit 3.2 — SemanticParagraphSegmenter)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | spaCy sentence boundaries | `list(nlp(text).sents)` → sentences as base units | Free, offline |
| **2** | Discourse marker regex | Split on: `however\|therefore\|furthermore\|in contrast\|on the other hand` | Free, offline |
| **3** | e5-base sliding window | `cosine_sim(embed(window[i]), embed(window[i+1]))` → drop < 0.7 = boundary | Free, offline, ~100ms/doc |
| **4** | LLM (OpenCode API) | Prompt: `"Split this paragraph into distinct semantic units. Return each unit separately."` | API call |

#### Gap 8: Relationship Type Classification (Unit 3.6 — RelationshipExtractor)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | LLM (OpenCode API) | Prompt: `"What is the semantic relation between [entity_A] and [entity_B] in: [context]? Choose from: CAUSES, DEPENDS_ON, PART_OF, LOCATED_IN, TEMPORAL, ARGUMENT_FOR, ARGUMENT_AGAINST, CONDITIONAL, OTHER."` | API call, reasoning |
| **2** | LLM (KiloCode API) | Same prompt, different provider | API call, fallback |
| **3** | LLM (Cline API) | Same prompt, third provider | API call, fallback |
| **4** | Dependency tree patterns | `nsubj → ROOT → dobj` → `PERFORMS`; `nmod:of → nmod` → `PART_OF` | Free, offline, rule-based |
| **5** | Predefined taxonomy + patterns | Fixed relation types with regex + POS patterns | Free, offline |
| **6** | ML classifier (fine-tuned) | BERT trained on SemEval/ontology relations | Free, offline, needs training data |

#### Gap 9: Conflict Resolution Adjudication (Unit 4.3 — ConflictResolver)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | Confidence-weighted formula | `score = confidence × (evidence_tokens / max_tokens)` → highest wins | Free, zero compute |
| **2** | Layer priority rules | Table > List > Paragraph (richer layer wins) | Free, zero compute |
| **3** | LLM (OpenCode API) | Prompt: `"Two layers produce contradictory claims: [claim_A] vs [claim_B]. Which is more supported by evidence? Evidence A: [evidence_A], Evidence B: [evidence_B]"` | API call |

#### Gap 10: Argument Mining (Unit 4.4 — CrossLayerLinker)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | LLM (OpenCode API) | Prompt: `"Identify the premise and conclusion in this argument: [text]. Also identify any supporting evidence and the relation between them."` | API call, reasoning |
| **2** | LLM (KiloCode API) | Same prompt, different provider | API call, fallback |
| **3** | LLM (Cline API) | Same prompt, third provider | API call, fallback |
| **4** | Discourse marker patterns | `because\|since\|therefore\|thus\|consequently\|as a result` → causal/argument | Free, offline |
| **5** | Predicate frame chaining | If `predicate_A(patient) == predicate_B(agent)` → causal chain | Free, offline |

#### Gap 11: Implicit Causal Detection (Unit 4.4 — CrossLayerLinker)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | LLM (OpenCode API) | Prompt: `"Is there a causal relationship between: [statement_A] and [statement_B]? Answer yes/no with confidence 0-1. Explain the causal mechanism."` | API call, reasoning |
| **2** | LLM (KiloCode API) | Same prompt, different provider | API call, fallback |
| **3** | LLM (Cline API) | Same prompt, third provider | API call, fallback |
| **4** | Temporal ordering + proximity | Event A before Event B + same topic cluster = causal candidate | Free, offline |
| **5** | e5-base similarity | `cosine_sim(embed(predicate_A), embed(predicate_B))` > 0.8 = potential link | Free, offline |

#### Gap 12: Confidence Calibration (Unit 4.6 — ConfidenceScorer)

| Priority | Fallback | Integration Mechanism | Cost |
|----------|----------|----------------------|------|
| **1** | Statistical aggregation | `avg(confidence_per_unit × tier_weight)` where tier_weight: spaCy=1.0, Stanza=0.95, LLM=0.7 | Free, zero compute |
| **2** | Evidence-based scaling | `confidence × log(evidence_count + 1) / log(max_evidence + 1)` | Free, zero compute |
| **3** | LLM (OpenCode API) | Prompt: `"Rate confidence 0.0-1.0 for this claim: [claim] based on this evidence: [evidence]"` | API call |

### Summary: LLM Usage Points

LLMs are the **primary** tool for semantic reasoning tasks (relationships, arguments, causality) and **fallback** for structural NLP tasks (tokenization, NER, SRL, coref):

#### Primary Usage (LLM first, patterns as fallback)

| # | Scenario | LLM Provider Priority |
|---|----------|----------------------|
| 1 | **Relationship Type Classification** | OpenCode → KiloCode → Cline → Patterns → Taxonomy → ML |
| 2 | **Argument Mining** | OpenCode → KiloCode → Cline → Discourse markers → Predicate chaining |
| 3 | **Implicit Causal Detection** | OpenCode → KiloCode → Cline → Temporal ordering → e5-base similarity |

#### Fallback Usage (NLP first, LLM last resort)

| # | Scenario | Why NLP first |
|---|----------|--------------|
| 4 | NER with custom labels | spaCy covers standard cases; GLiNER handles zero-shot |
| 5 | SRL for complex sentences | Stanza SRL handles most English sentences |
| 6 | Coreference resolution | Stanza coref handles ~3 sentence window well |
| 7 | Topic labeling without heading | KeyBERT/YAKE produce reasonable phrases |
| 8 | Semantic segmentation | spaCy boundaries + discourse markers cover 90% |
| 9 | Conflict adjudication | Confidence formula resolves most cases |
| 10 | Confidence calibration | Statistical aggregation is reliable |

### LLM API Priority Order

```
1. OpenCode API    ← First choice (fastest, cheapest)
2. KiloCode API    ← Second choice
3. Cline API       ← Third choice
4. OpenRouter API  ← Fourth choice (aggregator, more options)
5. Codex API       ← Last choice (OpenAI, most expensive)
```

---

## Open Decisions (to resolve during BUILD planning)

1. **Language for implementation:** Python (rapid prototyping, rich NLP ecosystem) or Rust (performance, type safety)?
2. **Graph storage:** In-memory (NetworkX) for v1? Or persistent (SQLite + graph extension)?
3. **Configuration format:** YAML, JSON, or TOML?
4. **Error handling strategy:** Fail-fast on first invalid unit? Or degrade gracefully with confidence=0?

# 03_STAGE_MATRIX — Prism Hybrid Neuro-Symbolic NLP Pipeline Implementation Matrix

> Brutally honest evaluation of all pipeline stages/sub-steps to catch gaps before implementation. Based on `01_DEFINE.md` and `02_PLAN.md`.

## Summary Table
| Step ID | Stage Name | Processing Unit | Input Type | Output Type | Risk Level |
|---------|------------|-----------------|------------|-------------|------------|
| 1.0 | Stage 1: Holistic Document Tokenization | - | Stage1Input | Stage1Output | - |
| 1.1 | Document Conversion | DocumentConverter | Stage1Input | str (Markdown) | Medium |
| 1.2 | Token Stream Construction | TokenStreamBuilder | Stage1Input (Markdown) + TokenizationConfig | dict[str, Token] | Low |
| 1.3 | Metadata Indexing | MetadataIndexer | Stage1Output (tokens) + TokenizationConfig | TokenMetadataIndex | Low |
| 2.0 | Stage 2: Physical Topology Analyzer | - | Stage2Input | Stage2Output | - |
| 2.1 | Markdown AST Parsing | MarkdownParser | str (Markdown) + TopologyConfig | MarkdownAST | Low |
| 2.2 | Layer Classification | LayerClassifier | MarkdownAST + TopologyConfig | dict[str, list[PhysicalComponent]] | Medium |
| 2.3 | Component-Token Mapping | ComponentMapper | list[PhysicalComponent] + Stage1Output + TopologyConfig | dict[str, list[str]] | Medium |
| 2.4 | Topology Report Assembly | TopologyBuilder | list[PhysicalComponent] + Stage1Output + TopologyConfig | Stage2Output | Low |
| 3.0 | Stage 3: Semantic Topology Analyzer (Per Physical Layer) | - | Stage3Input | Stage3Output | - |
| 3.1 | Topic Detection | TopicDetector | PhysicalComponent + Stage1Output + SemanticConfig | topic_label: str + mini_topics: list[MiniTopic] | Medium |
| 3.2 | Semantic Paragraph Segmentation | SemanticParagraphSegmenter | PhysicalComponent + topic info + Stage1Output + SemanticConfig | list[SemanticParagraphUnit] | High |
| 3.3 | Predicate Extraction | PredicateExtractor | SemanticParagraphUnit list + Stage1Output + SemanticConfig | list[PredicateFrame] | High |
| 3.4 | Entity Extraction | EntityExtractor | SemanticParagraphUnit list + Stage1Output + SemanticConfig | list[RawEntity] | High |
| 3.5 | Intra-Layer Entity Resolution | EntityResolver | list[RawEntity] + SemanticConfig | dict[str, Entity] | High |
| 3.6 | Relationship Extraction | RelationshipExtractor | dict[str, Entity] + list[PredicateFrame] + SemanticConfig | list[Relationship] | High |
| 3.7 | Mini-PG Construction | MiniPGBuilder | Topic info + dict[str, Entity] + list[PredicateFrame] + list[Relationship] + SemanticConfig | MiniPG | Low |
| 3.8 | Recursive Sub-Component Processing | Reuses 3.1-3.7 | PhysicalComponent (sub-component) + parent context + SemanticConfig | list[str] (child MiniPG IDs) | Medium |
| 4.0 | Stage 4: Aggregation Layer (Cross-Layer MAP-REDUCE) | - | Stage4Input | Stage4Output | - |
| 4.1 | Cross-Layer Entity Resolution | CrossLayerEntityResolver | All MiniPG entities + Stage1Output + AggregationConfig | dict[str, Entity] (global) | High |
| 4.2 | Mini-PG Merging | MiniPGMerger | All MiniPGs + global entities + AggregationConfig | GlobalPG draft | Medium |
| 4.3 | Conflict Resolution | ConflictResolver | GlobalPG draft.relationships + AggregationConfig | list[Relationship] (resolved) | High |
| 4.4 | Cross-Topological Linking | CrossLayerLinker | GlobalPG draft + all MiniPGs + Stage1Output + AggregationConfig | list[Relationship] (cross-layer) | High |
| 4.5 | Topic Clustering | TopicClusterer | All MiniPG topics + Stage1Output + AggregationConfig | list[TopicCluster] | Medium |
| 4.6 | Confidence Scoring | ConfidenceScorer | GlobalPG draft + all sources + AggregationConfig | confidence_summary: dict | Medium |
| 4.7 | Global PG Assembly | GlobalPGBuilder | All merged components + clusters + confidence + AggregationConfig | GlobalPG | Low |

---

## 1.0 Stage 1: Holistic Document Tokenization
**Purpose:** Convert raw documents to structured Markdown, flatten to global token stream, assign document-wide sequential token IDs, and index token metadata.

### 1.1 Document Conversion
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 1: Holistic Document Tokenization — Convert raw non-Markdown documents (PDF, DOCX, PPTX) to structured Markdown as input to downstream tokenization. |
| Processing Unit | DocumentConverter |
| Input Schema | Stage1Input: {source: str, source_type: str, config: TokenizationConfig} <br> TokenizationConfig: {tokenizer: str, include_whitespace: bool, language: str} |
| Output Schema | str (structured Markdown text preserving headings, lists, tables, code blocks) |
| Swappable Implementations | Docling, Pandoc, custom parser |
| Critical Operations | 1. Validate source exists/is readable. 2. Convert source to Markdown preserving structural elements. 3. Return clean Markdown string with no binary artifacts. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Clear input (raw doc + type) and output (Markdown) with explicit conversion target. No ambiguity on structured Markdown. |
| Inputs Sufficient? | Yes | Stage1Input provides all required fields: source, source_type, config. |
| Outputs Complete? | Yes | Only need Markdown string; downstream TokenStreamBuilder only requires Markdown text. |
| Swappable Options Adequate? | Yes | Covers major conversion tools (Docling for PDF/DOCX, Pandoc for broad format support, custom for edge cases). Sufficient for Phase 1 scope (Markdown only per DEFINE). |
| Dependencies | None | Stage 1 first step, no prior stage dependencies. |
| Risk Level | Medium | Conversion errors (e.g., broken tables, lost headings) propagate to all downstream stages. Docling/Pandoc have known edge cases with complex layouts. |

---

### 1.2 Token Stream Construction
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 1: Holistic Document Tokenization — Flatten entire Markdown document into a single sequential token stream with global document-wide IDs. |
| Processing Unit | TokenStreamBuilder |
| Input Schema | str (Markdown text) + TokenizationConfig: {tokenizer: str, include_whitespace: bool, language: str} |
| Output Schema | dict[str, Token] where Token: {id: str, text: str, lemma: str = None, pos: str = None, ner_label: str = None} <br> Example: {T0: Token(id=T0, text=المشروع, ...), ...} |
| Swappable Implementations | Whitespace tokenizer, SentencePiece, spaCy tokenizer, regex-based |
| Critical Operations | 1. Flatten entire Markdown into sequential token stream. 2. Assign global sequential IDs T0, T1, ... document-wide. 3. Populate Token.text for each entry. 4. Handle edge cases (whitespace, punctuation) per config. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Explicit steps: flatten, assign global IDs, no layer mapping yet. |
| Inputs Sufficient? | Yes | Markdown text + config (tokenizer type, include_whitespace, language) from Stage1Input. |
| Outputs Complete? | Yes | Token.lemma/pos/ner_label are intentionally unpopulated at this stage (filled later). Matches DEFINE Stage 1 output. |
| Swappable Options Adequate? | Yes | Covers rule-based (whitespace, regex), ML-based (spaCy, SentencePiece). Sufficient for Arabic + English support. |
| Dependencies | 1.1 (Document Conversion) | Requires Markdown text output from 1.1. |
| Risk Level | Low | Tokenization is well-understood; global ID assignment is deterministic. Only risk is tokenizer-specific edge cases. |

---

### 1.3 Metadata Indexing
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 1: Holistic Document Tokenization — Build positional metadata per token (char offsets, source line, bounding box). |
| Processing Unit | MetadataIndexer |
| Input Schema | dict[str, Token] (global token stream) + str (source text) + TokenizationConfig |
| Output Schema | TokenMetadataIndex (dict[str, TokenMetadata]) where TokenMetadata: {token_id: str, char_start: int, char_end: int, source_line: int | None, bounding_box: tuple | None} |
| Swappable Implementations | Char-offset indexer, Line-based indexer, BBox-aware indexer |
| Critical Operations | 1. Map each token to its character offset in source text. 2. Record source line number. 3. Populate bounding_box (null for Markdown). 4. Ensure no tokens have missing metadata. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Explicit metadata fields per DEFINE and PLAN. |
| Inputs Sufficient? | Yes | Token stream has text, source text is available, config has language for line offset calculation. |
| Outputs Complete? | Yes | All required metadata fields per DEFINE's Token Metadata Schema. |
| Swappable Options Adequate? | Yes | Char-offset is baseline, line-based for simple docs, BBox for future OCR support. |
| Dependencies | 1.2 (Token Stream Construction) | Requires token texts and IDs to map offsets. |
| Risk Level | Low | Deterministic calculation of char offsets; line-based indexing is straightforward. |

---

## 2.0 Stage 2: Physical Topology Analyzer
**Purpose:** Parse Markdown into AST, classify physical layer types, map components to global token IDs, and output PhysicalTopologyReport.

### 2.1 Markdown AST Parsing
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 2: Physical Topology Analyzer — Parse structured Markdown into a standard Abstract Syntax Tree (AST) for layer classification. |
| Processing Unit | MarkdownParser |
| Input Schema | str (Markdown text) + TopologyConfig: {layer_types_to_detect: list[str], nesting_depth_limit: int} |
| Output Schema | MarkdownAST (serializable AST with node types: heading, paragraph, table, list, etc.) |
| Swappable Implementations | markdown-it-py, mistune, CommonMark |
| Critical Operations | 1. Parse Markdown into standard AST. 2. Preserve all structural node types per DEFINE's Physical Layer Types. 3. Return serializable AST for downstream classification. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Clear input (Markdown) and output (AST). Explicit parser options. |
| Inputs Sufficient? | Yes | Markdown text + config (layer types to detect, nesting depth limit). |
| Outputs Complete? | Yes | AST must include all node types per DEFINE's 10 Physical Layer Types. |
| Swappable Options Adequate? | Yes | All major Python Markdown parsers, covers all required AST node types. |
| Dependencies | 1.1 (Document Conversion) | Requires Markdown text output. |
| Risk Level | Low | Mature parsers with well-tested AST outputs. |

---

### 2.2 Layer Classification
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 2: Physical Topology Analyzer — Classify AST nodes into DEFINE's Physical Layer Types and instantiate PhysicalComponents. |
| Processing Unit | LayerClassifier |
| Input Schema | MarkdownAST + TopologyConfig |
| Output Schema | dict[str, list[PhysicalComponent]] where PhysicalComponent: {component_id: str, layer_type: str, raw_content: str, token_span: list[str] = None, parent_id: str = None, children: list[str] = None, attributes: dict = {}} |
| Swappable Implementations | Rule-based classifier, ML-based classifier |
| Critical Operations | 1. Traverse AST nodes. 2. Classify each node into one of DEFINE's Physical Layer Types. 3. Assign unique component_id per component. 4. Extract raw content for each component. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Partially | DEFINE lists 10 layer types, but rule-based classification may miss edge cases (e.g., blockquote containing a list). ML-based classifier has no specified training data or labels. |
| Inputs Sufficient? | Yes | AST has node types, config specifies which layer types to detect. |
| Outputs Complete? | No | PhysicalComponent.token_span is not populated here (requires 2.3 ComponentMapper). Output is partial. |
| Swappable Options Adequate? | No | ML-based classifier is unactionable (no training data/labels). Rule-based is sufficient for Phase 1 but ML option adds no value without supporting artifacts. |
| Dependencies | 2.1 (Markdown AST Parsing) | Requires AST output. |
| Risk Level | Medium | Misclassification of layer types (e.g., treating code block as paragraph) propagates to Stage 3, causing incorrect semantic analysis. |

---

### 2.3 Component-Token Mapping
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 2: Physical Topology Analyzer — Map each PhysicalComponent to its corresponding global token IDs using Stage 1 metadata. |
| Processing Unit | ComponentMapper |
| Input Schema | list[PhysicalComponent] (from 2.2, without token_span) + Stage1Output (tokens + metadata) + TopologyConfig |
| Output Schema | dict[str, list[str]] (component ID → list of global token IDs e.g., [T14, T15, ..., T89]) |
| Swappable Implementations | Char-span mapper, Line-based mapper |
| Critical Operations | 1. For each component, get char span from raw content. 2. Map char span to global token IDs using Stage1's metadata index. 3. Populate PhysicalComponent.token_span. 4. Handle nested components per nesting_depth_limit. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Explicit mapping from component char spans to global token IDs. |
| Inputs Sufficient? | Yes | Components have raw content/char spans, Stage1 has token metadata with char offsets. |
| Outputs Complete? | Yes | All PhysicalComponents now have token_span populated. |
| Swappable Options Adequate? | Yes | Char-span is precise, line-based is fallback for simple docs. |
| Dependencies | 2.2 (Layer Classification), Stage 1 (token metadata) | Requires component list and token metadata. |
| Risk Level | Medium | Char-span mismatches between Markdown parser and token metadata cause orphan tokens or missing tokens. |

---

### 2.4 Topology Report Assembly
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 2: Physical Topology Analyzer — Assemble final PhysicalTopologyReport from all components and token mappings. |
| Processing Unit | TopologyBuilder |
| Input Schema | list[PhysicalComponent] (with token_span) + Stage1Output + TopologyConfig |
| Output Schema | Stage2Output: {discovered_layers: dict[str, list[PhysicalComponent]], layer_types: list[str], is_single_layer: bool, component_to_tokens: dict[str, list[str]]} |
| Swappable Implementations | Tree builder, Flat index builder |
| Critical Operations | 1. Group components by layer type. 2. Set is_single_layer (True if only paragraphs exist). 3. Build component_to_tokens dict. 4. Validate all tokens are assigned to at least one component (CP2). |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Explicit output schema per PLAN. |
| Inputs Sufficient? | Yes | All components and token data available. |
| Outputs Complete? | Yes | Matches Stage2Output schema exactly. |
| Swappable Options Adequate? | Yes | Tree builder for nested components, flat for simple docs. |
| Dependencies | 2.3 (Component-Token Mapping) | Requires completed component list with token spans. |
| Risk Level | Low | Deterministic assembly; validation catches missing tokens. |

---

## 3.0 Stage 3: Semantic Topology Analyzer (Per Physical Layer)
**Purpose:** For each physical layer, perform topic detection, semantic segmentation, predicate/entity extraction, entity resolution, relationship extraction, and Mini-PG construction. Supports recursive processing of sub-components.

### 3.1 Topic Detection
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Identify the global and mini-topics for a physical layer. |
| Processing Unit | TopicDetector |
| Input Schema | PhysicalComponent + Stage1Output (tokens) + SemanticConfig: {topic_detection: str, entity_extractor: str, ..., language: str, recursion_depth: int} |
| Output Schema | topic_label: str + mini_topics: list[MiniTopic] where MiniTopic: {topic_id: str, label: str, token_span: list[str], confidence: float} |
| Swappable Implementations | Heading-based, BERTopic, LLM-based, keyword-based |
| Critical Operations | 1. Extract topic from parent heading if available (heading-based). 2. For layers without heading, use statistical/topic modeling. 3. Identify mini-topics (sub-components like table cells). 4. Assign confidence per topic. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Partially | DEFINE says topic is from heading or statistical, but statistical is undefined. Mini-topic identification rules are vague (when is a table cell a mini-topic?). |
| Inputs Sufficient? | Yes | Component has raw content/tokens, Stage1 has token texts, config specifies topic detection method. |
| Outputs Complete? | No | MiniTopic requires token_span mapping to global IDs, which is not explicitly output here. |
| Swappable Options Adequate? | No | BERTopic requires embedding model config, LLM-based requires prompt template, neither specified. Heading-based is well-defined, others are unactionable. |
| Dependencies | Stage 2 (PhysicalComponent), Stage 1 (tokens) | Requires component and token data. |
| Risk Level | Medium | Incorrect topic detection leads to wrong semantic context for all downstream steps in the layer. |

---

### 3.2 Semantic Paragraph Segmentation
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Detect semantic paragraph units within a physical layer (may not align with physical boundaries). |
| Processing Unit | SemanticParagraphSegmenter |
| Input Schema | PhysicalComponent + topic info (from 3.1) + Stage1Output + SemanticConfig |
| Output Schema | list[SemanticParagraphUnit] where SemanticParagraphUnit: {unit_id: str, token_span: list[str], component_id: str, confidence: float} |
| Swappable Implementations | Rule-based (line breaks), semantic similarity clustering, NLP-based |
| Critical Operations | 1. Split layer content into semantic units (not just physical line breaks). 2. Map each unit to global token IDs. 3. Handle layer-specific semantics (e.g., table cell = semantic unit). |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | Semantic paragraph units are not defined. No rules for segmentation (how is a semantic unit different from a physical paragraph?). DEFINE says units may not align with physical boundaries but no criteria. |
| Inputs Sufficient? | Yes | Content and tokens available. |
| Outputs Complete? | No | No confidence score for each unit, no linkage to mini-topics from 3.1. |
| Swappable Options Adequate? | No | Semantic similarity clustering requires embedding model, NLP-based requires specific NLP library config. Only rule-based is actionable. |
| Dependencies | 3.1 (Topic Detection) | Requires topic context for segmentation. |
| Risk Level | High | Poor segmentation breaks predicate/entity extraction, as sentences may be split across units or merged incorrectly. |

---

### 3.3 Predicate Extraction
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Extract predicate frames (SRL) from semantic paragraph units. |
| Processing Unit | PredicateExtractor |
| Input Schema | list[SemanticParagraphUnit] + Stage1Output + SemanticConfig: {predicate_extractor: str, ...} |
| Output Schema | list[PredicateFrame] where PredicateFrame: {predicate: str, agent: str | None, patient: str | None, instrument: str | None, location: str | None, time: str | None, source_tokens: list[str], source_layer: str} |
| Swappable Implementations | spaCy SRL, Stanza SRL, LLM-based, pattern-based |
| Critical Operations | 1. Perform SRL on each semantic paragraph. 2. Extract predicate frames with all roles. 3. Map each frame to source global token IDs. 4. Assign source_layer (component ID). |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Partially | PredicateFrame schema is explicit, but SRL for Arabic is poorly supported by spaCy/Stanza. No Arabic SRL options listed. |
| Inputs Sufficient? | Yes | Semantic paragraphs have token spans, tokens have text. |
| Outputs Complete? | Yes | Matches PredicateFrame schema exactly. |
| Swappable Options Adequate? | No | Arabic SRL support is missing. spaCy/Stanza have limited Arabic SRL. LLM-based is only viable option for Arabic but no prompt specified. |
| Dependencies | 3.2 (Semantic Paragraph Segmentation) | Requires semantic paragraph units. |
| Risk Level | High | SRL failure (especially for Arabic) leads to no predicates, breaking relationship extraction and Mini-PG construction. |

---

### 3.4 Entity Extraction
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Extract raw entities from semantic paragraph units within the layer scope. |
| Processing Unit | EntityExtractor |
| Input Schema | list[SemanticParagraphUnit] + Stage1Output + SemanticConfig: {entity_extractor: str, ...} |
| Output Schema | list[RawEntity] where RawEntity: {entity_id: str, label: str, mentions: list[str], confidence: float} |
| Swappable Implementations | spaCy NER, Stanza NER, LLM-based, regex/keyword-based |
| Critical Operations | 1. Extract entities from each semantic paragraph. 2. Map entities to global token IDs. 3. Assign NER label, confidence. 4. Handle layer-specific entities (e.g., table column entities). |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Partially | Entity schema is explicit, but NER labels are not defined (what labels are supported? Only PROJECT as per DEFINE example?). |
| Inputs Sufficient? | Yes | Paragraph tokens available. |
| Outputs Complete? | No | Raw entities are not linked to mini-topics or semantic paragraphs. |
| Swappable Options Adequate? | No | Arabic NER support in spaCy/Stanza is limited. Regex/keyword-based is only viable for known entity types, LLM-based no prompt specified. |
| Dependencies | 3.2 (Semantic Paragraph Segmentation) | Requires semantic paragraph units. |
| Risk Level | High | Missed entities break entity resolution and graph completeness. |

---

### 3.5 Intra-Layer Entity Resolution
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Resolve entity ambiguity and merge duplicates within the layer scope. |
| Processing Unit | EntityResolver |
| Input Schema | list[RawEntity] + SemanticConfig: {entity_resolver: str, ...} |
| Output Schema | dict[str, Entity] where Entity: {id: str, label: str, mentions: list[str], attributes: dict, confidence: float, source_component: str} |
| Swappable Implementations | spaCy coref, rule-based alias resolution, LLM-based, embedding similarity |
| Critical Operations | 1. Merge duplicate entities within the layer. 2. Resolve coreferences (e.g., it refers to the project). 3. Populate entity attributes. 4. Assign local confidence score. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | Coreference resolution rules are not specified. No confidence threshold for merging entities via embedding similarity. |
| Inputs Sufficient? | Yes | Raw entities with mentions and labels. |
| Outputs Complete? | No | Entity.attributes schema is undefined (what attributes are supported?). |
| Swappable Options Adequate? | No | spaCy coref for Arabic is unsupported. Embedding similarity requires embedding model config. LLM-based no prompt. |
| Dependencies | 3.4 (Entity Extraction) | Requires raw entities. |
| Risk Level | High | Incorrect entity merging leads to duplicate nodes or merged distinct entities in Mini-PG. |

---

### 3.6 Relationship Extraction
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Extract relationships between resolved entities from predicate frames. |
| Processing Unit | RelationshipExtractor |
| Input Schema | dict[str, Entity] (resolved) + list[PredicateFrame] + SemanticConfig: {relationship_extractor: str, ...} |
| Output Schema | list[Relationship] where Relationship: {id: str, source_entity_id: str, target_entity_id: str, relation_type: str, predicate_text: str, confidence: float, evidence_tokens: list[str]} |
| Swappable Implementations | Pattern-based, LLM-based, dependency-tree traversal |
| Critical Operations | 1. Extract relationships between entities from predicate frames. 2. Infer implicit relationships (e.g., causal from context). 3. Map relationships to evidence tokens. 4. Assign relation_type from defined list (CAUSES, DEPENDS_ON, etc.). |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | Relation types are listed but no rules for inferring implicit relationships. Arabic dependency parsing is limited. |
| Inputs Sufficient? | Yes | Entities and predicates available. |
| Outputs Complete? | No | Relationship.alternative_hypotheses is not populated at this stage (done in Stage 4). |
| Swappable Options Adequate? | No | Arabic dependency parsing is limited. LLM-based no prompt specified. |
| Dependencies | 3.3 (Predicate Extraction), 3.5 (Intra-Layer Entity Resolution) | Requires predicates and resolved entities. |
| Risk Level | High | Missed or incorrect relationships break graph edges and cross-layer linking. |

---

### 3.7 Mini-PG Construction
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Assemble all layer outputs into a Mini Property Graph. |
| Processing Unit | MiniPGBuilder |
| Input Schema | Topic info (3.1) + resolved entities (3.5) + predicates (3.3) + relationships (3.6) + SemanticConfig |
| Output Schema | MiniPG: {layer_id: str, parent_layer_id: str | None, topic_label: str, mini_topics: list[MiniTopic], entities: dict[str, Entity], predicates: list[PredicateFrame], relationships: list[Relationship], child_pg_ids: list[str]} |
| Swappable Implementations | NetworkX builder, custom graph builder |
| Critical Operations | 1. Assemble all components into MiniPG object. 2. Link to parent layer if sub-component. 3. Validate no missing required fields. 4. Assign child_pg_ids if recursive processing done. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Explicit MiniPG schema per DEFINE. |
| Inputs Sufficient? | Yes | All required components from prior steps. |
| Outputs Complete? | Yes | Matches MiniPG schema exactly. |
| Swappable Options Adequate? | Yes | NetworkX is standard for in-memory graphs, custom for other storage. |
| Dependencies | 3.1, 3.3, 3.5, 3.6 | Requires all prior step outputs. |
| Risk Level | Low | Deterministic assembly; validation catches missing fields. |

---

### 3.8 Recursive Sub-Component Processing
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 3: Semantic Topology Analyzer — Recursively process sub-components that are themselves physical layer types (e.g., table cell containing a list). |
| Processing Unit | Reuses 3.1-3.7 per sub-component |
| Input Schema | PhysicalComponent (sub-component) + parent MiniPG context + SemanticConfig: {recursion_depth: int, ...} |
| Output Schema | list[str] (child MiniPG IDs added to parent MiniPG.child_pg_ids) |
| Swappable Implementations | Same as 3.1-3.7 |
| Critical Operations | 1. Detect sub-components from PhysicalComponent.children. 2. Run full 3.1-3.7 on each sub-component. 3. Attach child MiniPG to parent. 4. Respect recursion_depth limit. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | Rules for detecting sub-components are not specified. When is a table cell a sub-component vs a mini-topic? |
| Inputs Sufficient? | Yes | Sub-components are identified in Stage 2's PhysicalComponent.children. |
| Outputs Complete? | No | No handling of cross-sub-component relationships (e.g., entity in child sub-component referenced in parent). |
| Swappable Options Adequate? | No | Same as prior steps — inadequate for Arabic, no config/prompts for LLM options. |
| Dependencies | 3.1-3.7, Stage 2 (sub-component list) | Requires parent processing and sub-component list. |
| Risk Level | Medium | Deep recursion causes performance issues; unhandled sub-components lead to missed semantic content. |

---

## 4.0 Stage 4: Aggregation Layer (Cross-Layer MAP-REDUCE)
**Purpose:** Merge all Mini-PGs into a global property graph with cross-layer entity resolution, conflict resolution, cross-topological linking, topic clustering, and confidence scoring.

### 4.1 Cross-Layer Entity Resolution
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 4: Aggregation Layer — Merge same entities mentioned across multiple physical layers into global entities. |
| Processing Unit | CrossLayerEntityResolver |
| Input Schema | All MiniPG entities (dict[str, Entity] per MiniPG) + Stage1Output + AggregationConfig: {entity_merge_strategy: str, ...} |
| Output Schema | dict[str, Entity] (global merged entities: merged mentions, layers list, source_layer) |
| Swappable Implementations | Embedding similarity, LLM-based, rule-based alias matching |
| Critical Operations | 1. Identify same entity across multiple MiniPGs. 2. Merge mentions from all layers. 3. Resolve conflicts (e.g., different labels for same token). 4. Assign global entity ID. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | No similarity threshold for embedding-based merging, no alias rules for rule-based. LLM prompt not specified. |
| Inputs Sufficient? | Yes | All entities from MiniPGs have mentions and labels. |
| Outputs Complete? | No | Entity.confidence is not aggregated across layers (no formula for merging confidences). |
| Swappable Options Adequate? | No | Arabic embeddings for entity similarity not specified. LLM-based no prompt. |
| Dependencies | All Stage 3 MiniPG outputs | Requires all MiniPG entities. |
| Risk Level | High | Incorrect merging leads to duplicate global entities or merged distinct entities. |

---

### 4.2 Mini-PG Merging
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 4: Aggregation Layer — Union all Mini-PG elements into a draft Global Property Graph. |
| Processing Unit | MiniPGMerger |
| Input Schema | All MiniPGs + merged global entities (4.1) + AggregationConfig: {entity_merge_strategy: str, ...} |
| Output Schema | GlobalPG draft: {entities: dict[str, Entity], relationships: list[Relationship], predicates: list[PredicateFrame], topic_clusters: list = None, confidence_summary: dict = None} |
| Swappable Implementations | Union merger, intersection merger, weighted merger |
| Critical Operations | 1. Union all entities (use merged global entities). 2. Union all relationships, predicates. 3. Preserve provenance (which MiniPG produced each element). 4. Handle entity ID remapping to global IDs. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Partially | Union/merge strategies are listed but no rules for weighted merger (what weights to use?). |
| Inputs Sufficient? | Yes | All MiniPGs and merged entities available. |
| Outputs Complete? | No | Relationships are not conflict-resolved yet, topic clusters and confidence not added. |
| Swappable Options Adequate? | No | Weighted merger has no weight specification. Intersection would drop most elements, not useful for Phase 1. |
| Dependencies | 4.1 (Cross-Layer Entity Resolution), all Stage 3 MiniPGs | Requires merged entities and MiniPGs. |
| Risk Level | Medium | Incorrect merging strategy leads to incomplete or bloated global graph. |

---

### 4.3 Conflict Resolution
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 4: Aggregation Layer — Resolve contradictory relationships from different layers using confidence-weighted voting. |
| Processing Unit | ConflictResolver |
| Input Schema | GlobalPG draft.relationships + confidence scores + AggregationConfig: {conflict_resolution: str, min_confidence_threshold: float, ...} |
| Output Schema | list[Relationship] (conflict-resolved: select highest confidence, store alternatives in alternative_hypotheses) |
| Swappable Implementations | Confidence-weighted voting, LLM adjudication, rule-based priority |
| Critical Operations | 1. Detect contradictory relationships (same source/target, different relation_type). 2. Apply voting by confidence. 3. Store alternatives. 4. Remove low-confidence conflicts per min_confidence_threshold. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | DEFINE Open Question 4 explicitly notes confidence-weighted voting formula is missing. Rule-based priority rules not defined. |
| Inputs Sufficient? | Yes | Relationships have confidence scores and evidence tokens. |
| Outputs Complete? | No | alternative_hypotheses schema is undefined (what to store?). |
| Swappable Options Adequate? | No | LLM adjudication prompt not specified. Rule-based priority has no rules. |
| Dependencies | 4.2 (Mini-PG Merging) | Requires draft GlobalPG. |
| Risk Level | High | Unresolved conflicts lead to contradictory edges in final graph. |

---

### 4.4 Cross-Topological Linking
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 4: Aggregation Layer — Detect causal/argument/conditional relationships spanning multiple physical layers. |
| Processing Unit | CrossLayerLinker |
| Input Schema | GlobalPG draft + all MiniPGs + Stage1Output + AggregationConfig: {topic_clustering: str, ...} |
| Output Schema | list[Relationship] (added cross-layer causal/argument/conditional relationships) |
| Swappable Implementations | Causal chain detector, argument structure detector, conditional relation detector |
| Critical Operations | 1. Detect causal chains spanning layers. 2. Detect argument structures (evidence → conclusion across layers). 3. Add new relationships with cross-layer provenance. 4. Assign confidence. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | Detection rules for causal/argument/conditional relationships are not specified. No examples of cross-layer linking. |
| Inputs Sufficient? | Yes | All MiniPGs have topics, entities, predicates. |
| Outputs Complete? | No | No linkage to topic clusters (done in 4.5). |
| Swappable Options Adequate? | No | All options require NLP/LLM models for inference, no config or prompts specified. |
| Dependencies | 4.2 (Mini-PG Merging), all Stage 3 MiniPGs | Requires draft GlobalPG and MiniPGs. |
| Risk Level | High | Missed cross-layer links break the core value proposition of Prism (multi-layer inference). |

---

### 4.5 Topic Clustering
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 4: Aggregation Layer — Cluster semantically related paragraphs across different sections/layers into topic clusters. |
| Processing Unit | TopicClusterer |
| Input Schema | All MiniPG topics + Stage1Output + AggregationConfig: {topic_clustering: str, ...} |
| Output Schema | list[TopicCluster] where TopicCluster: {cluster_id: str, topic_label: str, component_ids: list[str], entities: list[str], centroid_embedding: list[float] | None} |
| Swappable Implementations | Embedding-based clustering, lexical overlap, LLM-based |
| Critical Operations | 1. Cluster MiniPGs by semantic similarity (not physical sections). 2. Assign cluster topic label. 3. Calculate centroid embedding if using embedding-based. 4. Link clusters to global entities. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | Clustering algorithm (k-means? HDBSCAN?) not specified. Embedding model not defined. Lexical overlap threshold not set. |
| Inputs Sufficient? | Yes | MiniPGs have topic labels and token spans. |
| Outputs Complete? | No | TopicCluster.entities linkage not defined (how to assign entities to clusters?). |
| Swappable Options Adequate? | No | Embedding-based requires model config. LLM-based no prompt. |
| Dependencies | All Stage 3 MiniPGs | Requires all MiniPG topic info. |
| Risk Level | Medium | Poor clustering leads to irrelevant topic groups, breaking cross-layer analysis. |

---

### 4.6 Confidence Scoring
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 4: Aggregation Layer — Assign and aggregate confidence scores to all global graph elements. |
| Processing Unit | ConfidenceScorer |
| Input Schema | GlobalPG draft + all sources (MiniPGs, tokens) + AggregationConfig: {confidence_scorer: str, min_confidence_threshold: float, ...} |
| Output Schema | confidence_summary: dict (entity_avg, relationship_avg, predicate_avg, etc.) + per-node/edge confidence |
| Swappable Implementations | Statistical model, LLM-based, rule-based |
| Critical Operations | 1. Aggregate confidence from all layers for each entity/relationship. 2. Calibrate confidence scores. 3. Generate summary stats. 4. Filter low-confidence elements per min_confidence_threshold. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | No | Statistical model formula not specified. LLM prompt for confidence calibration not provided. Rule-based rules not defined. |
| Inputs Sufficient? | Yes | All elements have per-layer confidence scores. |
| Outputs Complete? | No | Per-node/edge confidence is not added to GlobalPG elements, only summary. |
| Swappable Options Adequate? | No | All options lack config/prompts/rules. |
| Dependencies | 4.2, 4.3, 4.4, 4.5 | Requires all prior outputs. |
| Risk Level | Medium | Uncalibrated confidence scores make the graph untrustworthy for audit. |

---

### 4.7 Global PG Assembly
#### Sub-Step Details
| Field | Value |
|-------|-------|
| Stage Name & Purpose | Stage 4: Aggregation Layer — Assemble final Global Property Graph from all merged components. |
| Processing Unit | GlobalPGBuilder |
| Input Schema | All merged components + clusters + confidence + provenance + AggregationConfig |
| Output Schema | GlobalPG: {entities: dict[str, Entity], relationships: list[Relationship], predicates: list[PredicateFrame], topic_clusters: list[TopicCluster], confidence_summary: dict, provenance: dict} |
| Swappable Implementations | NetworkX builder, Neo4j builder, JSON builder |
| Critical Operations | 1. Assemble final GlobalPG object. 2. Validate all required fields. 3. Add provenance for every node/edge. 4. Generate confidence_summary. |

#### Critical Evaluation
| Evaluation Point | Result | Reasoning |
|------------------|--------|-----------|
| Scope Well-Defined? | Yes | Explicit GlobalPG schema per DEFINE. |
| Inputs Sufficient? | Yes | All components from prior steps. |
| Outputs Complete? | Yes | Matches GlobalPG schema exactly. |
| Swappable Options Adequate? | Yes | NetworkX for in-memory, Neo4j for persistent, JSON for export. |
| Dependencies | 4.1-4.6 | Requires all prior step outputs. |
| Risk Level | Low | Deterministic assembly; validation catches missing fields. |

---

## Overall Assessment

### Missing Steps That Should Exist
1. ~~**Pre-Stage Input Validation (0.5):**~~ → **Resolved as ValidationUnit** — Will be implemented as V0 (Pre-Tokenization Validation) in the ValidationUnit series.
2. ~~**Inter-Stage Validation Gates:**~~ → **Resolved** — CP1-CP5 converted to mandatory ValidationUnit Processing Units.
3. **LLM Prompt Management:** No step for managing LLM prompts for LLM fallback cases. Should add a PromptRegistry to centralize prompt storage and versioning.
4. ~~**Error Handling & Retry Logic:**~~ → **Resolved as part of ValidationUnit** — ValidationUnits handle failure detection; PipelineOrchestrator handles retry/degradation strategy.
5. **English NLP Benchmark:** No step to validate English tokenization, NER, SRL performance against a benchmark. To be added during BUILD phase.

### Steps That Are Over-Engineered
1. **Stage 3 Recursive Sub-Component Processing (3.8):** For Phase 1 (Markdown only, no complex nested components), recursion depth >1 is over-engineering. Should limit to depth 1 for Phase 1.
2. **Stage 4 Topic Clustering (4.5):** Cross-layer topic clustering is a nice-to-have, not required for Phase 1 success criteria. Over-engineered for initial release.
3. **Swappable ML/LLM Options for All Steps:** Most ML/LLM options lack config, prompts, or training data. Swappable options are over-engineered without supporting artifacts; should reduce to rule-based + 1 LLM option with defined prompts for Phase 1.

### Steps That Are Under-Specified
1. ~~**All Arabic NLP Steps (3.3, 3.4, 3.5, 4.1):**~~ → **Resolved** — English is primary language. spaCy, Stanza, NLTK, GLiNER all have excellent English support.
2. ~~**Conflict Resolution Formula (4.3):**~~ → **Resolved** — `score = confidence × (evidence_tokens / max_tokens_in_layer)` with tiebreaker rules defined.
3. ~~**Semantic Paragraph Segmentation Rules (3.2):**~~ → **Resolved** — Rule: 1:1 default. Split if >150 words + discourse markers detected via NLTK. LLM fallback only if rules fail.
4. **Relationship Extraction Inference Rules (3.6):** No rules for inferring implicit relationships (e.g., causal from context). No defined relation type taxonomy beyond examples (CAUSES, DEPENDS_ON).
5. **Cross-Topological Linking Rules (4.4):** Detection rules are partially resolved (3-tier cascade) but specific pattern lists and predicate linking logic still need definition.

### Cross-Cutting Concerns Not Addressed
1. **Provenance Tracking:** DEFINE specifies provenance field for GlobalPG, but no explicit step for tracking which stage/unit produced each node/edge across all stages. → **To be addressed during BUILD (P0: Schemas).**
2. ~~**Arabic Language Centralization:**~~ → **Resolved** — English is primary. spaCy/Stanza/NLTK all have excellent English support out of the box.
3. **Performance Profiling:** PLAN mentions performance profiling in P6, but no step for benchmarking stage latency, memory usage, or throughput. → **To be addressed during BUILD (P6).**
4. ~~**Configuration Management:**~~ → **Resolved** — To be defined during BUILD (P0: Schemas) as Pydantic config model.
5. **Scalability Guardrails:** PLAN mentions parallelism for Stage 3, but no step for resource management (max workers, memory limits, backpressure) to prevent exhaustion. → **To be addressed during BUILD (P5: Orchestrator).**
6. **Audit Trail:** No step for logging pipeline execution, unit inputs/outputs, or confidence scores for end-to-end auditability. → **To be addressed during BUILD (P5: Orchestrator).**

### Recommended Additions (Status: Resolved)

| # | Recommendation | Status | Resolution |
|---|---------------|--------|------------|
| 1 | **Language Lock** | ✅ Resolved | English primary. Tool stack: spaCy → Stanza → NLTK → GLiNER → ML → LLM |
| 2 | **LLM Prompt Library** | ✅ Resolved | LLM used only for reasoning/disambiguation. API priority: OpenCode → KiloCode → Cline → OpenRouter → Codex |
| 3 | **Validation Units** | ✅ Resolved | CP1-CP5 converted to mandatory ValidationUnit Processing Units between all stages |
| 4 | **Conflict Resolution Formula** | ✅ Resolved | `score = confidence × (evidence_tokens / max_tokens_in_layer)` with tiebreaker rules |
| 5 | **Inter-Stage Validation Gates** | ✅ Resolved | ValidationUnits run after each stage; pipeline fails if checks don't pass |
| 6 | **NLP Benchmark** | ⏳ Deferred | English benchmark documents added during BUILD phase (P6) |
| 7 | **Configuration Schema** | ⏳ Deferred | To be defined during BUILD (P0: Schemas) |

### Updated Recommended Additions (Remaining)

1. **LLM Prompt Template Library:** Create prompts/v1/ directory with versioned prompts for LLM fallback cases (semantic segmentation fallback, SRL fallback, conflict resolution fallback, cross-layer inference).
2. **Configuration Schema:** Define a config/pipeline.yaml schema specifying all stage configs, tool selections, and language settings, with Pydantic validation.
3. **Scalability Guardrails:** Implement resource management (max workers, memory limits, backpressure) in PipelineOrchestrator.
4. **Audit Trail:** Add structured logging for pipeline execution, unit inputs/outputs, and confidence scores.

(End of file)
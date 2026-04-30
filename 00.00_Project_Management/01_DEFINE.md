# DEFINE — Prism: Hybrid Neuro-Symbolic NLP Pipeline

## Problem Statement

**How might we** transform complex Markdown documents into rich, structured Property Graphs with entities, causal/conditional relationships, argument structures, and confidence scores — replacing opaque, single-step LLM extraction with a transparent, multi-stage, auditable pipeline?

## Current Gap

| Tool | Approach | Limitation |
|------|----------|------------|
| **ICM** | Keyword/FTS-based | Zero semantics, no relationships |
| **Graphify** | Single-step LLM extraction | Fails at synthesis, inference, argument mining |
| **Prism (proposed)** | Hybrid neuro-symbolic pipeline | Deterministic analysis + LLM reasoning + transparent multi-stage |

## Scope

- **Phase 1:** Markdown documents only (no OCR, no raw images)
- Diagrams/figures rendered as text/codes, not visual analysis

## Pipeline Architecture

```
[1] Holistic Document Tokenization     ← T0..TN (global, document-wide)
         │
         ▼
[2] Physical Topology Analyzer         ← Discover + Classify layers
         │
         ▼
[3] Semantic Topology Analyzer         ← PER physical layer (recursive)
         Topics → Paragraph → Predicate → Entity → ER → Mini-PG
         │
         ▼
[4] Aggregation Layer                  ← CROSS-LAYER (MAP-REDUCE)
         Cross-layer ER, Merge Mini-PGs, Global Property Graph
```

### Core Design Principles

1. **Separation of Logic from Interface:** Pipelines are fully independent of communication protocols (MCP/CLI).
2. **Global Token IDs First:** Holistic tokenization happens BEFORE any layer analysis — ensuring a shared, document-wide identifier space (`T0`, `T1`, ...) that all layers reference.
3. **Physical Layer Discovery:** The Physical Topology Analyzer scans the document to determine which physical layers exist — not every document has all layer types.
4. **Recursive Semantic Analysis per Layer:** Each discovered physical layer receives the SAME Semantic Topology Analysis steps — ensuring uniform processing regardless of layer type (paragraph, table, list, etc.).
5. **Semantic Units Inside Physical Layers:** A table cell may contain a "paragraph" — treated as a mini-topic within the table's semantic scope, not a standalone paragraph layer.
6. **Layer-First Entity Resolution:** Entities are resolved locally within each physical layer's semantic tree before cross-layer aggregation.
7. **Property Graph as Object:** Each physical layer produces a Mini-PG; the Aggregation phase merges them with conflict resolution.

---

## Stage 1: Holistic Document Tokenization

**Input:** Raw Markdown document (from Docling conversion of PDF/DOCX/PPTX)

**Process:**
1. Flatten the entire document into a single sequential token stream
2. Assign global sequential IDs: `T0`, `T1`, `T2`, ... (document-wide, temporal order)
3. Store raw positional metadata per token (layer unknown at this stage)

**Output:**
- Global token stream: `[(T0, "token_text"), (T1, "token_text"), ...]`
- Metadata index: token → `{char_start, char_end, source_line}`

**Why First:** The global token IDs serve as the shared reference space that ALL subsequent physical and semantic layers point back to. Without this, cross-layer linking would require reconciliation of separate ID schemes.

---

## Stage 2: Physical Topology Analyzer

**Input:** Structured Markdown + global token stream

**Process:**
1. Parse Markdown AST
2. Scan and classify — which physical layer types exist in this document?
3. Map each discovered component back to global token IDs

**Physical Layer Types:**

| Layer Type | Description | Examples |
|------------|-------------|----------|
| **Paragraph** | Homogeneous text blocks | Body paragraphs, abstracts, summaries |
| **List** | Sequential or bullet items | Bullet points, numbered steps, enumerations |
| **Tabular Data** | Row × column structured data | Data tables, comparison matrices, timelines |
| **Diagram** | Text-based diagrams/codes | Flowcharts in ASCII, Mermaid, architecture diagrams |
| **Heading/Section** | Section boundaries | h1-h6, numbered sections |
| **Code Block** | Code snippets, commands | Language snippets, CLI commands, configs |
| **Footnote/Annotation** | Footnotes, endnotes, margin notes | `[^1]`, `> Note:` blocks |
| **Metadata** | Document-level metadata | Title, author, date, version, keywords |
| **Figure/Image** | Image references (text description only) | `![caption](path)` |
| **Blockquote** | Quoted text, callouts | `> quoted text`, warnings, tips |

**Output:**

```
PhysicalTopologyReport:
  single_layer_document: bool          ← True if only paragraphs exist
  discovered_layers: dict:
    paragraphs:    [P1, P2, P3, ...]   ← Each P = {component_id, global_tokens: [T14..T89]}
    lists:         [L1, L2, ...]        ← Each L = {component_id, items: [...]}
    tables:        [TBL1, TBL2, ...]    ← Each TBL = {component_id, cells: {row,col → tokens}}
    headings:      [H1, H2, ...]        ← Each H = {level, text, tokens}
    code_blocks:   [C1, C2, ...]
    footnotes:     [FN1, FN2, ...]
    metadata:      [MD1]
    figures:       [F1, F2, ...]
    blockquotes:   [BQ1, BQ2, ...]
    diagrams:      [D1, D2, ...]
```

**Key Concept:** Each physical component is a **container** that maps to a subset of the global token stream. A table cell may contain tokens that semantically form a "paragraph" — this is handled at Stage 3, not here.

---

## Stage 3: Semantic Topology Analyzer (per physical layer, recursive)

**Applied to EACH physical layer discovered in Stage 2.** Same steps, same structure — regardless of whether the layer is a paragraph, table, list, or code block.

### Semantic Tree Structure (per physical layer)

```
[Physical Layer Container: e.g., "TABLE_1"]
    │
    ├── Topic                          ← ما موضوع هذه الطبقة؟
    │     ├── Global topic             ← Derived from heading/section context
    │     └── Mini-topics              ← Internal semantic units
    │           (e.g., each table cell = a mini-topic in table scope)
    │           (e.g., each list item = a mini-topic in list scope)
    │
    ├── Paragraph                      ← الوحدات الفقرية السيمانتيكية
    │     (semantic paragraph units — may not align with physical boundaries)
    │
    ├── Sentence → Predicate           ← استخراج الإطار الإسنادي
    │     (1 sentence = 0..N predicates)
    │
    ├── Entity                         ← استخراج الكيانات (نطاق محلي)
    │
    ├── Entity Resolution              ← حل الغموض داخل نطاق هذه الطبقة
    │
    └── Entity Property Graph          ← Mini-PG الناتج من هذه الطبقة
```

### Processing Steps (per layer)

| Step | Operation | Output |
|------|-----------|--------|
| **1. Topic Detection** | Identify the layer's topic (from heading if available, else statistical) | `topic_label`, `mini_topics[]` |
| **2. Paragraph** | Detect semantic paragraph units within the layer | Semantic units with token spans |
| **3. Predicate Extraction** | SRL on sentences → predicate frames | `[(predicate, agent, patient, ...)]` |
| **4. Entity Extraction** | NER within layer scope | Raw entities with token spans |
| **5. Entity Resolution** | Resolve entity ambiguity within layer scope | Resolved entities (merged duplicates) |
| **6. Mini-PG Construction** | Build Property Graph from entities + relationships + predicates | `LayerMiniPG` object |

### Recursive Behavior

If a physical layer contains **sub-components** that are themselves physical layer types (e.g., a table cell containing a list), the Semantic Analyzer:
1. Creates a **sub-tree** for the sub-component
2. Processes it through the same 6 steps
3. Attaches the sub-tree's Mini-PG as a child of the parent's Mini-PG
4. The parent Mini-PG references the child via `child_pg_id`

### Mini-PG Output Schema (per physical layer)

```python
class MiniPG:
    layer_id: str                      # e.g., "table:tbl1", "para:p3"
    parent_layer_id: str | None        # If this is a sub-component
    topic_label: str                   # Detected topic for this layer
    mini_topics: list[MiniTopic]       # Internal semantic units
    entities: dict[str, Entity]        # Resolved entities (local scope)
    predicates: list[PredicateFrame]   # Extracted predicates
    relationships: list[Relationship]  # Edges between entities
    child_pgs: list[str]               # IDs of sub-component Mini-PGs
```

---

## Stage 4: Aggregation Layer (Cross-Layer MAP-REDUCE)

**Input:** All Mini-PGs from Stage 3 (from all physical layers)

**Process:**

### 4.1 Cross-Layer Entity Resolution
- Same entity mentioned in multiple physical layers (e.g., "المشروع" in `para:p3` AND `table:tbl1`)
- Merge into single global entity with `mentions` spanning all layers

### 4.2 Merge All Mini-PGs → Global Property Graph
- Union of all entities (post cross-layer ER)
- Union of all predicates
- Union of all relationships

### 4.3 Conflict Resolution
- Contradictory relationships from different layers (e.g., Layer A: "A causes B", Layer B: "B causes A")
- **Strategy:** Weighted voting by confidence. Each relationship carries `confidence` + `evidence_tokens`. Select highest confidence; record alternatives as `alternative_hypothesis`.

### 4.4 Cross-Topological Linking
- **Causal chains** spanning multiple components (premise in list → consequence in paragraph)
- **Argument structures** (evidence in table → conclusion in paragraph)
- **Conditional relationships** across layer boundaries

### 4.5 Topic Clustering
- Cluster semantically related paragraphs across different sections/layers
- Group into topic clusters (not limited to physical section boundaries)

### 4.6 Confidence Scoring
- Assign confidence to every entity, relationship, and inference in the global graph

**Output:**

```python
class GlobalPG:
    entities: dict[str, Entity]           # Merged entities (cross-layer)
    relationships: list[Relationship]     # Merged relationships (conflict-resolved)
    predicates: list[PredicateFrame]      # All predicates from all layers
    topic_clusters: list[TopicCluster]    # Cross-layer semantic clusters
    confidence_summary: dict              # Aggregate confidence stats
    provenance: dict                      # For every node/edge: which layers produced it
```

---

## Token Addressing System

### Global Token ID

- Format: `T{n}` where `n` is the sequential position in the flattened document
- Example: `T0`, `T5`, `T142`
- **Invariant:** Same token always has same ID regardless of processing stage
- **Identity is separate from location:** `T5` is the identity; where it lives (which layer, which cell, which sentence) is metadata

### Metadata Schema (per token)

```json
{
  "token_id": "T5",
  "text": "المشروع",
  "lemma": "مشروع",
  "pos": "NOUN",
  "ner_label": "PROJECT",
  "metadata": {
    "layer_type": "PARAGRAPH",
    "component_id": "p3",
    "sentence_id": "s0",
    "phrase_id": "np1",
    "char_start": 142,
    "char_end": 149,
    "bounding_box": null,
    "document_section": "3.1 Methodology"
  }
}
```

---

## Property Graph Data Model

### Entity (Node)

```python
class Entity:
    id: str                    # Unique entity ID (e.g., "E_PROJECT_001")
    label: str                 # Entity type (PROJECT, PERSON, ORG, etc.)
    mentions: list[str]        # Global token IDs referencing this entity
    attributes: dict           # Resolved attributes (name, date, etc.)
    confidence: float          # Entity resolution confidence [0.0, 1.0]
    layers: list[str]          # Physical layer IDs where this entity appears
    source_layer: str          # The physical layer where it was first detected
```

### Relationship (Edge)

```python
class Relationship:
    id: str                    # Unique edge ID
    source: str                # Source entity ID
    target: str                # Target entity ID
    relation_type: str         # (CAUSES, DEPENDS_ON, PART_OF, etc.)
    predicate: str             # Source predicate text
    confidence: float          # Relationship confidence [0.0, 1.0]
    layers: list[str]          # Physical layers where this relationship was detected
    evidence: list[str]        # Global token IDs supporting this relationship
    alternative_hypotheses: list  # Conflicting relationships (if any)
```

### Predicate Frame

```python
class PredicateFrame:
    predicate: str             # Main verb/relation
    agent: str | None          # Who/what performs
    patient: str | None        # Who/what receives
    instrument: str | None     # By what means
    location: str | None       # Where
    time: str | None           # When
    source_tokens: list[str]   # Global token IDs that formed this predicate
    source_layer: str          # Physical layer ID
```

---

## Integration Layer (Future Phases)

- **MCP Server:** Expose pipeline stages and query graph via MCP protocol
- **CLI Tool:** Command-line interface for running pipeline on documents
- **ICM Adapter:** Export graph data in ICM-compatible format
- **Graphify Adapter:** Feed enriched graph into Graphify for visualization

## Success Criteria

- [ ] Pipeline processes a multi-layer Markdown document end-to-end
- [ ] Holistic tokenization assigns global IDs before any layer analysis
- [ ] Physical Topology Analyzer correctly discovers and classifies all layer types present
- [ ] Each physical layer receives identical Semantic Topology Analysis (6 steps)
- [ ] Mini-PGs are produced per physical layer with recursive sub-component support
- [ ] Cross-layer Entity Resolution merges entities from different physical layers
- [ ] Mini-PGs merge into a coherent Global Property Graph with conflict resolution
- [ ] Cross-topological linking detects causal/argument chains across layers
- [ ] Confidence scores are assigned to all entities, relationships, and inferences
- [ ] Pipeline is fully decoupled from MCP/CLI interfaces

## Open Questions

1. **LLM Integration Point:** At which stage(s) do we invoke LLM reasoning? (Cross-layer inference? Confidence calibration? Topic clustering?)
2. **Scalability Target:** What document size should we optimize for? (10 pages? 100 pages? 1000+ pages?)
3. **Language Support:** Arabic only initially? Multi-language from the start?
4. **Conflict Resolution Confidence Formula:** Exact formula for weighted voting when layers produce contradictory relationships
5. **Topic Clustering Algorithm:** How to detect semantic similarity across layers — embeddings? lexical overlap? both?

"""Stage 2 — Physical Topology Analyzer.

Pipeline Abstraction (Phase 1-3):
- 6 ProcessingUnits with unified `process(input, config)` interface
- Input/Output wrapper Pydantic models for type safety
- typing.Protocol definitions for structural subtyping
- Stage2Pipeline orchestrator with validation gates
- Stage2PipelineConfig for swappable unit implementations

LangGraph Subgraph (Phase 5):
- Stage2GraphState for progressive state accumulation
- Node creators (processing + aggregation)
- Conditional edges for validation routing
- build_stage2_subgraph() for compiled StateGraph
- GraphConfig with SQLite checkpointing support

Aggregation (Phase 4):
- 9 aggregation units (7 rules + 2 NLP-enhanced)
- TokenRangeAggregator: Bidirectional Token <-> Component mapping
- TableAggregator: Table matrix parsing from AST
- ListAggregator: List matrix parsing with nesting
- CodeBlockAggregator: Code block line-by-line analysis
- HeadingSequenceAnalyzer: Heading validation + spaCy POS
- IndentationAnalyzer: Heading indentation pattern analysis
- NestingValidator: Hierarchy validation against NestingMatrix
- DetectorCorrelation: Cross-detector correlation + e5-small
- TopologyAssembler: Final Stage2Output assembly
"""

from prism.stage2.parser import MarkdownItParser
from prism.stage2.classifier import LayerClassifier
from prism.stage2.hierarchy import HierarchyBuilder
from prism.stage2.mapper import ComponentMapper
from prism.stage2.token_span import TokenSpanMapper
from prism.stage2.topology import TopologyBuilder
from prism.stage2.pipeline import PipelineStepError, Stage2Pipeline
from prism.stage2.pipeline_config import Stage2PipelineConfig
from prism.stage2.pipeline_models import (
    ClassifierInput,
    HierarchyInput,
    MapperInput,
    MapperOutput,
    ParserOutput,
    TokenSpanInput,
    TokenSpanOutput,
    TopologyInput,
)
from prism.stage2.protocols import (
    IClassifier,
    ICodeBlockAggregator,
    IComponentMapper,
    IDetectorCorrelator,
    IHeadingSequenceAnalyzer,
    IHierarchyBuilder,
    IIndentationAnalyzer,
    IListAggregator,
    INestingValidator,
    IParser,
    ITableAggregator,
    ITokenRangeAggregator,
    ITokenSpanMapper,
    ITopologyAssembler,
    ITopologyBuilder,
)

# Optional: LangGraph subgraph (requires langgraph package)
try:
    from prism.stage2.graph import (
        GraphConfig,
        Stage2GraphState,
        build_stage2_subgraph,
    )
    _HAS_LANGGRAPH = True
except ImportError:
    _HAS_LANGGRAPH = False
    build_stage2_subgraph = None  # type: ignore[misc]
    Stage2GraphState = None  # type: ignore[misc]
    GraphConfig = None  # type: ignore[misc]

__all__ = [
    # Processing units
    "MarkdownItParser",
    "LayerClassifier",
    "HierarchyBuilder",
    "ComponentMapper",
    "TokenSpanMapper",
    "TopologyBuilder",
    # Pipeline
    "Stage2Pipeline",
    "Stage2PipelineConfig",
    "PipelineStepError",
    # Wrapper models
    "ParserOutput",
    "ClassifierInput",
    "HierarchyInput",
    "MapperInput",
    "MapperOutput",
    "TokenSpanInput",
    "TokenSpanOutput",
    "TopologyInput",
    # Protocols
    "IParser",
    "IClassifier",
    "IHierarchyBuilder",
    "IComponentMapper",
    "ITokenSpanMapper",
    "ITopologyBuilder",
    # Aggregation Protocols
    "IDetectorCorrelator",
    "ITokenRangeAggregator",
    "ITableAggregator",
    "IListAggregator",
    "ICodeBlockAggregator",
    "IHeadingSequenceAnalyzer",
    "IIndentationAnalyzer",
    "INestingValidator",
    "ITopologyAssembler",
    # LangGraph subgraph (optional)
    "build_stage2_subgraph",
    "Stage2GraphState",
    "GraphConfig",
    "_HAS_LANGGRAPH",
]

"""LangGraph subgraph for Stage 2 Physical Topology.

This package wraps Stage2Pipeline into a LangGraph StateGraph,
providing:
- Checkpointing (SQLite) between each step
- Conditional edges (validation pass/fail → next step or halt)
- Fallback routing (swappable implementations via PipelineConfig)
- Progressive state accumulation (Stage2GraphState)

Exports:
- build_stage2_subgraph(config) → CompiledStateGraph
- Stage2GraphState (Pydantic state model)
- GraphConfig (extends Stage2PipelineConfig)
"""

from prism.stage2.graph.builder import build_stage2_subgraph
from prism.stage2.graph.config import GraphConfig
from prism.stage2.graph.state import Stage2GraphState

__all__ = [
    "build_stage2_subgraph",
    "Stage2GraphState",
    "GraphConfig",
]

"""LangGraph subgraph builder for Stage 2.

Assembles the complete Stage 2 StateGraph:
1. Instantiate all ProcessingUnits from PipelineConfig
2. Create node functions (processing + validation + aggregation)
3. Add nodes to StateGraph
4. Wire sequential edges between steps
5. Add conditional edges (validation routing)
6. Compile and return
"""

from langgraph.graph import END, StateGraph

from prism.stage2.pipeline_config import Stage2PipelineConfig

from .edges import (
    route_after_aggregate_codeblocks,
    route_after_aggregate_lists,
    route_after_aggregate_tables,
    route_after_aggregate_tokens,
    route_after_analyze_headings,
    route_after_analyze_indentation,
    route_after_assemble_topology,
    route_after_validate_classifier,
    route_after_validate_correlate,
    route_after_validate_hierarchy,
    route_after_validate_mapper,
    route_after_validate_nesting,
    route_after_validate_parser,
    route_after_validate_tokens,
    route_after_validate_topology,
)
from .nodes import (
    create_assembler_node,
    create_classify_node,
    create_codeblock_node,
    create_correlate_node,
    create_heading_sequence_node,
    create_hierarchy_node,
    create_indentation_node,
    create_list_node,
    create_mapper_node,
    create_nesting_node,
    create_parse_node,
    create_table_node,
    create_token_range_node,
    create_token_span_node,
    create_topology_node,
)
from .state import Stage2GraphState


def build_stage2_subgraph(
    config: Stage2PipelineConfig | None = None,
):
    """Build the Stage 2 LangGraph subgraph with aggregation steps."""
    pipeline_config = config or Stage2PipelineConfig()

    # Instantiate all units
    parser = pipeline_config.parser()
    classifier = pipeline_config.classifier()
    correlator = pipeline_config.detector_correlator()
    hierarchy_builder = pipeline_config.hierarchy_builder()
    component_mapper = pipeline_config.component_mapper()
    token_span_mapper = pipeline_config.token_span_mapper()
    token_range_agg = pipeline_config.token_range_aggregator()
    table_agg = pipeline_config.table_aggregator()
    list_agg = pipeline_config.list_aggregator()
    codeblock_agg = pipeline_config.codeblock_aggregator()
    heading_analyzer = pipeline_config.heading_sequence_analyzer()
    indentation_analyzer = pipeline_config.indentation_analyzer()
    nesting_validator = pipeline_config.nesting_validator()
    topology_builder = pipeline_config.topology_builder()
    assembler = pipeline_config.topology_assembler()

    # Create state graph
    graph = StateGraph(Stage2GraphState)

    # === Add processing nodes ===
    graph.add_node("parse", create_parse_node(parser))
    graph.add_node("classify", create_classify_node(classifier))
    graph.add_node("correlate", create_correlate_node(correlator))
    graph.add_node("build_hierarchy", create_hierarchy_node(hierarchy_builder))
    graph.add_node("map_components", create_mapper_node(component_mapper))
    graph.add_node("map_tokens", create_token_span_node(token_span_mapper))

    # Aggregation nodes
    graph.add_node("aggregate_tokens", create_token_range_node(token_range_agg))
    graph.add_node("aggregate_tables", create_table_node(table_agg))
    graph.add_node("aggregate_lists", create_list_node(list_agg))
    graph.add_node("aggregate_codeblocks", create_codeblock_node(codeblock_agg))
    graph.add_node("analyze_headings", create_heading_sequence_node(heading_analyzer))
    graph.add_node("analyze_indentation", create_indentation_node(indentation_analyzer))
    graph.add_node("validate_nesting", create_nesting_node(nesting_validator))
    graph.add_node("build_topology", create_topology_node(topology_builder))
    graph.add_node("assemble_topology", create_assembler_node(assembler))
    graph.add_node("end_node", lambda state: {"current_step": "complete"})

    # === Add validation nodes ===
    graph.add_node(
        "validate_parser",
        lambda state: _validate_output(
            state, "parser", parser.validate_output, state.nodes,
        ),
    )
    graph.add_node(
        "validate_classifier",
        lambda state: _validate_output(
            state, "classifier", classifier.validate_output, state.report,
        ),
    )
    graph.add_node(
        "validate_correlate",
        lambda state: _validate_output(
            state, "correlate", correlator.validate_output, state.correlated_report,
        ),
    )
    graph.add_node(
        "validate_hierarchy",
        lambda state: _validate_output(
            state, "hierarchy", hierarchy_builder.validate_output, state.tree,
        ),
    )
    graph.add_node(
        "validate_mapper",
        lambda state: _validate_output(
            state, "mapper", component_mapper.validate_output,
            _make_mapper_output(state.components),
        ),
    )
    graph.add_node(
        "validate_tokens",
        lambda state: _validate_output(
            state, "tokens", token_span_mapper.validate_output,
            _make_token_span_output(state.token_mapping),
        ),
    )
    graph.add_node(
        "validate_topology",
        lambda state: _validate_output(
            state, "topology", topology_builder.validate_output, state.stage2_output,
        ),
    )

    # === Add halt node ===
    graph.add_node("halt", lambda state: {"current_step": "halted"})

    # === Add sequential edges ===
    graph.set_entry_point("parse")
    graph.add_edge("parse", "validate_parser")
    graph.add_edge("classify", "validate_classifier")
    graph.add_edge("correlate", "validate_correlate")
    graph.add_edge("build_hierarchy", "validate_hierarchy")
    graph.add_edge("map_components", "validate_mapper")
    graph.add_edge("map_tokens", "validate_tokens")
    graph.add_edge("aggregate_tokens", "aggregate_tables")
    graph.add_edge("aggregate_tables", "aggregate_lists")
    graph.add_edge("aggregate_lists", "aggregate_codeblocks")
    graph.add_edge("aggregate_codeblocks", "analyze_headings")
    graph.add_edge("analyze_headings", "analyze_indentation")
    graph.add_edge("analyze_indentation", "validate_nesting")
    graph.add_edge("build_topology", "validate_topology")
    graph.add_edge("assemble_topology", "end_node")

    # === Add conditional edges ===
    graph.add_conditional_edges(
        "validate_parser",
        route_after_validate_parser,
        {"classify": "classify", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_classifier",
        route_after_validate_classifier,
        {"correlate": "correlate", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_correlate",
        route_after_validate_correlate,
        {"build_hierarchy": "build_hierarchy", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_hierarchy",
        route_after_validate_hierarchy,
        {"map_components": "map_components", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_mapper",
        route_after_validate_mapper,
        {"map_tokens": "map_tokens", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_tokens",
        route_after_validate_tokens,
        {"aggregate_tokens": "aggregate_tokens", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "aggregate_tokens",
        route_after_aggregate_tokens,
        {"aggregate_tables": "aggregate_tables", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "aggregate_tables",
        route_after_aggregate_tables,
        {"aggregate_lists": "aggregate_lists", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "aggregate_lists",
        route_after_aggregate_lists,
        {"aggregate_codeblocks": "aggregate_codeblocks", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "aggregate_codeblocks",
        route_after_aggregate_codeblocks,
        {"analyze_headings": "analyze_headings", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "analyze_headings",
        route_after_analyze_headings,
        {"analyze_indentation": "analyze_indentation", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "analyze_indentation",
        route_after_analyze_indentation,
        {"validate_nesting": "validate_nesting", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_nesting",
        route_after_validate_nesting,
        {"build_topology": "build_topology", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_topology",
        route_after_validate_topology,
        {"assemble_topology": "assemble_topology", "halt": "halt"},
    )

    graph.add_conditional_edges(
        "assemble_topology",
        route_after_assemble_topology,
        {"end": END, "halt": "halt"},
    )

    return graph.compile()


def _validate_output(
    state: Stage2GraphState,
    step_name: str,
    validate_fn,
    output_data,
) -> dict:
    """Validate output and return state update."""
    if output_data is None:
        return {
            "errors": state.errors + [f"{step_name} output is None"],
            "current_step": f"validate_{step_name}_failed",
        }
    valid, msg = validate_fn(output_data)
    if not valid:
        return {
            "errors": state.errors + [f"{step_name} output invalid: {msg}"],
            "current_step": f"validate_{step_name}_failed",
        }
    return {"current_step": f"validate_{step_name}_passed"}


def _make_mapper_output(components):
    from prism.stage2.pipeline_models import MapperOutput
    return MapperOutput(components=components)


def _make_token_span_output(token_mapping):
    from prism.stage2.pipeline_models import TokenSpanOutput
    return TokenSpanOutput(component_to_tokens=token_mapping)

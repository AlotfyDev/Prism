"""LangGraph node wrappers for Stage 2 subgraph.

Each function wraps a ProcessingUnit (Protocol-compliant) into a LangGraph node:
  state: Stage2GraphState -> dict[str, Any] (state update)

Node types:
- Processing nodes: call unit.process() and return state update
- Aggregation nodes: call unit.aggregate() and return state update
"""

from typing import Any, Callable

from prism.schemas.token import Stage1Output
from prism.stage2.aggregation.aggregation_models import AssemblyInput
from prism.stage2.pipeline_models import (
    ClassifierInput,
    HierarchyInput,
    MapperInput,
    TokenSpanInput,
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

from .state import Stage2GraphState


def create_parse_node(parser: IParser) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node that wraps an IParser implementation."""

    def parse_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = Stage1Output(source_text=state.source_text)
        nodes = parser.process(input_data)
        return {
            "nodes": nodes,
            "current_step": "parsed",
        }

    return parse_node


def create_classify_node(
    classifier: IClassifier,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node that wraps an IClassifier implementation."""

    def classify_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = ClassifierInput(
            nodes=state.nodes,
            source_text=state.source_text,
        )
        report = classifier.process(input_data)
        return {
            "report": report,
            "current_step": "classified",
        }

    return classify_node


def create_correlate_node(
    correlator: IDetectorCorrelator,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for cross-detector correlation."""

    def correlate_node(state: Stage2GraphState) -> dict[str, Any]:
        correlated = correlator.aggregate(state.report)
        return {
            "correlated_report": correlated,
            "current_step": "correlated",
        }

    return correlate_node


def create_hierarchy_node(
    builder: IHierarchyBuilder,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node that wraps an IHierarchyBuilder implementation."""

    def hierarchy_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = HierarchyInput(report=state.report)
        tree = builder.process(input_data)
        return {
            "tree": tree,
            "current_step": "hierarchy_built",
        }

    return hierarchy_node


def create_mapper_node(
    mapper: IComponentMapper,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node that wraps an IComponentMapper implementation."""

    def mapper_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = MapperInput(tree=state.tree)
        output = mapper.process(input_data)
        return {
            "components": output.components,
            "current_step": "components_mapped",
        }

    return mapper_node


def create_token_span_node(
    span_mapper: ITokenSpanMapper,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node that wraps an ITokenSpanMapper implementation."""

    def token_span_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = TokenSpanInput(
            components=state.components,
            stage1_output=Stage1Output(source_text=state.source_text),
        )
        output = span_mapper.process(input_data)
        return {
            "token_mapping": output.component_to_tokens,
            "current_step": "tokens_mapped",
        }

    return token_span_node


# Aggregation nodes

def create_token_range_node(
    aggregator: ITokenRangeAggregator,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for TokenRangeAggregator."""

    def token_range_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = {
            "components": state.components,
            "stage1_output": Stage1Output(source_text=state.source_text),
        }
        token_range_index = aggregator.aggregate(input_data)
        return {
            "token_range_index": token_range_index,
            "current_step": "token_ranges_aggregated",
        }

    return token_range_node


def create_table_node(
    aggregator: ITableAggregator,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for TableAggregator."""

    def table_node(state: Stage2GraphState) -> dict[str, Any]:
        table_indices_list = aggregator.aggregate(state.nodes)
        table_indices = {ti.component_id: ti for ti in table_indices_list}
        return {
            "table_indices": table_indices,
            "current_step": "tables_aggregated",
        }

    return table_node


def create_list_node(
    aggregator: IListAggregator,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for ListAggregator."""

    def list_node(state: Stage2GraphState) -> dict[str, Any]:
        list_indices_list = aggregator.aggregate(state.nodes)
        list_indices = {li.component_id: li for li in list_indices_list}
        return {
            "list_indices": list_indices,
            "current_step": "lists_aggregated",
        }

    return list_node


def create_codeblock_node(
    aggregator: ICodeBlockAggregator,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for CodeBlockAggregator."""

    def codeblock_node(state: Stage2GraphState) -> dict[str, Any]:
        codeblock_indices_list = aggregator.aggregate(state.nodes)
        codeblock_indices = {cbi.component_id: cbi for cbi in codeblock_indices_list}
        return {
            "codeblock_indices": codeblock_indices,
            "current_step": "codeblocks_aggregated",
        }

    return codeblock_node


def create_heading_sequence_node(
    analyzer: IHeadingSequenceAnalyzer,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for HeadingSequenceAnalyzer."""

    def heading_sequence_node(state: Stage2GraphState) -> dict[str, Any]:
        heading_components = [
            c for c in state.components if c.layer_type.value == "heading"
        ]
        heading_sequence = analyzer.aggregate(heading_components)
        return {
            "heading_sequence": heading_sequence,
            "current_step": "headings_analyzed",
        }

    return heading_sequence_node


def create_indentation_node(
    analyzer: IIndentationAnalyzer,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for IndentationAnalyzer."""

    def indentation_node(state: Stage2GraphState) -> dict[str, Any]:
        heading_components = [
            c for c in state.components if c.layer_type.value == "heading"
        ]
        indentation = analyzer.aggregate(heading_components)
        return {
            "indentation_pattern": indentation,
            "current_step": "indentation_analyzed",
        }

    return indentation_node


def create_nesting_node(
    validator: INestingValidator,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for NestingValidator."""

    def nesting_node(state: Stage2GraphState) -> dict[str, Any]:
        component_dict = {c.component_id: c for c in state.components}
        nesting_validation = validator.aggregate(component_dict)
        return {
            "nesting_validation": nesting_validation,
            "current_step": "nesting_validated",
        }

    return nesting_node


def create_topology_node(
    builder: ITopologyBuilder,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node that wraps an ITopologyBuilder implementation."""

    def topology_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = TopologyInput(
            components=state.components,
            token_mapping=state.token_mapping,
        )
        output = builder.process(input_data)
        return {
            "stage2_output": output,
            "current_step": "topology_built",
        }

    return topology_node


def create_assembler_node(
    assembler: ITopologyAssembler,
) -> Callable[[Stage2GraphState], dict[str, Any]]:
    """Creates a LangGraph node for TopologyAssembler."""

    def assembler_node(state: Stage2GraphState) -> dict[str, Any]:
        component_dict = {c.component_id: c for c in state.components}
        assembly_input = AssemblyInput(
            components=component_dict,
            heading_sequence=state.heading_sequence,
            correlations=state.correlated_report,
            token_range_index=state.token_range_index,
            nesting_validation=state.nesting_validation,
            indentation_pattern=state.indentation_pattern,
        )
        final_output = assembler.aggregate(assembly_input)
        return {
            "stage2_output": final_output,
            "current_step": "topology_assembled",
        }

    return assembler_node

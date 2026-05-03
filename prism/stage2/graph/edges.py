"""Conditional edges for Stage 2 subgraph.

Routing functions that determine the next node based on state:
- route_after_validate_*: pass → next step | fail → halt
- route_fallback: pass → next step | fail → halt
"""

from .state import Stage2GraphState


def route_after_validate_parser(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "classify"


def route_after_validate_classifier(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "correlate"


def route_after_validate_correlate(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "build_hierarchy"


def route_after_validate_hierarchy(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "map_components"


def route_after_validate_mapper(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "map_tokens"


def route_after_validate_tokens(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "aggregate_tokens"


# Aggregation routing

def route_after_aggregate_tokens(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "aggregate_tables"


def route_after_aggregate_tables(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "aggregate_lists"


def route_after_aggregate_lists(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "aggregate_codeblocks"


def route_after_aggregate_codeblocks(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "analyze_headings"


def route_after_analyze_headings(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "analyze_indentation"


def route_after_analyze_indentation(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "validate_nesting"


def route_after_validate_nesting(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "build_topology"


def route_after_validate_topology(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "assemble_topology"


def route_after_assemble_topology(state: Stage2GraphState) -> str:
    return "end"


def route_fallback(
    state: Stage2GraphState,
    step_name: str,
    available_fallbacks: list[str],
) -> str:
    """Route to next fallback implementation if current step failed."""
    if not state.has_error():
        return f"validate_{step_name}"

    if state.retry_count.get(step_name, 0) >= len(available_fallbacks):
        return "halt"

    return available_fallbacks[state.retry_count.get(step_name, 0)]

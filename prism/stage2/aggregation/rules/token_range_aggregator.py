"""Token Range Aggregator — Bidirectional Token <-> Component mapping.

Builds:
1. Forward: component_id -> list of token IDs (existing)
2. Reverse: token_id -> component_id (NEW)
3. Gap detection: tokens not assigned to any component
4. Coverage statistics

Reliability: 100% — pure math, deterministic binary search.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Any

from prism.schemas.physical import PhysicalComponent
from prism.schemas.token import Stage1Output
from prism.stage2.aggregation.aggregation_models import TokenRangeIndex


class TokenRangeAggregator:
    """Builds bidirectional Token <-> Component index."""

    def aggregate(self, input_data: dict[str, Any]) -> TokenRangeIndex:
        components: list[PhysicalComponent] = input_data["components"]
        stage1_output: Stage1Output = input_data["stage1_output"]
        return self._build_index(components, stage1_output)

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str]:
        if "components" not in input_data:
            return False, "Missing 'components' in input"
        if "stage1_output" not in input_data:
            return False, "Missing 'stage1_output' in input"
        if not isinstance(input_data["components"], list):
            return False, "'components' must be a list"
        if not isinstance(input_data["stage1_output"], Stage1Output):
            return False, "'stage1_output' must be a Stage1Output"
        return True, ""

    def validate_output(self, output_data: TokenRangeIndex) -> tuple[bool, str]:
        if output_data.total_tokens < 0:
            return False, "total_tokens must be >= 0"
        if output_data.assigned_tokens + len(output_data.unassigned_tokens) != output_data.total_tokens:
            return False, "assigned + unassigned must equal total"
        return True, ""

    def name(self) -> str:
        return "TokenRangeAggregator"

    @property
    def tier(self) -> str:
        return "rules"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _build_index(
        self,
        components: list[PhysicalComponent],
        stage1_output: Stage1Output,
    ) -> TokenRangeIndex:
        tokens = stage1_output.tokens
        metadata = stage1_output.metadata
        total_tokens = len(tokens)

        # Build sorted list of (char_start, char_end, token_id)
        token_positions = []
        for tid, meta in metadata.items():
            token_positions.append((meta.char_start, meta.char_end, tid))
        token_positions.sort(key=lambda x: x[0])

        # Build sorted component ranges
        sorted_components = sorted(components, key=lambda c: c.char_start)
        comp_starts = [c.char_start for c in sorted_components]

        # Forward: component -> tokens
        component_to_tokens: dict[str, list[str]] = {}
        for comp in sorted_components:
            token_ids = self._find_tokens_in_range(
                token_positions, comp.char_start, comp.char_end
            )
            component_to_tokens[comp.component_id] = token_ids

        # Reverse: token -> component
        token_to_component: dict[str, str] = {}
        assigned_count = 0

        for _, _, tid in token_positions:
            meta = metadata[tid]
            component_id = self._find_containing_component(
                sorted_components, comp_starts, meta.char_start
            )
            if component_id is not None:
                token_to_component[tid] = component_id
                assigned_count += 1

        # Unassigned tokens
        assigned_token_ids = set(token_to_component.keys())
        all_token_ids = set(tokens.keys())
        unassigned = sorted(all_token_ids - assigned_token_ids)

        coverage_pct = (assigned_count / total_tokens * 100) if total_tokens > 0 else 100.0

        return TokenRangeIndex(
            component_to_tokens=component_to_tokens,
            token_to_component=token_to_component,
            unassigned_tokens=unassigned,
            coverage_pct=round(coverage_pct, 2),
            total_tokens=total_tokens,
            assigned_tokens=assigned_count,
        )

    def _find_tokens_in_range(
        self,
        token_positions: list[tuple[int, int, str]],
        char_start: int,
        char_end: int,
    ) -> list[str]:
        """Find all tokens whose char range overlaps with [char_start, char_end)."""
        starts = [tp[0] for tp in token_positions]
        start_idx = bisect_left(starts, char_start)

        result = []
        for i in range(start_idx, len(token_positions)):
            tp_start, tp_end, tid = token_positions[i]
            if tp_start >= char_end:
                break
            if tp_end > char_start:
                result.append(tid)
        return result

    def _find_containing_component(
        self,
        sorted_components: list[PhysicalComponent],
        comp_starts: list[int],
        token_char_start: int,
    ) -> str | None:
        """Find the component that contains the given token position."""
        idx = bisect_right(comp_starts, token_char_start) - 1

        candidates = []
        for i in range(idx, -1, -1):
            comp = sorted_components[i]
            if comp.char_start <= token_char_start < comp.char_end:
                candidates.append(comp)
            elif comp.char_start > token_char_start:
                break

        if not candidates:
            return None

        smallest = min(candidates, key=lambda c: c.char_length)
        return smallest.component_id

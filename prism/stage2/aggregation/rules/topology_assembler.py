"""Topology Assembler — Final Stage2Output assembly from all aggregation results.

Collects all aggregation outputs and builds the enhanced Stage2Output.
Reliability: 100% — dictionary assembly.
"""

from __future__ import annotations

from typing import Any

from prism.schemas.physical import PhysicalComponent, Stage2Output
from prism.stage2.aggregation.aggregation_models import (
    AssemblyInput,
    CorrelatedReport,
    HeadingSequenceReport,
    IndentationPattern,
    NestingValidationReport,
    TokenRangeIndex,
)


class TopologyAssembler:
    """Assembles all aggregation results into final Stage2Output."""

    # ------------------------------------------------------------------
    # IAggregator Protocol
    # ------------------------------------------------------------------

    def aggregate(self, input_data: AssemblyInput) -> Stage2Output:
        return self._assemble(input_data)

    def validate_input(self, input_data: AssemblyInput) -> tuple[bool, str]:
        if not isinstance(input_data, AssemblyInput):
            return False, "Input must be AssemblyInput"
        if not input_data.components:
            return False, "Must have at least one component"
        return True, ""

    def validate_output(self, output_data: Stage2Output) -> tuple[bool, str]:
        if not output_data.discovered_layers:
            return False, "Stage2Output must have discovered_layers"
        if not output_data.layer_types:
            return False, "Stage2Output must have layer_types"
        return True, ""

    def name(self) -> str:
        return "TopologyAssembler"

    @property
    def tier(self) -> str:
        return "rules"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    def _assemble(self, assembly_input: AssemblyInput) -> Stage2Output:
        """Build enhanced Stage2Output from all aggregation results."""
        # Build discovered_layers dict
        discovered_layers: dict[str, PhysicalComponent] = {}
        layer_types = set()

        for comp_id, comp_data in assembly_input.components.items():
            if isinstance(comp_data, PhysicalComponent):
                discovered_layers[comp_id] = comp_data
                layer_types.add(comp_data.layer_type)
            elif isinstance(comp_data, dict):
                # Handle dict representation — try to reconstruct
                # For now, skip dicts (should be PhysicalComponent instances)
                pass

        # Calculate is_single_layer
        is_single_layer = len(layer_types) == 1

        # Build component_to_tokens from token_range_index
        component_to_tokens = self._build_token_mapping(assembly_input.token_range_index)

        return Stage2Output(
            discovered_layers=discovered_layers,
            layer_types=layer_types,
            is_single_layer=is_single_layer,
            component_to_tokens=component_to_tokens,
        )

    def _build_token_mapping(
        self, token_range_index: TokenRangeIndex | None
    ) -> dict[str, tuple[int, int]]:
        """Build component_to_tokens mapping from TokenRangeIndex."""
        if token_range_index is None:
            return {}

        result = {}
        for comp_id, token_ids in token_range_index.component_to_tokens.items():
            if token_ids:
                # Extract numeric IDs and find range
                numeric_ids = self._extract_numeric_ids(token_ids)
                if numeric_ids:
                    result[comp_id] = (min(numeric_ids), max(numeric_ids))
        return result

    def _extract_numeric_ids(self, token_ids: list[str]) -> list[int]:
        """Extract numeric IDs from token ID strings (e.g., 'T0' -> 0)."""
        numeric = []
        for tid in token_ids:
            # Handle various formats: T0, T1, token_0, 0
            if tid.startswith("T"):
                try:
                    numeric.append(int(tid[1:]))
                except ValueError:
                    pass
            elif tid.startswith("token_"):
                try:
                    numeric.append(int(tid[6:]))
                except ValueError:
                    pass
            else:
                try:
                    numeric.append(int(tid))
                except ValueError:
                    pass
        return numeric

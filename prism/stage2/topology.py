"""Stage 2.3: TopologyBuilder — assembles Stage2Output from all intermediates.

Takes components + token mapping and produces the final Stage2Output
schema with discovered_layers, layer_types, and component_to_tokens.
"""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    PhysicalComponent,
    Stage2Output,
    TopologyConfig,
)


class TopologyBuilder:
    """Assemble Stage2Output from mapped components and token spans.

    Final assembly step for Stage 2: collects all typed PhysicalComponent
    objects, computes layer type statistics, and builds the component-to-token
    mapping.

    Input:  list[PhysicalComponent] + dict[str, list[str]] + TopologyConfig
    Output: Stage2Output
    """

    @property
    def tier(self) -> str:
        return "orchestrator"

    @property
    def version(self) -> str:
        return "v1.0.0"

    def name(self) -> str:
        return "TopologyBuilder"

    def build(
        self,
        components: list[PhysicalComponent],
        token_mapping: dict[str, list[str]],
        config: Optional[TopologyConfig] = None,
    ) -> Stage2Output:
        """Assemble Stage2Output from components and token mapping.

        Args:
            components: PhysicalComponent objects from ComponentMapper.
            token_mapping: component_id -> list of token IDs from TokenSpanMapper.
            config: Optional topology config.

        Returns:
            Stage2Output with all discovered layers and mappings.
        """
        discovered: dict[str, PhysicalComponent] = {}
        component_to_tokens: dict[str, tuple[int, int]] = {}

        for comp in components:
            discovered[comp.component_id] = comp

            # Build token span from mapping
            if comp.component_id in token_mapping:
                ids = token_mapping[comp.component_id]
                if ids:
                    # Extract numeric IDs from T{n} format
                    numeric_ids = []
                    for tid in ids:
                        if tid.startswith("T"):
                            try:
                                numeric_ids.append(int(tid[1:]))
                            except ValueError:
                                pass
                    if numeric_ids:
                        component_to_tokens[comp.component_id] = (
                            min(numeric_ids),
                            max(numeric_ids),
                        )

        return Stage2Output(
            discovered_layers=discovered,
            component_to_tokens=component_to_tokens,
        )

    def validate_input(
        self,
        components: list[PhysicalComponent],
        token_mapping: dict[str, list[str]],
    ) -> tuple[bool, str]:
        """Verify inputs are non-empty."""
        if not components:
            return False, "No components to assemble"
        return True, ""

    def validate_output(
        self,
        output: Stage2Output,
    ) -> tuple[bool, str]:
        """Verify output has discovered layers."""
        if output.component_count == 0:
            return False, "Stage2Output has no discovered layers"
        return True, ""

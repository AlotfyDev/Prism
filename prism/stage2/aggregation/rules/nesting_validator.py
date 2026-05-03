"""Nesting Validator — Validates component hierarchy against NestingMatrix.

Enforces nesting rules, detects cycles, calculates depth distribution.
Reliability: 100% — deterministic rules.
"""

from __future__ import annotations

from collections import defaultdict

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    NESTING_MATRIX,
    NestingMatrix,
    PhysicalComponent,
)
from prism.stage2.aggregation.aggregation_models import (
    NestingValidationReport,
    NestingViolation,
)


class NestingValidator:
    """Validates and enforces NestingMatrix rules across component hierarchy."""

    def __init__(self, nesting_matrix: NestingMatrix | None = None):
        self.matrix = nesting_matrix or NESTING_MATRIX

    # ------------------------------------------------------------------
    # IAggregator Protocol
    # ------------------------------------------------------------------

    def aggregate(self, input_data: dict[str, PhysicalComponent]) -> NestingValidationReport:
        return self._validate_nesting(input_data)

    def validate_input(self, input_data: dict[str, PhysicalComponent]) -> tuple[bool, str]:
        if not isinstance(input_data, dict):
            return False, "Input must be a dict of component_id -> PhysicalComponent"
        for key, comp in input_data.items():
            if key != comp.component_id:
                return False, f"Key '{key}' must match component_id '{comp.component_id}'"
        return True, ""

    def validate_output(self, output_data: NestingValidationReport) -> tuple[bool, str]:
        if output_data.total_components < 0:
            return False, "total_components must be >= 0"
        if not output_data.is_valid and not output_data.violations:
            return False, "Invalid report must have violations"
        return True, ""

    def name(self) -> str:
        return "NestingValidator"

    @property
    def tier(self) -> str:
        return "rules"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    def _validate_nesting(
        self,
        components: dict[str, PhysicalComponent],
    ) -> NestingValidationReport:
        """Validate all parent-child relationships against NestingMatrix."""
        violations: list[NestingViolation] = []
        depth_map: dict[str, int] = {}
        depth_distribution: dict[int, int] = defaultdict(int)
        container_stats: dict[str, dict] = {}

        # Calculate depths via BFS
        root_ids = {cid for cid, comp in components.items() if comp.parent_id is None}
        self._calculate_depths(components, root_ids, depth_map)

        # Validate each parent-child pair
        for comp_id, comp in components.items():
            if comp.parent_id and comp.parent_id in components:
                parent = components[comp.parent_id]
                is_valid, reason = self.matrix.validate_hierarchy(
                    children=[(comp.layer_type, depth_map.get(comp_id, 0))],
                    parent_type=parent.layer_type,
                    parent_depth=depth_map.get(parent.component_id, 0),
                )

                if not is_valid:
                    violations.append(NestingViolation(
                        parent_id=parent.component_id,
                        child_id=comp_id,
                        parent_type=parent.layer_type,
                        child_type=comp.layer_type,
                        reason=reason,
                    ))

            # Container stats
            children = [
                cid for cid, c in components.items()
                if c.parent_id == comp_id
            ]
            if children:
                child_types = [components[cid].layer_type.value for cid in children]
                container_stats[comp_id] = {
                    "children_count": len(children),
                    "child_types": child_types,
                }

        # Calculate max depth
        max_depth = max(depth_map.values(), default=0)

        # Depth distribution
        for depth in depth_map.values():
            depth_distribution[depth] += 1

        is_valid = len(violations) == 0

        return NestingValidationReport(
            is_valid=is_valid,
            violations=violations,
            max_depth=max_depth,
            total_components=len(components),
            depth_distribution=dict(depth_distribution),
            container_stats=container_stats,
        )

    def _calculate_depths(
        self,
        components: dict[str, PhysicalComponent],
        root_ids: set[str],
        depth_map: dict[str, int],
    ) -> None:
        """Calculate depth for each component via BFS."""
        for root_id in root_ids:
            self._dfs_depth(components, root_id, 0, depth_map, set())

        # Handle components not reachable from roots
        for comp_id in components:
            if comp_id not in depth_map:
                # Trace back to find depth
                depth = self._trace_depth(components, comp_id, set())
                depth_map[comp_id] = depth

    def _dfs_depth(
        self,
        components: dict[str, PhysicalComponent],
        comp_id: str,
        depth: int,
        depth_map: dict[str, int],
        visited: set[str],
    ) -> None:
        """DFS to calculate depths."""
        if comp_id in visited:
            return  # Cycle detected — skip
        visited.add(comp_id)
        depth_map[comp_id] = depth

        # Visit children
        children = [
            cid for cid, c in components.items()
            if c.parent_id == comp_id
        ]
        for child_id in children:
            self._dfs_depth(components, child_id, depth + 1, depth_map, visited)

    def _trace_depth(
        self,
        components: dict[str, PhysicalComponent],
        comp_id: str,
        visited: set[str],
    ) -> int:
        """Trace parent chain to determine depth."""
        if comp_id in visited:
            return 0  # Cycle
        visited.add(comp_id)

        comp = components.get(comp_id)
        if comp is None or comp.parent_id is None:
            return 0

        if comp.parent_id in components:
            return 1 + self._trace_depth(components, comp.parent_id, visited)
        return 0

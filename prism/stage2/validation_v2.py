"""ValidationV2 — Component Integrity Gate for Stage 2.

Implements the ValidationUnit contract to verify that Stage2Output
meets all component integrity requirements before proceeding to Stage 3.

Checks:
  V2.1 — Component ID validity (format: `{layer_type}:{identifier}`)
  V2.2 — Layer type consistency (component_id prefix matches layer_type field)
  V2.3 — Token span consistency (all spans valid, no overlaps between components)
  V2.4 — Parent-child integrity (parent_ids reference existing components, no cycles)
  V2.5 — Nesting validation (parent-child relationships valid per NestingMatrix)
  V2.6 — Component-to-token mapping completeness (all components with spans mapped)

Severity:
  CRITICAL — V2.1, V2.2, V2.3, V2.4 (pipeline must halt on failure)
  WARNING  — V2.5, V2.6 (may indicate structural issues but not fatal)
"""

import re
from typing import Optional

from prism.core.validation_unit import (
    ValidationCheck,
    ValidationReport,
    ValidationSeverity,
    ValidationUnit,
)
from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    NESTING_MATRIX,
    NestingMatrix,
    PhysicalComponent,
    Stage2Output,
)


_COMPONENT_ID_RE = re.compile(r"^[a-z_]+:.+$")


class ValidationV2(ValidationUnit):
    """Component integrity validation gate for Stage 2 output."""

    def __init__(
        self,
        nesting_matrix: Optional[NestingMatrix] = None,
    ) -> None:
        self.nesting_matrix = nesting_matrix or NESTING_MATRIX

    def validate(self, data: Stage2Output) -> ValidationReport:
        if not isinstance(data, Stage2Output):
            return ValidationReport(
                stage="stage2",
                passed=False,
                checks=[
                    ValidationCheck(
                        id="V2.0",
                        name="V2.0_input_type",
                        passed=False,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Expected Stage2Output, got {type(data).__name__}",
                    )
                ],
            )

        if not data.discovered_layers:
            return ValidationReport(
                stage="stage2",
                passed=True,
                checks=[
                    ValidationCheck(
                        id="V2.empty",
                        name="V2.empty_output",
                        passed=True,
                        severity=ValidationSeverity.INFO,
                        message="Stage2Output is empty (no components discovered)",
                    )
                ],
            )

        checks: list[ValidationCheck] = []

        # V2.1: Component ID validity
        checks.append(self._check_component_id_validity(data))

        # V2.2: Layer type consistency
        checks.append(self._check_layer_type_consistency(data))

        # V2.3: Token span consistency
        checks.append(self._check_token_span_consistency(data))

        # V2.4: Parent-child integrity
        checks.append(self._check_parent_child_integrity(data))

        # V2.5: Nesting validation
        checks.append(self._check_nesting_validation(data))

        # V2.6: Component-to-token mapping completeness
        checks.append(self._check_mapping_completeness(data))

        passed = all(c.passed for c in checks)
        return ValidationReport(stage="stage2", passed=passed, checks=checks)

    def _check_component_id_validity(self, data: Stage2Output) -> ValidationCheck:
        """V2.1: All component IDs must match `{layer_type}:{identifier}` pattern."""
        invalid_ids = []

        for comp_id in data.discovered_layers:
            if not _COMPONENT_ID_RE.match(comp_id):
                invalid_ids.append(comp_id)

        if invalid_ids:
            return ValidationCheck(
                id="V2.1",
                name="V2.1_component_id_validity",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"{len(invalid_ids)} invalid component ID(s): {invalid_ids[:5]}",
                details={"invalid_ids": invalid_ids},
            )

        return ValidationCheck(
            id="V2.1",
            name="V2.1_component_id_validity",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message=f"All {len(data.discovered_layers)} component IDs are valid",
        )

    def _check_layer_type_consistency(self, data: Stage2Output) -> ValidationCheck:
        """V2.2: component_id prefix must match the component's layer_type field."""
        mismatches = []

        for comp_id, comp in data.discovered_layers.items():
            expected_prefix = f"{comp.layer_type.value}:"
            if not comp_id.startswith(expected_prefix):
                mismatches.append({
                    "component_id": comp_id,
                    "expected_prefix": expected_prefix,
                    "actual_layer_type": comp.layer_type.value,
                })

        if mismatches:
            return ValidationCheck(
                id="V2.2",
                name="V2.2_layer_type_consistency",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"{len(mismatches)} component(s) have mismatched ID/layer_type",
                details={"mismatches": mismatches[:5]},
            )

        return ValidationCheck(
            id="V2.2",
            name="V2.2_layer_type_consistency",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message="All component IDs match their layer_type fields",
        )

    def _check_token_span_consistency(self, data: Stage2Output) -> ValidationCheck:
        """V2.3: Token spans must be valid (start <= end) and non-overlapping."""
        invalid_spans = []
        overlaps = []

        # Collect all components with token spans
        components_with_spans = [
            (comp_id, comp)
            for comp_id, comp in data.discovered_layers.items()
            if comp.token_span is not None
        ]

        # Validate individual spans
        for comp_id, comp in components_with_spans:
            start, end = comp.token_span
            if end < start:
                invalid_spans.append({
                    "component_id": comp_id,
                    "token_span": [start, end],
                    "error": "end < start",
                })

        # Check for overlaps
        sorted_spans = sorted(
            [(comp_id, comp.token_span) for comp_id, comp in components_with_spans],
            key=lambda x: x[1][0],
        )

        for i in range(len(sorted_spans) - 1):
            id_a, (start_a, end_a) = sorted_spans[i]
            id_b, (start_b, end_b) = sorted_spans[i + 1]
            if end_a >= start_b:
                overlaps.append({
                    "component_a": id_a,
                    "component_b": id_b,
                    "span_a": [start_a, end_a],
                    "span_b": [start_b, end_b],
                    "overlap_start": start_b,
                    "overlap_end": min(end_a, end_b),
                })

        errors = []
        if invalid_spans:
            errors.append(f"{len(invalid_spans)} invalid span(s)")
        if overlaps:
            errors.append(f"{len(overlaps)} overlapping span(s)")

        if errors:
            details = {}
            if invalid_spans:
                details["invalid_spans"] = invalid_spans
            if overlaps:
                details["overlaps"] = overlaps

            return ValidationCheck(
                id="V2.3",
                name="V2.3_token_span_consistency",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="; ".join(errors),
                details=details,
            )

        span_count = len(components_with_spans)
        if span_count == 0:
            return ValidationCheck(
                id="V2.3",
                name="V2.3_token_span_consistency",
                passed=True,
                severity=ValidationSeverity.WARNING,
                message="No token spans set on any component",
            )

        return ValidationCheck(
            id="V2.3",
            name="V2.3_token_span_consistency",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message=f"{span_count} token spans verified — no overlaps",
        )

    def _check_parent_child_integrity(self, data: Stage2Output) -> ValidationCheck:
        """V2.4: All parent_ids must reference existing components; no cycles."""
        all_ids = set(data.discovered_layers.keys())

        # Check parent_id references
        orphaned_parents = []
        for comp_id, comp in data.discovered_layers.items():
            if comp.parent_id is not None and comp.parent_id not in all_ids:
                orphaned_parents.append({
                    "component_id": comp_id,
                    "parent_id": comp.parent_id,
                })

        # Check children references
        orphaned_children = []
        for comp_id, comp in data.discovered_layers.items():
            for child_id in comp.children:
                if child_id not in all_ids:
                    orphaned_children.append({
                        "component_id": comp_id,
                        "missing_child": child_id,
                    })

        # Check for cycles using DFS
        cycles = self._detect_cycles(data.discovered_layers)

        errors = []
        if orphaned_parents:
            errors.append(f"{len(orphaned_parents)} orphaned parent reference(s)")
        if orphaned_children:
            errors.append(f"{len(orphaned_children)} orphaned child reference(s)")
        if cycles:
            errors.append(f"{len(cycles)} cycle(s) detected")

        if errors:
            details = {}
            if orphaned_parents:
                details["orphaned_parents"] = orphaned_parents
            if orphaned_children:
                details["orphaned_children"] = orphaned_children
            if cycles:
                details["cycles"] = cycles

            return ValidationCheck(
                id="V2.4",
                name="V2.4_parent_child_integrity",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="; ".join(errors),
                details=details,
            )

        return ValidationCheck(
            id="V2.4",
            name="V2.4_parent_child_integrity",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message="All parent-child references valid — no cycles",
        )

    def _detect_cycles(
        self,
        components: dict[str, PhysicalComponent],
    ) -> list[list[str]]:
        """Detect cycles in parent-child graph using DFS."""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _dfs(node_id: str, path: list[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            comp = components.get(node_id)
            if comp:
                for child_id in comp.children:
                    if child_id not in visited:
                        _dfs(child_id, path)
                    elif child_id in rec_stack:
                        # Found cycle
                        cycle_start = path.index(child_id)
                        cycles.append(path[cycle_start:] + [child_id])

            path.pop()
            rec_stack.discard(node_id)

        for comp_id in components:
            if comp_id not in visited:
                _dfs(comp_id, [])

        return cycles

    def _check_nesting_validation(self, data: Stage2Output) -> ValidationCheck:
        """V2.5: Parent-child relationships must be valid per NestingMatrix."""
        invalid_nesting = []

        for comp_id, comp in data.discovered_layers.items():
            if comp.parent_id is not None:
                parent = data.discovered_layers.get(comp.parent_id)
                if parent is not None:
                    if not self.nesting_matrix.can_contain(
                        parent.layer_type,
                        comp.layer_type,
                    ):
                        invalid_nesting.append({
                            "parent_id": comp.parent_id,
                            "parent_type": parent.layer_type.value,
                            "child_id": comp_id,
                            "child_type": comp.layer_type.value,
                        })

        if invalid_nesting:
            return ValidationCheck(
                id="V2.5",
                name="V2.5_nesting_validation",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"{len(invalid_nesting)} invalid nesting relationship(s) per NestingMatrix",
                details={"invalid_nesting": invalid_nesting[:5]},
            )

        return ValidationCheck(
            id="V2.5",
            name="V2.5_nesting_validation",
            passed=True,
            severity=ValidationSeverity.WARNING,
            message="All parent-child relationships valid per NestingMatrix",
        )

    def _check_mapping_completeness(self, data: Stage2Output) -> ValidationCheck:
        """V2.6: All components should have token spans for downstream stage routing."""
        components_with_spans = sum(
            1 for comp in data.discovered_layers.values()
            if comp.token_span is not None
        )
        total = len(data.discovered_layers)

        if components_with_spans == 0:
            return ValidationCheck(
                id="V2.6",
                name="V2.6_mapping_completeness",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"No components have token spans ({total} components total)",
            )

        if components_with_spans < total:
            unmapped_count = total - components_with_spans
            unmapped_ids = [
                comp_id
                for comp_id, comp in data.discovered_layers.items()
                if comp.token_span is None
            ]
            return ValidationCheck(
                id="V2.6",
                name="V2.6_mapping_completeness",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"{unmapped_count}/{total} components missing token spans",
                details={"unmapped_components": unmapped_ids[:10]},
            )

        # Verify component_to_tokens matches token spans
        mapped_ids = set(data.component_to_tokens.keys())
        span_ids = set(data.discovered_layers.keys())

        if mapped_ids != span_ids:
            missing = span_ids - mapped_ids
            extra = mapped_ids - span_ids
            details = {}
            if missing:
                details["missing_from_mapping"] = sorted(missing)
            if extra:
                details["extra_in_mapping"] = sorted(extra)

            return ValidationCheck(
                id="V2.6",
                name="V2.6_mapping_completeness",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message="component_to_tokens does not match discovered_layers",
                details=details,
            )

        return ValidationCheck(
            id="V2.6",
            name="V2.6_mapping_completeness",
            passed=True,
            severity=ValidationSeverity.WARNING,
            message=f"All {total} components have token spans and mapping entries",
        )

    def name(self) -> str:
        return "ValidationV2"

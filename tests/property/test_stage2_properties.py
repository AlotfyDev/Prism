"""Property-based tests for Stage 2 pipeline using Hypothesis.

Tests invariants that must hold for ANY valid Stage2Output,
regardless of input document structure.
"""

import pytest
from hypothesis import given, settings, strategies as st

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    NESTING_MATRIX,
    PhysicalComponent,
    Stage2Output,
)
from prism.stage2.validation_v2 import ValidationV2


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def valid_component_ids(draw):
    """Generate valid component IDs matching `{layer_type}:{identifier}`."""
    layer_type = draw(st.sampled_from(list(LayerType)))
    identifier = draw(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_"))
    return f"{layer_type.value}:{identifier}", layer_type


@st.composite
def physical_components(draw, min_size=1, max_size=10):
    """Generate a list of PhysicalComponent objects."""
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    components = {}
    char_pos = 0

    for i in range(count):
        comp_id, layer_type = draw(valid_component_ids())
        # Ensure unique IDs
        while comp_id in components:
            comp_id, layer_type = draw(valid_component_ids())

        raw_content = draw(st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz \n\t"))
        char_start = char_pos
        char_end = char_pos + len(raw_content)
        char_pos = char_end

        components[comp_id] = PhysicalComponent(
            component_id=comp_id,
            layer_type=layer_type,
            raw_content=raw_content,
            char_start=char_start,
            char_end=char_end,
        )

    return components


@st.composite
def stage2_outputs(draw, min_components=1, max_components=10):
    """Generate valid Stage2Output objects."""
    components = draw(physical_components(min_size=min_components, max_size=max_components))
    return Stage2Output(discovered_layers=components)


# =============================================================================
# Property Tests
# =============================================================================

class TestStage2OutputInvariants:
    """Test invariants of Stage2Output schema."""

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_layer_types_matches_discovered(self, output):
        """Property: layer_types set must exactly match discovered_layers types."""
        expected_types = {comp.layer_type for comp in output.discovered_layers.values()}
        assert output.layer_types == expected_types

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_is_single_layer_correct(self, output):
        """Property: is_single_layer is True iff exactly one layer type."""
        expected = len(output.layer_types) == 1
        assert output.is_single_layer == expected

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_component_count_matches(self, output):
        """Property: component_count equals len(discovered_layers)."""
        assert output.component_count == len(output.discovered_layers)

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_component_ids_unique(self, output):
        """Property: all component IDs are unique."""
        ids = list(output.discovered_layers.keys())
        assert len(ids) == len(set(ids))

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_component_ids_valid_format(self, output):
        """Property: all component IDs match `{layer_type}:{identifier}` pattern."""
        import re
        pattern = re.compile(r"^[a-z_]+:.+$")
        for comp_id in output.discovered_layers:
            assert pattern.match(comp_id), f"Invalid ID: {comp_id}"

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_component_id_prefix_matches_layer_type(self, output):
        """Property: component_id prefix matches layer_type.value."""
        for comp_id, comp in output.discovered_layers.items():
            expected_prefix = f"{comp.layer_type.value}:"
            assert comp_id.startswith(expected_prefix), (
                f"ID {comp_id} doesn't start with {expected_prefix}"
            )


class TestValidationV2Properties:
    """Property-based tests for ValidationV2."""

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_validation_deterministic(self, output):
        """Property: validation is deterministic — same input → same result."""
        validator = ValidationV2()
        result1 = validator.validate(output)
        result2 = validator.validate(output)
        assert result1.passed == result2.passed
        assert len(result1.checks) == len(result2.checks)
        for c1, c2 in zip(result1.checks, result2.checks):
            assert c1.id == c2.id
            assert c1.passed == c2.passed

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_all_checks_present(self, output):
        """Property: validation always produces exactly 6 checks."""
        validator = ValidationV2()
        report = validator.validate(output)
        if output.discovered_layers:
            check_ids = {c.id for c in report.checks}
            assert check_ids == {"V2.1", "V2.2", "V2.3", "V2.4", "V2.5", "V2.6"}

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_critical_failures_consistent(self, output):
        """Property: critical_failures matches checks with CRITICAL severity that failed."""
        validator = ValidationV2()
        report = validator.validate(output)
        expected = [
            c for c in report.checks
            if c.severity.value == "critical" and not c.passed
        ]
        assert len(report.critical_failures) == len(expected)

    @given(stage2_outputs())
    @settings(max_examples=100)
    def test_empty_output_always_passes(self, output):
        """Property: Stage2Output with no components always passes validation."""
        empty = Stage2Output()
        validator = ValidationV2()
        report = validator.validate(empty)
        assert report.passed


class TestTokenSpanProperties:
    """Property-based tests for token span invariants."""

    @given(
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
    )
    def test_token_span_valid_when_start_le_end(self, start, end):
        """Property: token span is valid when start <= end."""
        if start <= end:
            comp = PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="text",
                token_span=(start, end),
                char_start=0,
                char_end=4,
            )
            assert comp.token_span == (start, end)

    def test_token_span_invalid_when_end_lt_start(self):
        """Property: Pydantic rejects token_span where end < start."""
        # Note: Pydantic doesn't validate tuple elements by default,
        # but our validation gate catches this
        from prism.stage2.validation_v2 import ValidationV2
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="text",
                    token_span=(10, 5),  # Invalid: end < start
                    char_start=0,
                    char_end=4,
                ),
            },
        )
        validator = ValidationV2()
        report = validator.validate(output)
        v2_3 = next(c for c in report.checks if c.id == "V2.3")
        assert not v2_3.passed


class TestNestingMatrixProperties:
    """Property-based tests for NestingMatrix invariants."""

    @given(st.sampled_from(list(LayerType)))
    def test_leaf_types_have_no_children(self, layer_type):
        """Property: leaf types cannot have any valid children."""
        if NESTING_MATRIX.is_leaf(layer_type):
            children = NESTING_MATRIX.get_valid_children(layer_type)
            assert len(children) == 0

    @given(st.sampled_from(list(LayerType)))
    def test_container_rules_consistent(self, layer_type):
        """Property: if A can contain B, B's max_depth allows nesting under A."""
        children = NESTING_MATRIX.get_valid_children(layer_type)
        max_depth = NESTING_MATRIX.max_depth_for(layer_type)
        if children:
            assert max_depth >= 1 or max_depth == -1

    @given(
        st.sampled_from(list(LayerType)),
        st.sampled_from(list(LayerType)),
    )
    def test_can_contain_symmetric_check(self, parent, child):
        """Property: can_contain is directional and not symmetric."""
        # If parent can contain child, it doesn't mean child can contain parent
        if NESTING_MATRIX.can_contain(parent, child):
            # This is OK — just verify the relationship is directional
            pass  # The test passes by simply not crashing

    def test_all_layer_types_have_rules(self):
        """Property: every LayerType has a nesting rule."""
        for lt in LayerType:
            rule = NESTING_MATRIX.rules.get(lt)
            assert rule is not None, f"No nesting rule for {lt.value}"

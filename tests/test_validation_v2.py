"""Tests for ValidationV2 — Component Integrity Gate."""

import pytest

from prism.core.validation_unit import ValidationSeverity
from prism.schemas.enums import LayerType
from prism.schemas.physical import PhysicalComponent, Stage2Output

from prism.stage2.validation_v2 import ValidationV2


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def validator():
    return ValidationV2()


@pytest.fixture
def valid_output():
    """A minimal valid Stage2Output."""
    return Stage2Output(
        discovered_layers={
            "heading:h1": PhysicalComponent(
                component_id="heading:h1",
                layer_type=LayerType.HEADING,
                raw_content="# Title",
                attributes={"level": "1"},
                token_span=(0, 2),
            ),
            "paragraph:p1": PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="Hello world.",
                token_span=(3, 7),
            ),
        },
    )


@pytest.fixture
def output_with_parent_child():
    """Stage2Output with parent-child relationships."""
    return Stage2Output(
        discovered_layers={
            "heading:h1": PhysicalComponent(
                component_id="heading:h1",
                layer_type=LayerType.HEADING,
                raw_content="# Title",
                attributes={"level": "1"},
                children=["paragraph:p1"],
            ),
            "paragraph:p1": PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="Subtitle text",
                parent_id="heading:h1",
            ),
        },
    )


# =============================================================================
# Basic Validation
# =============================================================================

class TestValidationV2Basic:
    def test_name(self, validator):
        assert validator.name() == "ValidationV2"

    def test_valid_output_passes(self, validator, valid_output):
        report = validator.validate(valid_output)
        assert report.passed
        assert report.stage == "stage2"

    def test_empty_output_passes(self, validator):
        report = validator.validate(Stage2Output())
        assert report.passed
        assert len(report.checks) == 1
        assert report.checks[0].id == "V2.empty"

    def test_wrong_type_fails(self, validator):
        report = validator.validate("not_stage2_output")
        assert not report.passed
        assert report.checks[0].id == "V2.0"
        assert report.checks[0].severity == ValidationSeverity.CRITICAL


# =============================================================================
# V2.1: Component ID Validity
# =============================================================================

class TestV2_1_ComponentIDValidity:
    def test_valid_ids_pass(self, validator, valid_output):
        report = validator.validate(valid_output)
        v2_1 = next(c for c in report.checks if c.id == "V2.1")
        assert v2_1.passed

    def test_invalid_id_pattern_cannot_be_created(self, validator):
        """Pydantic prevents creating components with invalid ID patterns."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PhysicalComponent(
                component_id="invalid_id",
                layer_type=LayerType.PARAGRAPH,
                raw_content="text",
            )

    def test_no_colon_cannot_be_created(self, validator):
        """Pydantic prevents creating components without colon in ID."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PhysicalComponent(
                component_id="paragraph_p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="text",
            )


# =============================================================================
# V2.2: Layer Type Consistency
# =============================================================================

class TestV2_2_LayerTypeConsistency:
    def test_consistent_pass(self, validator, valid_output):
        report = validator.validate(valid_output)
        v2_2 = next(c for c in report.checks if c.id == "V2.2")
        assert v2_2.passed

    def test_mismatch_cannot_be_created(self, validator):
        """Pydantic prevents creating components with mismatched ID/layer_type."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PhysicalComponent(
                component_id="paragraph:h1",
                layer_type=LayerType.HEADING,
                raw_content="# Title",
            )


# =============================================================================
# V2.3: Token Span Consistency
# =============================================================================

class TestV2_3_TokenSpanConsistency:
    def test_valid_spans_pass(self, validator, valid_output):
        report = validator.validate(valid_output)
        v2_3 = next(c for c in report.checks if c.id == "V2.3")
        assert v2_3.passed

    def test_overlapping_spans_fail(self, validator):
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Hello world.",
                    token_span=(0, 5),
                ),
                "paragraph:p2": PhysicalComponent(
                    component_id="paragraph:p2",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Second text.",
                    token_span=(3, 8),
                ),
            },
        )
        report = validator.validate(output)
        v2_3 = next(c for c in report.checks if c.id == "V2.3")
        assert not v2_3.passed
        assert v2_3.severity == ValidationSeverity.CRITICAL

    def test_invalid_span_end_before_start(self, validator):
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Hello",
                    token_span=(5, 2),
                ),
            },
        )
        report = validator.validate(output)
        v2_3 = next(c for c in report.checks if c.id == "V2.3")
        assert not v2_3.passed

    def test_no_spans_warning(self, validator):
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Hello",
                ),
            },
        )
        report = validator.validate(output)
        v2_3 = next(c for c in report.checks if c.id == "V2.3")
        assert v2_3.passed
        assert v2_3.severity == ValidationSeverity.WARNING

    def test_adjacent_spans_pass(self, validator):
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Hello",
                    token_span=(0, 2),
                ),
                "paragraph:p2": PhysicalComponent(
                    component_id="paragraph:p2",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="world",
                    token_span=(3, 5),
                ),
            },
        )
        report = validator.validate(output)
        v2_3 = next(c for c in report.checks if c.id == "V2.3")
        assert v2_3.passed


# =============================================================================
# V2.4: Parent-Child Integrity
# =============================================================================

class TestV2_4_ParentChildIntegrity:
    def test_valid_parent_child_pass(self, validator, output_with_parent_child):
        report = validator.validate(output_with_parent_child)
        v2_4 = next(c for c in report.checks if c.id == "V2.4")
        assert v2_4.passed

    def test_orphaned_parent_fails(self, validator):
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="text",
                    parent_id="heading:nonexistent",
                ),
            },
        )
        report = validator.validate(output)
        v2_4 = next(c for c in report.checks if c.id == "V2.4")
        assert not v2_4.passed
        assert v2_4.severity == ValidationSeverity.CRITICAL

    def test_orphaned_child_fails(self, validator):
        output = Stage2Output(
            discovered_layers={
                "heading:h1": PhysicalComponent(
                    component_id="heading:h1",
                    layer_type=LayerType.HEADING,
                    raw_content="# Title",
                    children=["paragraph:nonexistent"],
                ),
            },
        )
        report = validator.validate(output)
        v2_4 = next(c for c in report.checks if c.id == "V2.4")
        assert not v2_4.passed

    def test_cycle_detection(self, validator):
        output = Stage2Output(
            discovered_layers={
                "heading:h1": PhysicalComponent(
                    component_id="heading:h1",
                    layer_type=LayerType.HEADING,
                    raw_content="# Title",
                    children=["paragraph:p1"],
                ),
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="text",
                    children=["heading:h1"],
                ),
            },
        )
        report = validator.validate(output)
        v2_4 = next(c for c in report.checks if c.id == "V2.4")
        assert not v2_4.passed
        assert "cycle" in v2_4.message.lower()


# =============================================================================
# V2.5: Nesting Validation
# =============================================================================

class TestV2_5_NestingValidation:
    def test_valid_nesting_pass(self, validator, output_with_parent_child):
        report = validator.validate(output_with_parent_child)
        v2_5 = next(c for c in report.checks if c.id == "V2.5")
        assert v2_5.passed

    def test_invalid_nesting_warning(self, validator):
        # CODE_BLOCK cannot contain PARAGRAPH
        output = Stage2Output(
            discovered_layers={
                "code_block:cb1": PhysicalComponent(
                    component_id="code_block:cb1",
                    layer_type=LayerType.CODE_BLOCK,
                    raw_content="```\nsome code\n```",
                    children=["paragraph:p1"],
                ),
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="some code",
                    parent_id="code_block:cb1",
                ),
            },
        )
        report = validator.validate(output)
        v2_5 = next(c for c in report.checks if c.id == "V2.5")
        assert not v2_5.passed
        assert v2_5.severity == ValidationSeverity.WARNING


# =============================================================================
# V2.6: Mapping Completeness
# =============================================================================

class TestV2_6_MappingCompleteness:
    def test_all_components_have_spans_pass(self, validator, valid_output):
        report = validator.validate(valid_output)
        v2_6 = next(c for c in report.checks if c.id == "V2.6")
        assert v2_6.passed

    def test_no_spans_warning(self, validator):
        """No components have token_span — warning."""
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Hello",
                ),
            },
        )
        report = validator.validate(output)
        v2_6 = next(c for c in report.checks if c.id == "V2.6")
        assert not v2_6.passed
        assert v2_6.severity == ValidationSeverity.WARNING
        assert "No components have token spans" in v2_6.message

    def test_partial_spans_warning(self, validator):
        """Some components have token_span, some don't — warning."""
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Hello",
                    token_span=(0, 5),
                ),
                "paragraph:p2": PhysicalComponent(
                    component_id="paragraph:p2",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="World",
                    # No token_span
                ),
            },
        )
        report = validator.validate(output)
        v2_6 = next(c for c in report.checks if c.id == "V2.6")
        assert not v2_6.passed
        assert "missing token spans" in v2_6.message


# =============================================================================
# Integration Tests
# =============================================================================

class TestValidationV2Integration:
    """Test ValidationV2 with realistic Stage2Output from full pipeline."""

    @pytest.fixture
    def realistic_output(self):
        """Simulate output from a real document with multiple layers."""
        return Stage2Output(
            discovered_layers={
                "heading:h1": PhysicalComponent(
                    component_id="heading:h1",
                    layer_type=LayerType.HEADING,
                    raw_content="# Main Title",
                    attributes={"level": "1"},
                    token_span=(0, 2),
                    children=["paragraph:p1", "list:l1"],
                ),
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Introduction paragraph.",
                    parent_id="heading:h1",
                    token_span=(3, 8),
                ),
                "list:l1": PhysicalComponent(
                    component_id="list:l1",
                    layer_type=LayerType.LIST,
                    raw_content="- Item 1\n- Item 2",
                    parent_id="heading:h1",
                    token_span=(9, 15),
                    children=["paragraph:p2"],
                ),
                "paragraph:p2": PhysicalComponent(
                    component_id="paragraph:p2",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Nested paragraph in list.",
                    parent_id="list:l1",
                    token_span=(16, 22),
                ),
                "code_block:cb1": PhysicalComponent(
                    component_id="code_block:cb1",
                    layer_type=LayerType.CODE_BLOCK,
                    raw_content="```\nprint('hello')\n```",
                    attributes={"language": "python"},
                    token_span=(23, 30),
                ),
            },
            component_to_tokens={
                "heading:h1": (0, 2),
                "paragraph:p1": (3, 8),
                "list:l1": (9, 15),
                "paragraph:p2": (16, 22),
                "code_block:cb1": (23, 30),
            },
        )

    def test_full_realistic_output_passes(self, validator, realistic_output):
        report = validator.validate(realistic_output)
        assert report.passed
        assert len(report.checks) == 6

    def test_all_checks_present(self, validator, realistic_output):
        report = validator.validate(realistic_output)
        check_ids = {c.id for c in report.checks}
        assert check_ids == {"V2.1", "V2.2", "V2.3", "V2.4", "V2.5", "V2.6"}

    def test_critical_failures_empty(self, validator, realistic_output):
        report = validator.validate(realistic_output)
        assert len(report.critical_failures) == 0


# =============================================================================
# Edge Cases
# =============================================================================

class TestValidationV2EdgeCases:
    def test_single_component(self, validator):
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Hello",
                    token_span=(0, 5),
                ),
            },
        )
        report = validator.validate(output)
        assert report.passed

    def test_all_layer_types(self, validator):
        """Test output containing all 10 layer types."""
        layers = {
            "paragraph:p1": PhysicalComponent(
                component_id="paragraph:p1",
                layer_type=LayerType.PARAGRAPH,
                raw_content="Text",
                token_span=(0, 5),
            ),
            "heading:h1": PhysicalComponent(
                component_id="heading:h1",
                layer_type=LayerType.HEADING,
                raw_content="# Title",
                token_span=(6, 10),
            ),
            "list:l1": PhysicalComponent(
                component_id="list:l1",
                layer_type=LayerType.LIST,
                raw_content="- item",
                token_span=(11, 15),
            ),
            "table:t1": PhysicalComponent(
                component_id="table:t1",
                layer_type=LayerType.TABLE,
                raw_content="| A | B |\n| 1 | 2 |",
                token_span=(16, 25),
            ),
            "code_block:cb1": PhysicalComponent(
                component_id="code_block:cb1",
                layer_type=LayerType.CODE_BLOCK,
                raw_content="```\ncode\n```",
                token_span=(26, 35),
            ),
            "blockquote:bq1": PhysicalComponent(
                component_id="blockquote:bq1",
                layer_type=LayerType.BLOCKQUOTE,
                raw_content="> quote",
                token_span=(36, 40),
            ),
            "footnote:fn1": PhysicalComponent(
                component_id="footnote:fn1",
                layer_type=LayerType.FOOTNOTE,
                raw_content="[^1]: note",
                token_span=(41, 45),
            ),
            "metadata:m1": PhysicalComponent(
                component_id="metadata:m1",
                layer_type=LayerType.METADATA,
                raw_content="---\ntitle: Test\n---",
                token_span=(46, 50),
            ),
            "figure:f1": PhysicalComponent(
                component_id="figure:f1",
                layer_type=LayerType.FIGURE,
                raw_content="![alt](src)",
                token_span=(51, 55),
            ),
            "diagram:d1": PhysicalComponent(
                component_id="diagram:d1",
                layer_type=LayerType.DIAGRAM,
                raw_content="```mermaid\ngraph TD\n```",
                token_span=(56, 60),
            ),
        }
        output = Stage2Output(discovered_layers=layers)
        report = validator.validate(output)
        assert report.passed

    def test_deep_nesting_valid(self, validator):
        """Test valid deep nesting: heading → list → paragraph."""
        output = Stage2Output(
            discovered_layers={
                "heading:h1": PhysicalComponent(
                    component_id="heading:h1",
                    layer_type=LayerType.HEADING,
                    raw_content="# Title",
                    children=["list:l1"],
                    token_span=(0, 5),
                ),
                "list:l1": PhysicalComponent(
                    component_id="list:l1",
                    layer_type=LayerType.LIST,
                    raw_content="- item",
                    parent_id="heading:h1",
                    children=["paragraph:p1"],
                    token_span=(6, 10),
                ),
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="text",
                    parent_id="list:l1",
                    token_span=(11, 15),
                ),
            },
        )
        report = validator.validate(output)
        assert report.passed

    def test_multiple_overlaps_reported(self, validator):
        """Test that multiple overlapping spans are all reported."""
        output = Stage2Output(
            discovered_layers={
                "paragraph:p1": PhysicalComponent(
                    component_id="paragraph:p1",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="First",
                    token_span=(0, 5),
                ),
                "paragraph:p2": PhysicalComponent(
                    component_id="paragraph:p2",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Second",
                    token_span=(3, 8),
                ),
                "paragraph:p3": PhysicalComponent(
                    component_id="paragraph:p3",
                    layer_type=LayerType.PARAGRAPH,
                    raw_content="Third",
                    token_span=(6, 12),
                ),
            },
        )
        report = validator.validate(output)
        v2_3 = next(c for c in report.checks if c.id == "V2.3")
        assert not v2_3.passed
        assert len(v2_3.details["overlaps"]) == 2

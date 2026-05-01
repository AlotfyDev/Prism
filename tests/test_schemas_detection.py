"""Unit tests for Stage 2 Detection schemas (LayerInstance, DetectedLayersReport)."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import LayerType
from prism.schemas.physical import DetectedLayersReport, LayerInstance


class TestLayerInstance:
    """LayerInstance Pydantic schema validation."""

    def test_valid_minimal(self):
        inst = LayerInstance(
            layer_type=LayerType.HEADING,
            char_start=0,
            char_end=10,
            line_start=0,
            line_end=1,
            raw_content="# Title",
        )
        assert inst.layer_type == LayerType.HEADING
        assert inst.raw_content == "# Title"

    def test_valid_with_attributes(self):
        inst = LayerInstance(
            layer_type=LayerType.CODE_BLOCK,
            char_start=0,
            char_end=20,
            line_start=0,
            line_end=3,
            raw_content="```python\nx = 1\n```",
            attributes={"language": "python"},
        )
        assert inst.attributes["language"] == "python"

    def test_valid_table_instance(self):
        inst = LayerInstance(
            layer_type=LayerType.TABLE,
            char_start=0,
            char_end=30,
            line_start=0,
            line_end=3,
            raw_content="| A | B |\n|---|---|\n| 1 | 2 |",
        )
        assert inst.layer_type == LayerType.TABLE

    def test_valid_metadata_instance(self):
        inst = LayerInstance(
            layer_type=LayerType.METADATA,
            char_start=0,
            char_end=20,
            line_start=0,
            line_end=3,
            raw_content="---\ntitle: Test\n---",
        )
        assert inst.layer_type == LayerType.METADATA

    def test_valid_footnote_instance(self):
        inst = LayerInstance(
            layer_type=LayerType.FOOTNOTE,
            char_start=0,
            char_end=25,
            line_start=0,
            line_end=1,
            raw_content="[^1]: some footnote text",
        )
        assert inst.layer_type == LayerType.FOOTNOTE

    def test_valid_diagram_instance(self):
        inst = LayerInstance(
            layer_type=LayerType.DIAGRAM,
            char_start=0,
            char_end=40,
            line_start=0,
            line_end=4,
            raw_content="```mermaid\ngraph TD\nA --> B\n```",
            attributes={"diagram_type": "mermaid"},
        )
        assert inst.layer_type == LayerType.DIAGRAM

    def test_valid_figure_instance(self):
        inst = LayerInstance(
            layer_type=LayerType.FIGURE,
            char_start=0,
            char_end=20,
            line_start=0,
            line_end=1,
            raw_content="![alt text](image.png)",
        )
        assert inst.layer_type == LayerType.FIGURE

    def test_invalid_char_end_before_start(self):
        with pytest.raises(ValidationError, match="char_end"):
            LayerInstance(
                layer_type=LayerType.PARAGRAPH,
                char_start=10,
                char_end=5,
                line_start=0,
                line_end=1,
                raw_content="text",
            )

    def test_invalid_char_end_equal_start(self):
        with pytest.raises(ValidationError, match="char_end"):
            LayerInstance(
                layer_type=LayerType.PARAGRAPH,
                char_start=5,
                char_end=5,
                line_start=0,
                line_end=1,
                raw_content="text",
            )

    def test_invalid_negative_char_start(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            LayerInstance(
                layer_type=LayerType.PARAGRAPH,
                char_start=-1,
                char_end=5,
                line_start=0,
                line_end=1,
                raw_content="text",
            )

    def test_invalid_empty_content(self):
        with pytest.raises(ValidationError, match="at least 1 character"):
            LayerInstance(
                layer_type=LayerType.PARAGRAPH,
                char_start=0,
                char_end=0,
                line_start=0,
                line_end=1,
                raw_content="",
            )

    def test_invalid_line_end_before_start(self):
        with pytest.raises(ValidationError, match="line_end"):
            LayerInstance(
                layer_type=LayerType.PARAGRAPH,
                char_start=0,
                char_end=10,
                line_start=5,
                line_end=3,
                raw_content="text",
            )

    def test_all_layer_types_supported(self):
        """Every LayerType can be used in LayerInstance."""
        for lt in LayerType:
            inst = LayerInstance(
                layer_type=lt,
                char_start=0,
                char_end=10,
                line_start=0,
                line_end=1,
                raw_content="test",
            )
            assert inst.layer_type == lt


class TestDetectedLayersReport:
    """DetectedLayersReport Pydantic schema validation."""

    def test_empty_report(self):
        report = DetectedLayersReport(source_text="")
        assert report.detected_types == set()
        assert report.instances == {}
        assert report.total_instances == 0

    def test_single_instance(self):
        report = DetectedLayersReport(
            source_text="# Title\n\nParagraph",
            instances={
                LayerType.HEADING: [
                    LayerInstance(
                        layer_type=LayerType.HEADING,
                        char_start=0,
                        char_end=7,
                        line_start=0,
                        line_end=1,
                        raw_content="# Title",
                    )
                ]
            },
        )
        assert report.detected_types == {LayerType.HEADING}
        assert report.total_instances == 1
        assert len(report.instances_of(LayerType.HEADING)) == 1

    def test_multiple_layer_types(self):
        instances = {
            LayerType.HEADING: [
                LayerInstance(
                    layer_type=LayerType.HEADING,
                    char_start=0,
                    char_end=7,
                    line_start=0,
                    line_end=1,
                    raw_content="# Title",
                )
            ],
            LayerType.PARAGRAPH: [
                LayerInstance(
                    layer_type=LayerType.PARAGRAPH,
                    char_start=9,
                    char_end=18,
                    line_start=2,
                    line_end=3,
                    raw_content="Paragraph",
                )
            ],
            LayerType.TABLE: [
                LayerInstance(
                    layer_type=LayerType.TABLE,
                    char_start=20,
                    char_end=50,
                    line_start=4,
                    line_end=7,
                    raw_content="| A | B |\n|---|---|\n| 1 | 2 |",
                )
            ],
        }
        report = DetectedLayersReport(
            source_text="# Title\n\nParagraph\n\n| A | B |\n|---|---|\n| 1 | 2 |",
            instances=instances,
        )
        assert report.detected_types == {LayerType.HEADING, LayerType.PARAGRAPH, LayerType.TABLE}
        assert report.total_instances == 3

    def test_multiple_instances_same_type(self):
        instances = {
            LayerType.HEADING: [
                LayerInstance(
                    layer_type=LayerType.HEADING,
                    char_start=0,
                    char_end=7,
                    line_start=0,
                    line_end=1,
                    raw_content="# Title",
                ),
                LayerInstance(
                    layer_type=LayerType.HEADING,
                    char_start=9,
                    char_end=19,
                    line_start=2,
                    line_end=3,
                    raw_content="## Section",
                ),
            ]
        }
        report = DetectedLayersReport(
            source_text="# Title\n\n## Section",
            instances=instances,
        )
        assert len(report.instances_of(LayerType.HEADING)) == 2
        assert report.total_instances == 2

    def test_sync_detected_types_auto(self):
        """detected_types should be auto-synced with instances keys."""
        report = DetectedLayersReport(
            source_text="test",
            detected_types=set(),
            instances={
                LayerType.LIST: [
                    LayerInstance(
                        layer_type=LayerType.LIST,
                        char_start=0,
                        char_end=10,
                        line_start=0,
                        line_end=1,
                        raw_content="- item 1",
                    )
                ]
            },
        )
        assert LayerType.LIST in report.detected_types

    def test_instances_of_returns_empty_for_missing_type(self):
        report = DetectedLayersReport(source_text="")
        assert report.instances_of(LayerType.HEADING) == []

    def test_has_type(self):
        report = DetectedLayersReport(
            source_text="# Title",
            instances={
                LayerType.HEADING: [
                    LayerInstance(
                        layer_type=LayerType.HEADING,
                        char_start=0,
                        char_end=7,
                        line_start=0,
                        line_end=1,
                        raw_content="# Title",
                    )
                ]
            },
        )
        assert report.has_type(LayerType.HEADING)
        assert not report.has_type(LayerType.TABLE)

    def test_layer_counts(self):
        report = DetectedLayersReport(
            source_text="# Title\n\n- item 1\n- item 2",
            instances={
                LayerType.HEADING: [
                    LayerInstance(
                        layer_type=LayerType.HEADING,
                        char_start=0,
                        char_end=7,
                        line_start=0,
                        line_end=1,
                        raw_content="# Title",
                    )
                ],
                LayerType.LIST: [
                    LayerInstance(
                        layer_type=LayerType.LIST,
                        char_start=9,
                        char_end=25,
                        line_start=2,
                        line_end=4,
                        raw_content="- item 1\n- item 2",
                    )
                ],
            },
        )
        counts = report.layer_counts()
        assert counts == {"heading": 1, "list": 1}

    def test_all_layer_types_in_report(self):
        """Every LayerType can appear in a DetectedLayersReport."""
        instances = {}
        for lt in LayerType:
            instances[lt] = [
                LayerInstance(
                    layer_type=lt,
                    char_start=0,
                    char_end=10,
                    line_start=0,
                    line_end=1,
                    raw_content="test",
                )
            ]
        report = DetectedLayersReport(source_text="test" * 10, instances=instances)
        assert len(report.detected_types) == len(LayerType)
        assert report.total_instances == len(LayerType)

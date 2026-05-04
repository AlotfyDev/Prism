"""Tests for HybridListDetector — detects LIST and TASK_LIST from AST nodes."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import MarkdownNode, NodeType
from prism.stage2.layers.specific_detectors import HybridListDetector


def _make_list_node(raw_content: str, style: str = "unordered") -> MarkdownNode:
    """Create a mock LIST MarkdownNode for testing."""
    return MarkdownNode(
        node_type=NodeType.LIST,
        raw_content=raw_content,
        char_start=0,
        char_end=len(raw_content),
        attributes={"style": style},
    )


class TestHybridListDetector:
    """Tests for HybridListDetector."""

    def setup_method(self):
        self.detector = HybridListDetector()

    def test_detects_regular_unordered_list(self):
        nodes = [_make_list_node("- Item 1\n- Item 2\n- Item 3")]
        results = self.detector.detect(nodes, "- Item 1\n- Item 2\n- Item 3")
        assert len(results) == 1
        assert results[0].layer_type == LayerType.LIST
        assert results[0].attributes.get("has_tasks") is None

    def test_detects_regular_ordered_list(self):
        nodes = [_make_list_node("1. First\n2. Second", style="ordered")]
        results = self.detector.detect(nodes, "1. First\n2. Second")
        assert len(results) == 1
        assert results[0].layer_type == LayerType.LIST

    def test_detects_full_task_list(self):
        raw = "- [ ] Task A\n- [x] Task B\n- [ ] Task C"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert len(results) == 1
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "3"
        assert results[0].attributes["checked_count"] == "1"

    def test_detects_partial_task_list(self):
        """Mixed list: 1 task + 2 normal items → entire list becomes TASK_LIST."""
        raw = "- [ ] Do something\n- Normal item\n- Another normal"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert len(results) == 1
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "1"
        assert results[0].attributes["checked_count"] == "0"

    def test_detects_checked_task_with_uppercase_x(self):
        raw = "- [X] Completed task"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["checked_count"] == "1"

    def test_detects_ordered_task_list(self):
        raw = "1. [ ] First task\n2. [x] Second task"
        nodes = [_make_list_node(raw, style="ordered")]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["style"] == "ordered"

    def test_detects_star_bullet_task_list(self):
        """Task lists with * bullet marker."""
        raw = "* [ ] Star task 1\n* [x] Star task 2"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "2"

    def test_detects_plus_bullet_task_list(self):
        """Task lists with + bullet marker."""
        raw = "+ [ ] Plus task"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST

    def test_detects_multiple_lists_mixed_types(self):
        """Two lists: one regular, one task list."""
        raw_regular = "- Regular A\n- Regular B"
        raw_task = "- [ ] Task A\n- [x] Task B"
        combined = raw_regular + "\n\n" + raw_task
        nodes = [
            _make_list_node(raw_regular),
            _make_list_node(raw_task),
        ]
        results = self.detector.detect(nodes, combined)
        assert len(results) == 2
        types = {r.layer_type for r in results}
        assert LayerType.LIST in types
        assert LayerType.TASK_LIST in types

    def test_detects_single_unchecked_task(self):
        raw = "- [ ] Single unchecked task"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "1"
        assert results[0].attributes["checked_count"] == "0"

    def test_detects_single_checked_task(self):
        raw = "- [x] Single checked task"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "1"
        assert results[0].attributes["checked_count"] == "1"

    def test_detects_fully_completed_task_list(self):
        raw = "- [x] Done A\n- [x] Done B\n- [X] Done C"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "3"
        assert results[0].attributes["checked_count"] == "3"

    def test_empty_list_returns_no_results(self):
        nodes = []
        results = self.detector.detect(nodes, "")
        assert len(results) == 0

    def test_list_with_only_whitespace(self):
        raw = "   \n  \n   "
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert len(results) == 1
        assert results[0].layer_type == LayerType.LIST

    def test_task_items_serialized_in_attributes(self):
        raw = "- [ ] Task A\n- [x] Task B"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert "task_items" in results[0].attributes
        import json

        items = json.loads(results[0].attributes["task_items"])
        assert len(items) == 2
        assert items[0]["checked"] is False
        assert items[0]["text"] == "Task A"
        assert items[1]["checked"] is True
        assert items[1]["text"] == "Task B"

    def test_detects_nested_task_list(self):
        """Task list with nested sub-list."""
        raw = "- [ ] Parent task\n  - Sub item 1\n  - Sub item 2"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert len(results) == 1
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "1"

    def test_detects_task_with_extra_spaces(self):
        """Task checkbox with extra spaces: [  ] or [  x  ]."""
        raw = "- [  ] Task with extra spaces"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST

    def test_preserves_style_for_task_list(self):
        raw = "- [ ] A\n- [x] B"
        nodes = [_make_list_node(raw, style="unordered")]
        results = self.detector.detect(nodes, raw)
        assert results[0].attributes["style"] == "unordered"

    def test_task_item_text_excludes_checkbox_marker(self):
        """Task item text should not include the [ ] or [x] marker."""
        raw = "- [ ] Write documentation"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        import json

        items = json.loads(results[0].attributes["task_items"])
        assert items[0]["text"] == "Write documentation"
        assert "[ ]" not in items[0]["text"]

    def test_mixed_checkboxes_in_single_list(self):
        raw = "- [ ] Unchecked\n- [X] Checked uppercase\n- [x] Checked lowercase"
        nodes = [_make_list_node(raw)]
        results = self.detector.detect(nodes, raw)
        assert results[0].layer_type == LayerType.TASK_LIST
        assert results[0].attributes["task_count"] == "3"
        assert results[0].attributes["checked_count"] == "2"

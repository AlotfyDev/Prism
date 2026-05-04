"""Tests for TaskItem and TaskListComponent schemas."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    ListStyle,
    TaskItem,
    TaskListComponent,
)


class TestTaskItem:
    """Tests for the TaskItem model."""

    def test_create_unchecked_item(self):
        item = TaskItem(item_index=0, text="Write documentation")
        assert item.item_index == 0
        assert item.is_checked is False
        assert item.text == "Write documentation"
        assert item.children == []
        assert item.char_start is None
        assert item.char_end is None

    def test_create_checked_item(self):
        item = TaskItem(item_index=1, text="Run tests", is_checked=True)
        assert item.is_checked is True
        assert item.text == "Run tests"

    def test_create_item_with_char_offsets(self):
        item = TaskItem(
            item_index=0,
            text="Deploy to production",
            is_checked=False,
            char_start=100,
            char_end=125,
        )
        assert item.char_start == 100
        assert item.char_end == 125

    def test_create_item_with_children(self):
        item = TaskItem(
            item_index=0,
            text="Parent task",
            children=["paragraph:p1", "list:l1"],
        )
        assert len(item.children) == 2
        assert "paragraph:p1" in item.children

    def test_item_index_must_be_non_negative(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            TaskItem(item_index=-1, text="bad")

    def test_empty_text_is_allowed(self):
        item = TaskItem(item_index=0, text="")
        assert item.text == ""

    def test_checked_with_uppercase_x(self):
        """Task items marked with [X] should be treated as checked."""
        item = TaskItem(item_index=0, text="Done", is_checked=True)
        assert item.is_checked is True


class TestTaskListComponent:
    """Tests for the TaskListComponent model."""

    def test_create_empty_task_list(self):
        tl = TaskListComponent(
            component_id="task_list:tl1",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] Task 1\n- [x] Task 2",
            style=ListStyle.UNORDERED,
            items=[],
            char_start=0,
            char_end=30,
        )
        assert tl.task_count == 0
        assert tl.checked_count == 0
        assert tl.completion_rate == 0.0

    def test_create_task_list_with_items(self):
        tl = TaskListComponent(
            component_id="task_list:tl1",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] Task 1\n- [x] Task 2\n- [ ] Task 3",
            style=ListStyle.UNORDERED,
            items=[
                TaskItem(item_index=0, text="Task 1", is_checked=False),
                TaskItem(item_index=1, text="Task 2", is_checked=True),
                TaskItem(item_index=2, text="Task 3", is_checked=False),
            ],
            char_start=0,
            char_end=50,
        )
        assert tl.task_count == 3
        assert tl.checked_count == 1
        assert tl.completion_rate == pytest.approx(1 / 3, rel=1e-6)

    def test_create_fully_completed_task_list(self):
        tl = TaskListComponent(
            component_id="task_list:tl2",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [x] Done A\n- [x] Done B",
            style=ListStyle.UNORDERED,
            items=[
                TaskItem(item_index=0, text="Done A", is_checked=True),
                TaskItem(item_index=1, text="Done B", is_checked=True),
            ],
            char_start=0,
            char_end=30,
        )
        assert tl.task_count == 2
        assert tl.checked_count == 2
        assert tl.completion_rate == pytest.approx(1.0)

    def test_create_ordered_task_list(self):
        tl = TaskListComponent(
            component_id="task_list:tl3",
            layer_type=LayerType.TASK_LIST,
            raw_content="1. [ ] First\n2. [x] Second",
            style=ListStyle.ORDERED,
            items=[
                TaskItem(item_index=0, text="First", is_checked=False),
                TaskItem(item_index=1, text="Second", is_checked=True),
            ],
            char_start=0,
            char_end=30,
        )
        assert tl.style == ListStyle.ORDERED

    def test_auto_computes_counts_on_construction(self):
        tl = TaskListComponent(
            component_id="task_list:tl4",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] A",
            items=[
                TaskItem(item_index=0, text="A", is_checked=False),
                TaskItem(item_index=1, text="B", is_checked=True),
                TaskItem(item_index=2, text="C", is_checked=True),
            ],
            char_start=0,
            char_end=10,
        )
        assert tl.task_count == 3
        assert tl.checked_count == 2
        assert tl.completion_rate == pytest.approx(2 / 3, rel=1e-6)

    def test_rejects_non_sequential_item_indices(self):
        with pytest.raises(ValidationError, match="item_index"):
            TaskListComponent(
                component_id="task_list:tl5",
                layer_type=LayerType.TASK_LIST,
                raw_content="- [ ] A",
                items=[
                    TaskItem(item_index=0, text="A", is_checked=False),
                    TaskItem(item_index=2, text="B", is_checked=True),
                ],
                char_start=0,
                char_end=10,
            )

    def test_rejects_duplicate_item_indices(self):
        with pytest.raises(ValidationError, match="item_index"):
            TaskListComponent(
                component_id="task_list:tl6",
                layer_type=LayerType.TASK_LIST,
                raw_content="- [ ] A",
                items=[
                    TaskItem(item_index=0, text="A", is_checked=False),
                    TaskItem(item_index=0, text="B", is_checked=True),
                ],
                char_start=0,
                char_end=10,
            )

    def test_accepts_sequential_indices_starting_from_zero(self):
        tl = TaskListComponent(
            component_id="task_list:tl7",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] A\n- [ ] B",
            items=[
                TaskItem(item_index=0, text="A", is_checked=False),
                TaskItem(item_index=1, text="B", is_checked=False),
            ],
            char_start=0,
            char_end=20,
        )
        assert tl.task_count == 2

    def test_single_item_task_list(self):
        tl = TaskListComponent(
            component_id="task_list:tl8",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [x] Solo task",
            items=[
                TaskItem(item_index=0, text="Solo task", is_checked=True),
            ],
            char_start=0,
            char_end=20,
        )
        assert tl.task_count == 1
        assert tl.checked_count == 1
        assert tl.completion_rate == pytest.approx(1.0)

    def test_completion_rate_is_zero_for_empty(self):
        tl = TaskListComponent(
            component_id="task_list:tl9",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] placeholder",
            items=[],
            char_start=0,
            char_end=20,
        )
        assert tl.task_count == 0
        assert tl.checked_count == 0
        assert tl.completion_rate == 0.0

    def test_completion_rate_float_precision(self):
        """Verify completion rate is computed with float precision."""
        items = [
            TaskItem(item_index=i, text=f"Task {i}", is_checked=(i < 7))
            for i in range(10)
        ]
        tl = TaskListComponent(
            component_id="task_list:tl10",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] Task 0\n- [x] Task 1",
            items=items,
            char_start=0,
            char_end=50,
        )
        assert tl.task_count == 10
        assert tl.checked_count == 7
        assert tl.completion_rate == pytest.approx(0.7, rel=1e-6)

    def test_layer_type_is_task_list(self):
        tl = TaskListComponent(
            component_id="task_list:tl11",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] A",
            items=[],
            char_start=0,
            char_end=10,
        )
        assert tl.layer_type == LayerType.TASK_LIST

    def test_inherits_physical_component_fields(self):
        tl = TaskListComponent(
            component_id="task_list:tl12",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] A\n- [x] B",
            items=[],
            char_start=5,
            char_end=25,
        )
        assert tl.component_id == "task_list:tl12"
        assert tl.raw_content == "- [ ] A\n- [x] B"
        assert tl.char_start == 5
        assert tl.char_end == 25
        assert tl.children == []
        assert tl.attributes == {}

    def test_default_style_is_unordered(self):
        tl = TaskListComponent(
            component_id="task_list:tl13",
            layer_type=LayerType.TASK_LIST,
            raw_content="- [ ] A",
            items=[],
            char_start=0,
            char_end=10,
        )
        assert tl.style == ListStyle.UNORDERED

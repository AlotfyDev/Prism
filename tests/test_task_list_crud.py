"""Tests for TaskListCRUD operations."""

import pytest

from prism.schemas.enums import LayerType
from prism.schemas.physical import ListStyle, TaskItem, TaskListComponent
from prism.stage2.layers import get_crud, LayerRegistry
from prism.stage2.layers.task_list import TaskListCRUD


class TestTaskListCRUD:
    """Tests for TaskListCRUD operations."""

    def setup_method(self):
        self.crud = TaskListCRUD()

    def test_create_task_list(self):
        tl = self.crud.create("tl1", "- [ ] Task A\n- [x] Task B")
        assert tl.component_id == "task_list:tl1"
        assert tl.layer_type == LayerType.TASK_LIST
        assert tl.style == ListStyle.UNORDERED
        assert tl.items == []
        assert tl.task_count == 0

    def test_create_ordered_task_list(self):
        tl = self.crud.create("tl2", "1. [ ] Task", style=ListStyle.ORDERED)
        assert tl.style == ListStyle.ORDERED

    def test_create_with_char_offsets(self):
        tl = self.crud.create("tl3", "- [ ] A", char_start=10, char_end=20)
        assert tl.char_start == 10
        assert tl.char_end == 20

    def test_add_unchecked_item(self):
        tl = self.crud.create("tl4", "- [ ] A")
        item = self.crud.add_item(tl, text="New task", is_checked=False)
        assert item.text == "New task"
        assert item.is_checked is False
        assert item.item_index == 0
        assert len(tl.items) == 1
        assert tl.task_count == 1

    def test_add_checked_item(self):
        tl = self.crud.create("tl5", "- [ ] A")
        item = self.crud.add_item(tl, text="Done", is_checked=True)
        assert item.is_checked is True
        assert tl.checked_count == 1
        assert tl.completion_rate == 1.0

    def test_add_multiple_items(self):
        tl = self.crud.create("tl6", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=False)
        self.crud.add_item(tl, text="B", is_checked=True)
        self.crud.add_item(tl, text="C", is_checked=False)
        assert tl.task_count == 3
        assert tl.checked_count == 1
        assert tl.completion_rate == pytest.approx(1 / 3, rel=1e-6)

    def test_insert_item(self):
        tl = self.crud.create("tl7", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=False)
        self.crud.add_item(tl, text="C", is_checked=False)
        self.crud.insert_item(tl, 1, text="B", is_checked=True)
        assert tl.items[1].text == "B"
        assert tl.items[1].is_checked is True
        assert tl.items[0].item_index == 0
        assert tl.items[1].item_index == 1
        assert tl.items[2].item_index == 2

    def test_insert_item_at_start(self):
        tl = self.crud.create("tl8", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=False)
        item = self.crud.insert_item(tl, 0, text="First", is_checked=True)
        assert item.item_index == 0
        assert item.text == "First"
        assert tl.items[0].item_index == 0
        assert tl.items[1].item_index == 1

    def test_insert_item_out_of_bounds(self):
        tl = self.crud.create("tl9", "- [ ] A")
        with pytest.raises(ValueError, match="out of range"):
            self.crud.insert_item(tl, 5, text="Bad")

    def test_remove_item(self):
        tl = self.crud.create("tl10", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=False)
        self.crud.add_item(tl, text="B", is_checked=True)
        self.crud.add_item(tl, text="C", is_checked=False)
        self.crud.remove_item(tl, 1)
        assert len(tl.items) == 2
        assert tl.items[0].text == "A"
        assert tl.items[1].text == "C"
        assert tl.items[1].item_index == 1
        assert tl.task_count == 2

    def test_remove_item_not_found(self):
        tl = self.crud.create("tl11", "- [ ] A")
        self.crud.add_item(tl, text="A")
        with pytest.raises(ValueError, match="not found"):
            self.crud.remove_item(tl, 5)

    def test_toggle_item(self):
        tl = self.crud.create("tl12", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=False)
        assert tl.checked_count == 0
        self.crud.toggle_item(tl, 0)
        assert tl.items[0].is_checked is True
        assert tl.checked_count == 1
        assert tl.completion_rate == 1.0

    def test_toggle_item_back(self):
        tl = self.crud.create("tl13", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=True)
        assert tl.checked_count == 1
        self.crud.toggle_item(tl, 0)
        assert tl.items[0].is_checked is False
        assert tl.checked_count == 0

    def test_check_item(self):
        tl = self.crud.create("tl14", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=False)
        self.crud.check_item(tl, 0)
        assert tl.items[0].is_checked is True
        assert tl.checked_count == 1

    def test_uncheck_item(self):
        tl = self.crud.create("tl15", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=True)
        self.crud.uncheck_item(tl, 0)
        assert tl.items[0].is_checked is False
        assert tl.checked_count == 0

    def test_reorder_item(self):
        tl = self.crud.create("tl16", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=False)
        self.crud.add_item(tl, text="B", is_checked=False)
        self.crud.add_item(tl, text="C", is_checked=False)
        self.crud.reorder_item(tl, 0, 2)
        assert tl.items[0].text == "B"
        assert tl.items[1].text == "C"
        assert tl.items[2].text == "A"

    def test_reorder_item_out_of_bounds(self):
        tl = self.crud.create("tl17", "- [ ] A")
        self.crud.add_item(tl, text="A")
        with pytest.raises(ValueError, match="out of range"):
            self.crud.reorder_item(tl, 0, 5)

    def test_add_child_to_item(self):
        tl = self.crud.create("tl18", "- [ ] A")
        self.crud.add_item(tl, text="A")
        self.crud.add_child_to_item(tl, 0, "paragraph:p1")
        assert "paragraph:p1" in tl.items[0].children
        assert "paragraph:p1" in tl.children

    def test_add_duplicate_child_raises(self):
        tl = self.crud.create("tl19", "- [ ] A")
        self.crud.add_item(tl, text="A")
        self.crud.add_child_to_item(tl, 0, "paragraph:p1")
        with pytest.raises(ValueError, match="already in item"):
            self.crud.add_child_to_item(tl, 0, "paragraph:p1")

    def test_remove_child_from_item(self):
        tl = self.crud.create("tl20", "- [ ] A")
        self.crud.add_item(tl, text="A")
        self.crud.add_child_to_item(tl, 0, "paragraph:p1")
        self.crud.remove_child_from_item(tl, 0, "paragraph:p1")
        assert "paragraph:p1" not in tl.items[0].children

    def test_remove_child_not_in_item(self):
        tl = self.crud.create("tl21", "- [ ] A")
        self.crud.add_item(tl, text="A")
        with pytest.raises(ValueError, match="not in item"):
            self.crud.remove_child_from_item(tl, 0, "paragraph:p99")

    def test_get_item(self):
        tl = self.crud.create("tl22", "- [ ] A")
        self.crud.add_item(tl, text="A", is_checked=True)
        item = self.crud.get_item(tl, 0)
        assert item.text == "A"
        assert item.is_checked is True

    def test_get_item_not_found(self):
        tl = self.crud.create("tl23", "- [ ] A")
        with pytest.raises(ValueError, match="not found"):
            self.crud.get_item(tl, 5)

    def test_set_item_char_range(self):
        tl = self.crud.create("tl24", "- [ ] A")
        self.crud.add_item(tl, text="A")
        self.crud.set_item_char_range(tl, 0, 10, 25)
        assert tl.items[0].char_start == 10
        assert tl.items[0].char_end == 25

    def test_set_style(self):
        tl = self.crud.create("tl25", "- [ ] A")
        self.crud.set_style(tl, ListStyle.ORDERED)
        assert tl.style == ListStyle.ORDERED

    def test_get_item_children(self):
        tl = self.crud.create("tl26", "- [ ] A")
        self.crud.add_item(tl, text="A")
        self.crud.add_child_to_item(tl, 0, "paragraph:p1")
        self.crud.add_child_to_item(tl, 0, "list:l1")
        children = self.crud.get_item_children(tl, 0)
        assert children == ["paragraph:p1", "list:l1"]

    def test_all_item_children(self):
        tl = self.crud.create("tl27", "- [ ] A")
        self.crud.add_item(tl, text="A")
        self.crud.add_item(tl, text="B")
        self.crud.add_child_to_item(tl, 0, "paragraph:p1")
        self.crud.add_child_to_item(tl, 1, "list:l1")
        result = self.crud.all_item_children(tl)
        assert result[0] == ["paragraph:p1"]
        assert result[1] == ["list:l1"]

    def test_item_count(self):
        tl = self.crud.create("tl28", "- [ ] A")
        assert self.crud.item_count(tl) == 0
        self.crud.add_item(tl, text="A")
        self.crud.add_item(tl, text="B")
        assert self.crud.item_count(tl) == 2

    def test_layer_registry_has_task_list(self):
        """Verify TaskListCRUD is auto-registered."""
        crud = LayerRegistry.get(LayerType.TASK_LIST)
        assert isinstance(crud, TaskListCRUD)

    def test_get_crud_returns_task_list_crud(self):
        """Verify get_crud() returns TaskListCRUD for TASK_LIST."""
        crud = get_crud(LayerType.TASK_LIST)
        assert isinstance(crud, TaskListCRUD)

    def test_layer_type_property(self):
        assert self.crud.layer_type == LayerType.TASK_LIST

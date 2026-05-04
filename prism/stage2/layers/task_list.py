"""CRUD operations for TaskListComponent."""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    ListStyle,
    TaskItem,
    TaskListComponent,
)

from prism.stage2.layers.base import LayerCRUD, LayerRegistry


class TaskListCRUD(LayerCRUD[TaskListComponent]):
    """CRUD operations for task list components.

    Provides task list-specific operations: add task items,
    toggle/check/uncheck items, plus all common PhysicalComponent
    operations from LayerCRUD.

    Usage:
        crud = TaskListCRUD()
        tl = crud.create("tl1", "- [ ] Task A\\n- [x] Task B")
        crud.add_item(tl, text="New task", is_checked=False)
        crud.toggle_item(tl, 0)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.TASK_LIST

    def create(
        self,
        identifier: str,
        raw_content: str,
        style: ListStyle = ListStyle.UNORDERED,
        char_start: int = 0,
        char_end: int = 0,
    ) -> TaskListComponent:
        """Create a new TaskListComponent.

        Args:
            identifier: Short ID (e.g. "tl1").
            raw_content: Raw Markdown task list text.
            style: Ordered or unordered.
            char_start: Character offset in source text (start, inclusive).
            char_end: Character offset in source text (end, exclusive).

        Returns:
            A new TaskListComponent.
        """
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return TaskListComponent(
            component_id=f"task_list:{identifier}",
            layer_type=LayerType.TASK_LIST,
            raw_content=raw_content,
            style=style,
            children=[],
            items=[],
            char_start=char_start,
            char_end=char_end,
        )

    def add_item(
        self,
        tl: TaskListComponent,
        text: str = "",
        is_checked: bool = False,
        item_index: Optional[int] = None,
    ) -> TaskItem:
        """Add a task item to the task list.

        Args:
            tl: The task list component.
            text: Task item text.
            is_checked: Whether the task is completed.
            item_index: Explicit index. None = auto-append.

        Returns:
            The newly created TaskItem.

        Raises:
            ValueError: If index is out of bounds (not at end).
        """
        if item_index is None:
            item_index = len(tl.items)
        elif item_index != len(tl.items):
            raise ValueError(
                f"add_item: index {item_index} != end ({len(tl.items)}). "
                f"Use insert_item() for non-append positions."
            )

        item = TaskItem(
            item_index=item_index,
            children=[],
            is_checked=is_checked,
            text=text,
        )
        tl.items.append(item)
        return item

    def insert_item(
        self,
        tl: TaskListComponent,
        position: int,
        text: str = "",
        is_checked: bool = False,
    ) -> TaskItem:
        """Insert a task item at a specific position, reordering subsequent items.

        Args:
            tl: The task list component.
            position: Insert position (0 = first).
            text: Task item text.
            is_checked: Whether the task is completed.

        Returns:
            The newly inserted TaskItem.

        Raises:
            ValueError: If position is out of bounds.
        """
        if position < 0 or position > len(tl.items):
            raise ValueError(
                f"Position {position} out of range [0, {len(tl.items)}]"
            )

        item = TaskItem(
            item_index=position,
            children=[],
            is_checked=is_checked,
            text=text,
        )
        tl.items.insert(position, item)
        self._reindex(tl)
        return item

    def remove_item(
        self,
        tl: TaskListComponent,
        item_index: int,
    ) -> TaskListComponent:
        """Remove a task item by its index, reordering subsequent items.

        Args:
            tl: The task list component.
            item_index: Index of the item to remove.

        Returns:
            Updated task list.

        Raises:
            ValueError: If item not found.
        """
        item = self.get_item(tl, item_index)

        for child_id in item.children:
            if child_id in tl.children:
                tl.children.remove(child_id)

        tl.items.remove(item)
        self._reindex(tl)
        return tl

    def reorder_item(
        self,
        tl: TaskListComponent,
        from_index: int,
        to_index: int,
    ) -> TaskListComponent:
        """Move a task item from one position to another.

        Args:
            tl: The task list component.
            from_index: Current position.
            to_index: New position.

        Returns:
            Updated task list.

        Raises:
            ValueError: If indices are out of bounds.
        """
        if from_index < 0 or from_index >= len(tl.items):
            raise ValueError(f"from_index {from_index} out of range")
        if to_index < 0 or to_index >= len(tl.items):
            raise ValueError(f"to_index {to_index} out of range")

        item = tl.items.pop(from_index)
        tl.items.insert(to_index, item)
        self._reindex(tl)
        return tl

    def toggle_item(
        self,
        tl: TaskListComponent,
        item_index: int,
    ) -> TaskListComponent:
        """Toggle a task item's checked state.

        Args:
            tl: The task list component.
            item_index: Target item index.

        Returns:
            Updated task list.
        """
        item = self.get_item(tl, item_index)
        item.is_checked = not item.is_checked
        self._recompute_stats(tl)
        return tl

    def check_item(
        self,
        tl: TaskListComponent,
        item_index: int,
    ) -> TaskListComponent:
        """Mark a task item as checked/completed.

        Args:
            tl: The task list component.
            item_index: Target item index.

        Returns:
            Updated task list.
        """
        item = self.get_item(tl, item_index)
        item.is_checked = True
        self._recompute_stats(tl)
        return tl

    def uncheck_item(
        self,
        tl: TaskListComponent,
        item_index: int,
    ) -> TaskListComponent:
        """Mark a task item as unchecked/incomplete.

        Args:
            tl: The task list component.
            item_index: Target item index.

        Returns:
            Updated task list.
        """
        item = self.get_item(tl, item_index)
        item.is_checked = False
        self._recompute_stats(tl)
        return tl

    def add_child_to_item(
        self,
        tl: TaskListComponent,
        item_index: int,
        child_id: str,
    ) -> TaskListComponent:
        """Add a child component to a specific task item.

        Args:
            tl: The task list component.
            item_index: Target item index.
            child_id: Child component_id.

        Returns:
            Updated task list.

        Raises:
            ValueError: If item not found or child already exists.
        """
        item = self.get_item(tl, item_index)

        if child_id in item.children:
            raise ValueError(
                f"Child '{child_id}' already in item {item_index}"
            )

        item.children.append(child_id)
        if child_id not in tl.children:
            tl.children.append(child_id)
        return tl

    def remove_child_from_item(
        self,
        tl: TaskListComponent,
        item_index: int,
        child_id: str,
    ) -> TaskListComponent:
        """Remove a child component from a specific task item.

        Args:
            tl: The task list component.
            item_index: Target item index.
            child_id: Child component_id to remove.

        Returns:
            Updated task list.
        """
        item = self.get_item(tl, item_index)

        if child_id not in item.children:
            raise ValueError(
                f"Child '{child_id}' not in item {item_index}"
            )

        item.children.remove(child_id)
        return tl

    def get_item(
        self,
        tl: TaskListComponent,
        item_index: int,
    ) -> TaskItem:
        """Get a task item by its index.

        Raises:
            ValueError: If item not found.
        """
        for item in tl.items:
            if item.item_index == item_index:
                return item
        raise ValueError(
            f"Item {item_index} not found in task list {tl.component_id}"
        )

    def set_item_char_range(
        self,
        tl: TaskListComponent,
        item_index: int,
        char_start: int,
        char_end: int,
    ) -> TaskListComponent:
        """Set character offsets for a task item.

        Args:
            tl: The task list component.
            item_index: Target item index.
            char_start: Character offset start.
            char_end: Character offset end.

        Returns:
            Updated task list.
        """
        item = self.get_item(tl, item_index)
        item.char_start = char_start
        item.char_end = char_end
        return tl

    def set_style(
        self,
        tl: TaskListComponent,
        style: ListStyle,
    ) -> TaskListComponent:
        """Change the task list style.

        Args:
            tl: The task list component.
            style: New style.

        Returns:
            Updated task list.
        """
        tl.style = style
        return tl

    def get_item_children(
        self,
        tl: TaskListComponent,
        item_index: int,
    ) -> list[str]:
        """Get child component IDs for a specific task item."""
        item = self.get_item(tl, item_index)
        return list(item.children)

    def all_item_children(
        self,
        tl: TaskListComponent,
    ) -> dict[int, list[str]]:
        """Get all children for all items as {item_index: children}."""
        return {item.item_index: list(item.children) for item in tl.items}

    def item_count(self, tl: TaskListComponent) -> int:
        """Return number of task items."""
        return len(tl.items)

    def _reindex(self, tl: TaskListComponent) -> None:
        """Reassign sequential item_index values."""
        for i, item in enumerate(tl.items):
            item.item_index = i

    def _recompute_stats(self, tl: TaskListComponent) -> None:
        """No-op: stats are now computed properties."""
        pass


# Auto-register on import
LayerRegistry.register(LayerType.TASK_LIST, TaskListCRUD())

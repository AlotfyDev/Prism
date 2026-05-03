"""CRUD operations for ListComponent."""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    ListComponent,
    ListItem,
    ListStyle,
)

from prism.stage2.layers.base import LayerCRUD, LayerRegistry


class ListCRUD(LayerCRUD[ListComponent]):
    """CRUD operations for list components.

    Provides list-specific operations: items, ordering, nesting,
    plus all common PhysicalComponent operations from LayerCRUD.

    Usage:
        crud = ListCRUD()
        lst = crud.create("l1", "- Item 1\\n- Item 2", style=ListStyle.UNORDERED)
        crud.add_item(lst)
        crud.add_child_to_item(lst, 0, "paragraph:p1")
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.LIST

    def create(
        self,
        identifier: str,
        raw_content: str,
        style: ListStyle = ListStyle.UNORDERED,
        char_start: int = 0,
        char_end: int = 0,
    ) -> ListComponent:
        """Create a new ListComponent.

        Args:
            identifier: Short ID (e.g. "l1").
            raw_content: Raw Markdown list text.
            style: Ordered or unordered.
            char_start: Character offset in source text (start, inclusive).
            char_end: Character offset in source text (end, exclusive).

        Returns:
            A new ListComponent.
        """
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return ListComponent(
            component_id=f"list:{identifier}",
            layer_type=LayerType.LIST,
            raw_content=raw_content,
            style=style,
            children=[],
            items=[],
            char_start=char_start,
            char_end=char_end,
        )

    def add_item(
        self,
        lst: ListComponent,
        item_index: Optional[int] = None,
    ) -> ListItem:
        """Add an empty item to the list.

        Args:
            lst: The list component.
            item_index: Explicit index. None = auto-append.

        Returns:
            The newly created ListItem.

        Raises:
            ValueError: If index is out of bounds (not at end).
        """
        if item_index is None:
            item_index = len(lst.items)
        elif item_index != len(lst.items):
            # Only allow append (at end). Use insert_item() for other positions.
            raise ValueError(
                f"add_item: index {item_index} != end ({len(lst.items)}). "
                f"Use insert_item() for non-append positions."
            )

        item = ListItem(
            item_index=item_index,
            children=[],
        )
        lst.items.append(item)
        return item

    def insert_item(
        self,
        lst: ListComponent,
        position: int,
    ) -> ListItem:
        """Insert an item at a specific position, reordering subsequent items.

        Args:
            lst: The list component.
            position: Insert position (0 = first).

        Returns:
            The newly inserted ListItem.

        Raises:
            ValueError: If position is out of bounds.
        """
        if position < 0 or position > len(lst.items):
            raise ValueError(
                f"Position {position} out of range [0, {len(lst.items)}]"
            )

        item = ListItem(
            item_index=position,
            children=[],
        )
        lst.items.insert(position, item)
        self._reindex(lst)
        return item

    def remove_item(
        self,
        lst: ListComponent,
        item_index: int,
    ) -> ListComponent:
        """Remove an item by its index, reordering subsequent items.

        Args:
            lst: The list component.
            item_index: Index of the item to remove.

        Returns:
            Updated list.

        Raises:
            ValueError: If item not found.
        """
        item = self.get_item(lst, item_index)

        # Remove child references from flat children
        for child_id in item.children:
            if child_id in lst.children:
                lst.children.remove(child_id)

        lst.items.remove(item)
        self._reindex(lst)
        return lst

    def reorder_item(
        self,
        lst: ListComponent,
        from_index: int,
        to_index: int,
    ) -> ListComponent:
        """Move an item from one position to another.

        Args:
            lst: The list component.
            from_index: Current position.
            to_index: New position.

        Returns:
            Updated list.

        Raises:
            ValueError: If indices are out of bounds.
        """
        if from_index < 0 or from_index >= len(lst.items):
            raise ValueError(f"from_index {from_index} out of range")
        if to_index < 0 or to_index >= len(lst.items):
            raise ValueError(f"to_index {to_index} out of range")

        item = lst.items.pop(from_index)
        lst.items.insert(to_index, item)
        self._reindex(lst)
        return lst

    def nest_sublist(
        self,
        lst: ListComponent,
        parent_item_index: int,
        sublist_id: str,
    ) -> ListComponent:
        """Nest a sub-list inside a list item.

        Validates that the parent item can contain a list
        (checked via LayerCRUD.add_child).

        Args:
            lst: The parent list component.
            parent_item_index: Index of the item to nest into.
            sublist_id: component_id of the sub-list.

        Returns:
            Updated list.
        """
        item = self.get_item(lst, parent_item_index)

        if sublist_id in item.children:
            raise ValueError(
                f"Sub-list '{sublist_id}' already in item {parent_item_index}"
            )

        item.children.append(sublist_id)
        if sublist_id not in lst.children:
            lst.children.append(sublist_id)
        return lst

    def add_child_to_item(
        self,
        lst: ListComponent,
        item_index: int,
        child_id: str,
    ) -> ListComponent:
        """Add a child component to a specific list item.

        Args:
            lst: The list component.
            item_index: Target item index.
            child_id: Child component_id.

        Returns:
            Updated list.

        Raises:
            ValueError: If item not found or child already exists.
        """
        item = self.get_item(lst, item_index)

        if child_id in item.children:
            raise ValueError(
                f"Child '{child_id}' already in item {item_index}"
            )

        item.children.append(child_id)
        if child_id not in lst.children:
            lst.children.append(child_id)
        return lst

    def remove_child_from_item(
        self,
        lst: ListComponent,
        item_index: int,
        child_id: str,
    ) -> ListComponent:
        """Remove a child component from a specific list item.

        Args:
            lst: The list component.
            item_index: Target item index.
            child_id: Child component_id to remove.

        Returns:
            Updated list.
        """
        item = self.get_item(lst, item_index)

        if child_id not in item.children:
            raise ValueError(
                f"Child '{child_id}' not in item {item_index}"
            )

        item.children.remove(child_id)
        return lst

    def get_item(
        self,
        lst: ListComponent,
        item_index: int,
    ) -> ListItem:
        """Get an item by its index.

        Raises:
            ValueError: If item not found.
        """
        for item in lst.items:
            if item.item_index == item_index:
                return item
        raise ValueError(
            f"Item {item_index} not found in list {lst.component_id}"
        )

    def set_item_char_range(
        self,
        lst: ListComponent,
        item_index: int,
        char_start: int,
        char_end: int,
    ) -> ListComponent:
        """Set character offsets for a list item.

        Args:
            lst: The list component.
            item_index: Target item index.
            char_start: Character offset start.
            char_end: Character offset end.

        Returns:
            Updated list.
        """
        item = self.get_item(lst, item_index)
        item.char_start = char_start
        item.char_end = char_end
        return lst

    def set_style(
        self,
        lst: ListComponent,
        style: ListStyle,
    ) -> ListComponent:
        """Change the list style.

        Args:
            lst: The list component.
            style: New style.

        Returns:
            Updated list.
        """
        lst.style = style
        return lst

    def get_item_children(
        self,
        lst: ListComponent,
        item_index: int,
    ) -> list[str]:
        """Get child component IDs for a specific item."""
        item = self.get_item(lst, item_index)
        return list(item.children)

    def all_item_children(
        self,
        lst: ListComponent,
    ) -> dict[int, list[str]]:
        """Get all children for all items as {item_index: children}."""
        return {item.item_index: list(item.children) for item in lst.items}

    def item_count(self, lst: ListComponent) -> int:
        """Return number of items."""
        return len(lst.items)

    def _reindex(self, lst: ListComponent) -> None:
        """Reassign sequential item_index values."""
        for i, item in enumerate(lst.items):
            item.item_index = i


# Auto-register on import
LayerRegistry.register(LayerType.LIST, ListCRUD())

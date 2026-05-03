"""Base CRUD operations for PhysicalComponent."""

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    NESTING_MATRIX,
    NestingMatrix,
    PhysicalComponent,
)


ComponentT = TypeVar("ComponentT", bound=PhysicalComponent)


class LayerCRUD(ABC, Generic[ComponentT]):
    """Abstract base for all layer-specific CRUD operations.

    Every layer type (heading, table, list, etc.) gets a concrete subclass
    that implements create() and type-specific operations. Common operations
    (add_child, remove_child, etc.) are implemented here with NestingMatrix
    validation.

    Design: schema lives in prism/schemas/physical.py (shared), CRUD lives
    in prism/stage2/layers/<type>.py (stage-specific).
    """

    @property
    @abstractmethod
    def layer_type(self) -> LayerType:
        """The LayerType this CRUD operates on."""

    @abstractmethod
    def create(
        self,
        identifier: str,
        raw_content: str,
        char_start: int = 0,
        char_end: int = 0,
        **kwargs,
    ) -> ComponentT:
        """Create a new component of this layer type.

        Args:
            identifier: Short ID for the component (e.g. "tbl1", "p3").
            raw_content: Raw Markdown text.
            char_start: Character offset in source text (start, inclusive).
            char_end: Character offset in source text (end, exclusive).
            **kwargs: Type-specific fields (e.g. rows for TableComponent).

        Returns:
            A fully constructed component.
        """

    def add_child(
        self,
        parent: ComponentT,
        child_id: str,
        child_type: LayerType,
    ) -> ComponentT:
        """Add a child component ID, validated against NestingMatrix.

        Args:
            parent: The parent component to add the child to.
            child_id: The child component_id string.
            child_type: The LayerType of the child.

        Returns:
            Updated parent component.

        Raises:
            ValueError: If the parent cannot contain the child type.
        """
        if not NESTING_MATRIX.can_contain(parent.layer_type, child_type):
            valid = NESTING_MATRIX.get_valid_children(parent.layer_type)
            raise ValueError(
                f"LayerType '{parent.layer_type.value}' cannot contain "
                f"'{child_type.value}'. Valid: {[v.value for v in valid]}"
            )

        if child_id in parent.children:
            raise ValueError(
                f"Child '{child_id}' already exists in parent '{parent.component_id}'"
            )

        parent.children.append(child_id)
        return parent

    def remove_child(
        self,
        parent: ComponentT,
        child_id: str,
    ) -> ComponentT:
        """Remove a child component ID from a parent.

        Args:
            parent: The parent component.
            child_id: The child component_id to remove.

        Returns:
            Updated parent component.

        Raises:
            ValueError: If the child is not found.
        """
        if child_id not in parent.children:
            raise ValueError(
                f"Child '{child_id}' not found in parent '{parent.component_id}'"
            )
        parent.children.remove(child_id)
        return parent

    def get_children(self, component: ComponentT) -> list[str]:
        """Return child component IDs."""
        return list(component.children)

    def set_parent(
        self,
        component: ComponentT,
        parent_id: str,
    ) -> ComponentT:
        """Set the parent reference on a component.

        Args:
            component: The child component.
            parent_id: The parent component_id.

        Returns:
            Updated component.
        """
        component.parent_id = parent_id
        return component

    def set_token_span(
        self,
        component: ComponentT,
        token_start: int,
        token_end: int,
    ) -> ComponentT:
        """Assign a token span to a component.

        Args:
            component: The component to update.
            token_start: Start token index (inclusive).
            token_end: End token index (inclusive).

        Returns:
            Updated component.

        Raises:
            ValueError: If end < start.
        """
        if token_end < token_start:
            raise ValueError(
                f"token_end ({token_end}) must be >= token_start ({token_start})"
            )
        component.token_span = (token_start, token_end)
        return component

    def get_token_span(self, component: ComponentT) -> Optional[tuple[int, int]]:
        """Return the component's token span."""
        return component.token_span


class LayerRegistry:
    """Global registry mapping LayerType → its CRUD implementation.

    Used by LayerClassifier to look up the correct CRUD for each
    detected layer type. Detectors register their CRUD at import time.
    """

    _registry: dict[LayerType, LayerCRUD] = {}

    @classmethod
    def register(cls, layer_type: LayerType, crud: LayerCRUD) -> None:
        """Register a CRUD implementation for a layer type."""
        cls._registry[layer_type] = crud

    @classmethod
    def get(cls, layer_type: LayerType) -> LayerCRUD:
        """Get the CRUD for a layer type.

        Raises:
            KeyError: If no CRUD is registered for the type.
        """
        if layer_type not in cls._registry:
            raise KeyError(
                f"No CRUD registered for LayerType '{layer_type.value}'"
            )
        return cls._registry[layer_type]

    @classmethod
    def has(cls, layer_type: LayerType) -> bool:
        """Check if a CRUD is registered for the type."""
        return layer_type in cls._registry

    @classmethod
    def all_types(cls) -> set[LayerType]:
        """Return all registered layer types."""
        return set(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._registry.clear()

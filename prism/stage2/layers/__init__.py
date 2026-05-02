"""Stage 2 — Layer types hub.

Central import point for all layer-specific CRUD operations.
Each layer type has its own module with:
  - CRUD operations class (auto-registered with LayerRegistry)
  - Later: detector class

Import pattern:
    from prism.stage2.layers import get_crud, LayerRegistry
    from prism.stage2.layers.table import TableCRUD
    from prism.stage2.layers import table, list, heading, ...

Usage:
    table_crud = get_crud(LayerType.TABLE)
    t = table_crud.create("tbl1", "| A | B |\\n| 1 | 2 |")
    table_crud.add_row(t)
"""

from prism.schemas.enums import LayerType

from prism.stage2.layers.base import LayerCRUD, LayerRegistry

# Import all layer modules to trigger auto-registration
from prism.stage2.layers.table import TableCRUD
from prism.stage2.layers.list import ListCRUD
from prism.stage2.layers.simple_layers import (
    HeadingCRUD,
    ParagraphCRUD,
    CodeBlockCRUD,
    BlockquoteCRUD,
    FootnoteCRUD,
    MetadataCRUD,
    FigureCRUD,
    DiagramCRUD,
)


def get_crud(layer_type: LayerType) -> LayerCRUD:
    """Get the CRUD implementation for a layer type.

    Convenience wrapper around LayerRegistry.get().
    """
    return LayerRegistry.get(layer_type)


__all__ = [
    # Base
    "LayerCRUD",
    "LayerRegistry",
    "get_crud",
    # Complex types
    "TableCRUD",
    "ListCRUD",
    # Simple types
    "HeadingCRUD",
    "ParagraphCRUD",
    "CodeBlockCRUD",
    "BlockquoteCRUD",
    "FootnoteCRUD",
    "MetadataCRUD",
    "FigureCRUD",
    "DiagramCRUD",
]

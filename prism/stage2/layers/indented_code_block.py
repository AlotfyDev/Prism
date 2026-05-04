"""CRUD operations for IndentedCodeBlockComponent."""

from prism.schemas.enums import LayerType
from prism.schemas.physical import IndentedCodeBlockComponent

from prism.stage2.layers.base import LayerCRUD, LayerRegistry


class IndentedCodeBlockCRUD(LayerCRUD[IndentedCodeBlockComponent]):
    """CRUD operations for indented code block components.

    Indented code blocks are leaf components (no children, no nesting).
    Per CommonMark, they have no language specification.

    Usage:
        crud = IndentedCodeBlockCRUD()
        icb = crud.create("icb1", "    code here")
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.INDENTED_CODE_BLOCK

    def create(
        self,
        identifier: str,
        raw_content: str,
        char_start: int = 0,
        char_end: int = 0,
    ) -> IndentedCodeBlockComponent:
        """Create a new IndentedCodeBlockComponent.

        Args:
            identifier: Short ID (e.g. "icb1").
            raw_content: Raw indented code block text (4+ spaces per line).
            char_start: Character offset in source text (start, inclusive).
            char_end: Character offset in source text (end, exclusive).

        Returns:
            A new IndentedCodeBlockComponent.
        """
        if char_end == 0:
            char_end = char_start + len(raw_content)

        line_count = raw_content.rstrip("\n").count("\n") + 1 if raw_content else 0

        return IndentedCodeBlockComponent(
            component_id=f"indented_code_block:{identifier}",
            layer_type=LayerType.INDENTED_CODE_BLOCK,
            raw_content=raw_content,
            line_count=line_count,
            children=[],
            char_start=char_start,
            char_end=char_end,
        )


LayerRegistry.register(LayerType.INDENTED_CODE_BLOCK, IndentedCodeBlockCRUD())

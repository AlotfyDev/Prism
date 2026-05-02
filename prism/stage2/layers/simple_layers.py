"""CRUD operations for simple layer types (no specialized schema).

Heading, Paragraph, CodeBlock, Blockquote, Footnote, Metadata,
Figure, and Diagram all use PhysicalComponent directly. Their CRUD
operations are identical — only the layer_type and create kwargs differ.

Each CRUD auto-registers with LayerRegistry on import.
"""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import PhysicalComponent

from prism.stage2.layers.base import LayerCRUD, LayerRegistry


class HeadingCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for heading components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HEADING

    def create(
        self,
        identifier: str,
        raw_content: str,
        level: int = 1,
    ) -> PhysicalComponent:
        return PhysicalComponent(
            component_id=f"heading:{identifier}",
            layer_type=LayerType.HEADING,
            raw_content=raw_content,
            attributes={"level": str(level)},
        )

    def get_level(self, component: PhysicalComponent) -> int:
        return int(component.attributes.get("level", "1"))

    def set_level(self, component: PhysicalComponent, level: int) -> PhysicalComponent:
        if level < 1 or level > 6:
            raise ValueError(f"Heading level must be 1-6, got {level}")
        component.attributes["level"] = str(level)
        return component


LayerRegistry.register(LayerType.HEADING, HeadingCRUD())


class ParagraphCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for paragraph components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.PARAGRAPH

    def create(
        self,
        identifier: str,
        raw_content: str,
    ) -> PhysicalComponent:
        return PhysicalComponent(
            component_id=f"paragraph:{identifier}",
            layer_type=LayerType.PARAGRAPH,
            raw_content=raw_content,
        )


LayerRegistry.register(LayerType.PARAGRAPH, ParagraphCRUD())


class CodeBlockCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for code block components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.CODE_BLOCK

    def create(
        self,
        identifier: str,
        raw_content: str,
        language: str = "",
    ) -> PhysicalComponent:
        attrs = {}
        if language:
            attrs["language"] = language
        return PhysicalComponent(
            component_id=f"code_block:{identifier}",
            layer_type=LayerType.CODE_BLOCK,
            raw_content=raw_content,
            attributes=attrs,
        )

    def get_language(self, component: PhysicalComponent) -> str:
        return component.attributes.get("language", "")

    def set_language(self, component: PhysicalComponent, language: str) -> PhysicalComponent:
        component.attributes["language"] = language
        return component


LayerRegistry.register(LayerType.CODE_BLOCK, CodeBlockCRUD())


class BlockquoteCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for blockquote components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.BLOCKQUOTE

    def create(
        self,
        identifier: str,
        raw_content: str,
        style: str = "blockquote",
    ) -> PhysicalComponent:
        return PhysicalComponent(
            component_id=f"blockquote:{identifier}",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content=raw_content,
            attributes={"style": style},
        )

    def get_style(self, component: PhysicalComponent) -> str:
        return component.attributes.get("style", "blockquote")


LayerRegistry.register(LayerType.BLOCKQUOTE, BlockquoteCRUD())


class FootnoteCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for footnote components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FOOTNOTE

    def create(
        self,
        identifier: str,
        raw_content: str,
        label: str = "",
    ) -> PhysicalComponent:
        attrs = {}
        if label:
            attrs["label"] = label
        return PhysicalComponent(
            component_id=f"footnote:{identifier}",
            layer_type=LayerType.FOOTNOTE,
            raw_content=raw_content,
            attributes=attrs,
        )

    def get_label(self, component: PhysicalComponent) -> str:
        return component.attributes.get("label", "")


LayerRegistry.register(LayerType.FOOTNOTE, FootnoteCRUD())


class MetadataCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for metadata components (YAML front matter)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.METADATA

    def create(
        self,
        identifier: str,
        raw_content: str,
    ) -> PhysicalComponent:
        return PhysicalComponent(
            component_id=f"metadata:{identifier}",
            layer_type=LayerType.METADATA,
            raw_content=raw_content,
        )


LayerRegistry.register(LayerType.METADATA, MetadataCRUD())


class FigureCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for figure/image components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FIGURE

    def create(
        self,
        identifier: str,
        raw_content: str,
        caption: str = "",
        src: str = "",
    ) -> PhysicalComponent:
        attrs = {}
        if caption:
            attrs["caption"] = caption
        if src:
            attrs["src"] = src
        return PhysicalComponent(
            component_id=f"figure:{identifier}",
            layer_type=LayerType.FIGURE,
            raw_content=raw_content,
            attributes=attrs,
        )

    def get_caption(self, component: PhysicalComponent) -> str:
        return component.attributes.get("caption", "")

    def get_src(self, component: PhysicalComponent) -> str:
        return component.attributes.get("src", "")


LayerRegistry.register(LayerType.FIGURE, FigureCRUD())


class DiagramCRUD(LayerCRUD[PhysicalComponent]):
    """CRUD for diagram components (mermaid, graphviz, ASCII)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.DIAGRAM

    def create(
        self,
        identifier: str,
        raw_content: str,
        diagram_type: str = "",
    ) -> PhysicalComponent:
        attrs = {}
        if diagram_type:
            attrs["diagram_type"] = diagram_type
        return PhysicalComponent(
            component_id=f"diagram:{identifier}",
            layer_type=LayerType.DIAGRAM,
            raw_content=raw_content,
            attributes=attrs,
        )

    def get_diagram_type(self, component: PhysicalComponent) -> str:
        return component.attributes.get("diagram_type", "")


LayerRegistry.register(LayerType.DIAGRAM, DiagramCRUD())

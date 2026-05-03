"""CRUD operations for simple layer types using typed Pydantic components.

Each LayerType has a dedicated typed component model (P2.6). CRUD classes
return their specific typed component instead of generic PhysicalComponent
with attributes: dict. This provides type safety, validation, and IDE
autocomplete.

Each CRUD auto-registers with LayerRegistry on import.
"""

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    BlockquoteComponent,
    CodeBlockComponent,
    DiagramComponent,
    EmphasisComponent,
    EmphasisType,
    FigureComponent,
    FootnoteComponent,
    HeadingComponent,
    HtmlBlockComponent,
    HtmlInlineComponent,
    InlineCodeComponent,
    LinkComponent,
    LinkType,
    MetadataComponent,
    ParagraphComponent,
)

from prism.stage2.layers.base import LayerCRUD, LayerRegistry


# =============================================================================
# HeadingCRUD → HeadingComponent
# =============================================================================

class HeadingCRUD(LayerCRUD[HeadingComponent]):
    """CRUD for heading components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HEADING

    def create(
        self,
        identifier: str,
        raw_content: str,
        level: int | None = None,
        text: str | None = None,
        anchor_id: str | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> HeadingComponent:
        if level is None:
            level = 0
            for ch in raw_content:
                if ch == "#":
                    level += 1
                else:
                    break
            level = max(1, min(6, level))
        if text is None:
            text = raw_content.lstrip("#").strip()
        if not text:
            text = raw_content.strip()
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return HeadingComponent(
            component_id=f"heading:{identifier}",
            layer_type=LayerType.HEADING,
            raw_content=raw_content,
            level=level,
            text=text,
            anchor_id=anchor_id,
            char_start=char_start,
            char_end=char_end,
        )

    def get_level(self, component: HeadingComponent) -> int:
        return component.level

    def set_level(self, component: HeadingComponent, level: int) -> HeadingComponent:
        if level < 1 or level > 6:
            raise ValueError(f"Heading level must be 1-6, got {level}")
        component.level = level
        return component


LayerRegistry.register(LayerType.HEADING, HeadingCRUD())


# =============================================================================
# ParagraphCRUD → ParagraphComponent
# =============================================================================

class ParagraphCRUD(LayerCRUD[ParagraphComponent]):
    """CRUD for paragraph components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.PARAGRAPH

    def create(
        self,
        identifier: str,
        raw_content: str,
        word_count: int | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> ParagraphComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return ParagraphComponent(
            component_id=f"paragraph:{identifier}",
            layer_type=LayerType.PARAGRAPH,
            raw_content=raw_content,
            word_count=word_count,
            char_start=char_start,
            char_end=char_end,
        )


LayerRegistry.register(LayerType.PARAGRAPH, ParagraphCRUD())


# =============================================================================
# CodeBlockCRUD → CodeBlockComponent
# =============================================================================

class CodeBlockCRUD(LayerCRUD[CodeBlockComponent]):
    """CRUD for code block components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.CODE_BLOCK

    def create(
        self,
        identifier: str,
        raw_content: str,
        language: str | None = None,
        has_lines: bool = False,
        char_start: int = 0,
        char_end: int = 0,
    ) -> CodeBlockComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return CodeBlockComponent(
            component_id=f"code_block:{identifier}",
            layer_type=LayerType.CODE_BLOCK,
            raw_content=raw_content,
            language=language,
            has_lines=has_lines,
            char_start=char_start,
            char_end=char_end,
        )

    def get_language(self, component: CodeBlockComponent) -> str | None:
        return component.language

    def set_language(self, component: CodeBlockComponent, language: str) -> CodeBlockComponent:
        component.language = language
        return component


LayerRegistry.register(LayerType.CODE_BLOCK, CodeBlockCRUD())


# =============================================================================
# BlockquoteCRUD → BlockquoteComponent
# =============================================================================

class BlockquoteCRUD(LayerCRUD[BlockquoteComponent]):
    """CRUD for blockquote components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.BLOCKQUOTE

    def create(
        self,
        identifier: str,
        raw_content: str,
        quote_level: int = 1,
        style: str = "blockquote",
        attribution: str | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> BlockquoteComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return BlockquoteComponent(
            component_id=f"blockquote:{identifier}",
            layer_type=LayerType.BLOCKQUOTE,
            raw_content=raw_content,
            style=style,
            quote_level=quote_level,
            attribution=attribution,
            char_start=char_start,
            char_end=char_end,
        )

    def get_style(self, component: BlockquoteComponent) -> str:
        return component.style

    def get_quote_level(self, component: BlockquoteComponent) -> int:
        return component.quote_level


LayerRegistry.register(LayerType.BLOCKQUOTE, BlockquoteCRUD())


# =============================================================================
# FootnoteCRUD → FootnoteComponent
# =============================================================================

class FootnoteCRUD(LayerCRUD[FootnoteComponent]):
    """CRUD for footnote components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FOOTNOTE

    def create(
        self,
        identifier: str,
        raw_content: str,
        footnote_id: str | None = None,
        label: str | None = None,
        has_url: bool = False,
        char_start: int = 0,
        char_end: int = 0,
    ) -> FootnoteComponent:
        fid = footnote_id or label or ""
        if not fid:
            import re as _re
            m = _re.search(r"\[\^?(\w+)\]?", raw_content)
            if m:
                fid = m.group(1)
        if not fid:
            fid = identifier
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return FootnoteComponent(
            component_id=f"footnote:{identifier}",
            layer_type=LayerType.FOOTNOTE,
            raw_content=raw_content,
            footnote_id=fid,
            has_url=has_url,
            char_start=char_start,
            char_end=char_end,
        )

    def get_label(self, component: FootnoteComponent) -> str:
        return component.footnote_id


LayerRegistry.register(LayerType.FOOTNOTE, FootnoteCRUD())


# =============================================================================
# MetadataCRUD → MetadataComponent
# =============================================================================

class MetadataCRUD(LayerCRUD[MetadataComponent]):
    """CRUD for metadata components (YAML/TOML front matter)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.METADATA

    def create(
        self,
        identifier: str,
        raw_content: str,
        format: str = "yaml",
        keys: list[str] | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> MetadataComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return MetadataComponent(
            component_id=f"metadata:{identifier}",
            layer_type=LayerType.METADATA,
            raw_content=raw_content,
            format=format,
            keys=keys or [],
            char_start=char_start,
            char_end=char_end,
        )

    def get_format(self, component: MetadataComponent) -> str:
        return component.format

    def get_keys(self, component: MetadataComponent) -> list[str]:
        return list(component.keys)


LayerRegistry.register(LayerType.METADATA, MetadataCRUD())


# =============================================================================
# FigureCRUD → FigureComponent
# =============================================================================

class FigureCRUD(LayerCRUD[FigureComponent]):
    """CRUD for figure/image components."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.FIGURE

    def create(
        self,
        identifier: str,
        raw_content: str,
        image_url: str | None = None,
        src: str | None = None,
        alt_text: str | None = None,
        caption: str | None = None,
        width: int | None = None,
        height: int | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> FigureComponent:
        url = image_url or src or ""
        alt = alt_text or caption or ""
        if not url or not alt:
            import re as _re
            m = _re.search(r"!\[([^\]]*)\]\(([^)]+)\)", raw_content)
            if m:
                if not alt:
                    alt = m.group(1)
                if not url:
                    url = m.group(2)
        if not url:
            url = identifier
        if not alt:
            alt = raw_content.strip()[:80]
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return FigureComponent(
            component_id=f"figure:{identifier}",
            layer_type=LayerType.FIGURE,
            raw_content=raw_content,
            image_url=url,
            alt_text=alt,
            width=width,
            height=height,
            char_start=char_start,
            char_end=char_end,
        )

    def get_caption(self, component: FigureComponent) -> str:
        return component.alt_text

    def get_src(self, component: FigureComponent) -> str:
        return component.image_url


LayerRegistry.register(LayerType.FIGURE, FigureCRUD())


# =============================================================================
# DiagramCRUD → DiagramComponent
# =============================================================================

class DiagramCRUD(LayerCRUD[DiagramComponent]):
    """CRUD for diagram components (mermaid, graphviz, ASCII)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.DIAGRAM

    def create(
        self,
        identifier: str,
        raw_content: str,
        diagram_type: str | None = None,
        title: str | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> DiagramComponent:
        if not diagram_type:
            lower = raw_content.lower()
            if "mermaid" in lower or "graph td" in lower or "graph lr" in lower or "sequenceDiagram" in raw_content:
                diagram_type = "mermaid"
            elif "digraph" in lower or "graph {" in lower:
                diagram_type = "graphviz"
            elif any(c in raw_content for c in ["+", "-", "|"]):
                diagram_type = "ascii"
            else:
                diagram_type = "unknown"
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return DiagramComponent(
            component_id=f"diagram:{identifier}",
            layer_type=LayerType.DIAGRAM,
            raw_content=raw_content,
            diagram_type=diagram_type,
            title=title,
            char_start=char_start,
            char_end=char_end,
        )

    def get_diagram_type(self, component: DiagramComponent) -> str:
        return component.diagram_type


LayerRegistry.register(LayerType.DIAGRAM, DiagramCRUD())


# =============================================================================
# InlineCodeCRUD → InlineCodeComponent
# =============================================================================

class InlineCodeCRUD(LayerCRUD[InlineCodeComponent]):
    """CRUD for inline code components (`code`)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.INLINE_CODE

    def create(
        self,
        identifier: str,
        raw_content: str,
        content: str = "",
        language_hint: str | None = None,
        syntax_category: str | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> InlineCodeComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return InlineCodeComponent(
            component_id=f"inline_code:{identifier}",
            layer_type=LayerType.INLINE_CODE,
            raw_content=raw_content,
            content=content,
            language_hint=language_hint,
            syntax_category=syntax_category,
            char_start=char_start,
            char_end=char_end,
        )

    def get_code(self, component: InlineCodeComponent) -> str:
        return component.content


LayerRegistry.register(LayerType.INLINE_CODE, InlineCodeCRUD())


# =============================================================================
# EmphasisCRUD → EmphasisComponent
# =============================================================================

class EmphasisCRUD(LayerCRUD[EmphasisComponent]):
    """CRUD for emphasis components (**bold**, *italic*, ~~strikethrough~~)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.EMPHASIS

    def create(
        self,
        identifier: str,
        raw_content: str,
        emphasis_type: EmphasisType = EmphasisType.BOLD,
        marker: str = "**",
        char_start: int = 0,
        char_end: int = 0,
    ) -> EmphasisComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return EmphasisComponent(
            component_id=f"emphasis:{identifier}",
            layer_type=LayerType.EMPHASIS,
            raw_content=raw_content,
            emphasis_type=emphasis_type,
            marker=marker,
            char_start=char_start,
            char_end=char_end,
        )

    def get_style(self, component: EmphasisComponent) -> str:
        return component.emphasis_type.value

    def get_text(self, component: EmphasisComponent) -> str:
        return component.raw_content


LayerRegistry.register(LayerType.EMPHASIS, EmphasisCRUD())


# =============================================================================
# LinkCRUD → LinkComponent
# =============================================================================

class LinkCRUD(LayerCRUD[LinkComponent]):
    """CRUD for link components ([text](url))."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.LINK

    def create(
        self,
        identifier: str,
        raw_content: str,
        link_type: LinkType = LinkType.INLINE,
        text: str = "",
        url: str = "",
        is_external: bool | None = None,
        domain: str | None = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> LinkComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return LinkComponent(
            component_id=f"link:{identifier}",
            layer_type=LayerType.LINK,
            raw_content=raw_content,
            link_type=link_type,
            text=text,
            url=url,
            is_external=is_external,
            domain=domain,
            char_start=char_start,
            char_end=char_end,
        )

    def get_text(self, component: LinkComponent) -> str:
        return component.text

    def get_url(self, component: LinkComponent) -> str:
        return component.url

    def is_image_link(self, component: LinkComponent) -> bool:
        return component.link_type == LinkType.IMAGE


LayerRegistry.register(LayerType.LINK, LinkCRUD())


# =============================================================================
# HTMLBlockCRUD → HtmlBlockComponent
# =============================================================================

class HTMLBlockCRUD(LayerCRUD[HtmlBlockComponent]):
    """CRUD for HTML block components (<div>...</div>)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HTML_BLOCK

    def create(
        self,
        identifier: str,
        raw_content: str,
        tag_name: str = "",
        attributes: dict[str, str] | None = None,
        is_semantic: bool = False,
        char_start: int = 0,
        char_end: int = 0,
    ) -> HtmlBlockComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return HtmlBlockComponent(
            component_id=f"html_block:{identifier}",
            layer_type=LayerType.HTML_BLOCK,
            raw_content=raw_content,
            tag_name=tag_name,
            attributes=attributes or {},
            is_semantic=is_semantic,
            char_start=char_start,
            char_end=char_end,
        )

    def get_tag(self, component: HtmlBlockComponent) -> str:
        return component.tag_name


LayerRegistry.register(LayerType.HTML_BLOCK, HTMLBlockCRUD())


# =============================================================================
# HTMLInlineCRUD → HtmlInlineComponent
# =============================================================================

class HTMLInlineCRUD(LayerCRUD[HtmlInlineComponent]):
    """CRUD for inline HTML components (<span>...</span>)."""

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HTML_INLINE

    def create(
        self,
        identifier: str,
        raw_content: str,
        tag_name: str = "",
        attributes: dict[str, str] | None = None,
        is_self_closing: bool = False,
        char_start: int = 0,
        char_end: int = 0,
    ) -> HtmlInlineComponent:
        if char_end == 0:
            char_end = char_start + len(raw_content)
        return HtmlInlineComponent(
            component_id=f"html_inline:{identifier}",
            layer_type=LayerType.HTML_INLINE,
            raw_content=raw_content,
            tag_name=tag_name,
            attributes=attributes or {},
            is_self_closing=is_self_closing,
            char_start=char_start,
            char_end=char_end,
        )

    def get_tag(self, component: HtmlInlineComponent) -> str:
        return component.tag_name


LayerRegistry.register(LayerType.HTML_INLINE, HTMLInlineCRUD())

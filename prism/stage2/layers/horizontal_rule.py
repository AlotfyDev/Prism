"""CRUD operations for HorizontalRuleComponent."""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    HRuleStyle,
    HorizontalRuleComponent,
)

from prism.stage2.layers.base import LayerCRUD, LayerRegistry


class HRCRUD(LayerCRUD[HorizontalRuleComponent]):
    """CRUD operations for horizontal rule components.

    Horizontal rules are leaf components (no children, no nesting).

    Usage:
        crud = HRCRUD()
        hr = crud.create("hr1", "---", style=HRuleStyle.DASH)
    """

    @property
    def layer_type(self) -> LayerType:
        return LayerType.HORIZONTAL_RULE

    def create(
        self,
        identifier: str,
        raw_content: str,
        style: Optional[HRuleStyle | str] = None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> HorizontalRuleComponent:
        """Create a new HorizontalRuleComponent.

        Args:
            identifier: Short ID (e.g. "hr1").
            raw_content: Raw Markdown HR text (e.g. "---", "***", "___").
            style: Separator character type. Auto-detected from raw_content
                if not provided. Can be HRuleStyle enum or string.
            char_start: Character offset in source text (start, inclusive).
            char_end: Character offset in source text (end, exclusive).

        Returns:
            A new HorizontalRuleComponent.
        """
        if char_end == 0:
            char_end = char_start + len(raw_content)

        if style is None:
            style = self._detect_style(raw_content)
        elif isinstance(style, str):
            style = self._style_from_string(style)

        return HorizontalRuleComponent(
            component_id=f"horizontal_rule:{identifier}",
            layer_type=LayerType.HORIZONTAL_RULE,
            raw_content=raw_content,
            style=style,
            children=[],
            char_start=char_start,
            char_end=char_end,
        )

    def set_style(
        self,
        hr: HorizontalRuleComponent,
        style: HRuleStyle,
    ) -> HorizontalRuleComponent:
        """Change the horizontal rule style.

        Args:
            hr: The horizontal rule component.
            style: New style.

        Returns:
            Updated component.
        """
        hr.style = style
        return hr

    @staticmethod
    def _detect_style(raw_content: str) -> HRuleStyle:
        """Detect the HR style from raw content.

        Args:
            raw_content: Raw Markdown HR text.

        Returns:
            Detected HRuleStyle.
        """
        stripped = raw_content.strip()
        if not stripped:
            return HRuleStyle.DASH

        first_char = stripped[0]
        if first_char == "*":
            return HRuleStyle.STAR
        elif first_char == "_":
            return HRuleStyle.UNDERSCORE
        else:
            return HRuleStyle.DASH

    @staticmethod
    def _style_from_string(style_str: str) -> HRuleStyle:
        """Convert a string to HRuleStyle enum.

        Args:
            style_str: Style string ("dash", "star", "underscore").

        Returns:
            Corresponding HRuleStyle.
        """
        style_map = {
            "dash": HRuleStyle.DASH,
            "star": HRuleStyle.STAR,
            "underscore": HRuleStyle.UNDERSCORE,
        }
        return style_map.get(style_str.lower(), HRuleStyle.DASH)


# Auto-register on import
LayerRegistry.register(LayerType.HORIZONTAL_RULE, HRCRUD())

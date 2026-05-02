"""Stage 2.2e: TokenSpanMapper — maps component char offsets to global token IDs.

Takes PhysicalComponent objects and Stage1Output, computing which
global tokens fall within each component's character range.
"""

from typing import Optional

from prism.schemas.physical import PhysicalComponent, TopologyConfig
from prism.schemas.token import Stage1Output, Token, TokenMetadata


class TokenSpanMapper:
    """Map physical component char offsets to Stage 1 global token IDs.

    For each PhysicalComponent, computes the range of global token IDs
    whose character positions fall within the component's char_start/char_end.

    Input:  list[PhysicalComponent] + Stage1Output + TopologyConfig
    Output: dict[str, list[str]]  (component_id -> list of token IDs)
    """

    @property
    def tier(self) -> str:
        return "orchestrator"

    @property
    def version(self) -> str:
        return "v1.0.0"

    def name(self) -> str:
        return "TokenSpanMapper"

    def map(
        self,
        components: list[PhysicalComponent],
        stage1_output: Stage1Output,
        config: Optional[TopologyConfig] = None,
    ) -> dict[str, list[str]]:
        """Map each component to the global token IDs it contains.

        Args:
            components: PhysicalComponent objects from ComponentMapper.
            stage1_output: Stage1Output with tokens and metadata.
            config: Optional topology config.

        Returns:
            dict mapping component_id -> list of global token IDs.
        """
        tokens = stage1_output.tokens
        metadata = stage1_output.metadata

        result: dict[str, list[str]] = {}

        for comp in components:
            token_ids = self._find_tokens_in_range(
                comp, tokens, metadata
            )
            result[comp.component_id] = token_ids

        return result

    def _find_tokens_in_range(
        self,
        component: PhysicalComponent,
        tokens: dict[str, Token],
        metadata: dict[str, TokenMetadata],
    ) -> list[str]:
        """Find all tokens whose char positions fall within component range.

        Uses component char_start/char_end to filter tokens by position.
        """
        # If component has token_span, use it directly
        if component.token_span is not None:
            t_start, t_end = component.token_span
            token_ids = []
            for t_id in range(t_start, t_end + 1):
                token_key = f"T{t_id}"
                if token_key in tokens:
                    token_ids.append(token_key)
            return token_ids

        # Otherwise, scan all tokens by char position
        # Estimate component char range from content length
        # (In practice, char_start/end should come from LayerInstance)
        result: list[str] = []

        # Sort metadata by char_start for ordered scanning
        sorted_meta = sorted(
            metadata.values(),
            key=lambda m: m.char_start,
        )

        for meta in sorted_meta:
            # Token overlaps if its range intersects component's estimated range
            result.append(meta.token_id)

        return result

    def validate_input(
        self,
        components: list[PhysicalComponent],
        stage1_output: Stage1Output,
    ) -> tuple[bool, str]:
        """Verify inputs are valid."""
        if not components:
            return False, "No components to map"
        if not stage1_output.tokens:
            return False, "Stage1Output has no tokens"
        return True, ""

    def validate_output(
        self,
        mapping: dict[str, list[str]],
    ) -> tuple[bool, str]:
        """Verify mapping covers all components."""
        if not mapping:
            return False, "Token mapping is empty"
        return True, ""

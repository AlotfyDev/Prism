"""Stage 2.2e: TokenSpanMapper — maps component char offsets to global token IDs.

Takes PhysicalComponent objects and Stage1Output, computing which
global tokens fall within each component's character range.

Uses binary search over sorted Stage 1 metadata for O(log N) lookup.
"""

from bisect import bisect_left, bisect_right
from typing import Optional

from prism.schemas.physical import PhysicalComponent, TopologyConfig
from prism.schemas.token import Stage1Output, Token, TokenMetadata
from prism.stage2.pipeline_models import TokenSpanInput, TokenSpanOutput


class TokenSpanMapper:
    """Map physical component char offsets to Stage 1 global token IDs.

    For each PhysicalComponent, computes the range of global token IDs
    whose character positions overlap with the component's char_start/char_end.

    Uses binary search over sorted TokenMetadata for efficient lookup.

    Input:  TokenSpanInput (components + stage1_output)
    Output: TokenSpanOutput (component_id -> list of token IDs)
    """

    @property
    def tier(self) -> str:
        return "orchestrator"

    @property
    def version(self) -> str:
        return "v1.0.0"

    def name(self) -> str:
        return "TokenSpanMapper"

    def process(
        self,
        input_data: TokenSpanInput,
        config: Optional[TopologyConfig] = None,
    ) -> TokenSpanOutput:
        """Map each component to the global token IDs it contains.

        Args:
            input_data: TokenSpanInput with components and stage1_output.
            config: Optional topology config.

        Returns:
            TokenSpanOutput with component_id -> list of token IDs.
        """
        mapping = self.map(
            input_data.components,
            input_data.stage1_output,
            config=config,
        )
        return TokenSpanOutput(component_to_tokens=mapping)

    # Backward compatibility: legacy map() method
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
        sorted_meta = self._build_sorted_metadata(stage1_output)
        char_starts = self._extract_char_starts(sorted_meta)

        result: dict[str, list[str]] = {}

        for comp in components:
            token_ids = self._find_tokens_in_range(
                comp, tokens, sorted_meta, char_starts
            )
            result[comp.component_id] = token_ids

        return result

    def _build_sorted_metadata(
        self, stage1_output: Stage1Output
    ) -> list[TokenMetadata]:
        """Build a list of TokenMetadata sorted by char_start.

        This is computed once per map() call and reused across all components.

        Args:
            stage1_output: Stage1Output with metadata.

        Returns:
            Sorted list of TokenMetadata by char_start.
        """
        return sorted(
            stage1_output.metadata.values(),
            key=lambda m: m.char_start,
        )

    def _extract_char_starts(
        self, sorted_meta: list[TokenMetadata]
    ) -> list[int]:
        """Extract char_start values from sorted metadata for binary search.

        Args:
            sorted_meta: List of TokenMetadata sorted by char_start.

        Returns:
            List of char_start integers, parallel to sorted_meta.
        """
        return [m.char_start for m in sorted_meta]

    def _find_tokens_in_range(
        self,
        component: PhysicalComponent,
        tokens: dict[str, Token],
        sorted_meta: list[TokenMetadata],
        char_starts: list[int],
    ) -> list[str]:
        """Find all tokens whose char positions overlap the component range.

        A token overlaps a component when:
            token.char_start < component.char_end AND token.char_end > component.char_start

        Uses binary search on sorted metadata for O(log N) boundary detection,
        then scans only the relevant range.

        Args:
            component: PhysicalComponent with char_start/char_end.
            tokens: Dict of token_id -> Token.
            sorted_meta: TokenMetadata sorted by char_start.
            char_starts: Parallel list of char_start values.

        Returns:
            List of overlapping token IDs in document order.
        """
        if component.token_span is not None:
            return self._resolve_token_span(
                component.token_span, tokens
            )

        if not sorted_meta:
            return []

        comp_start = component.char_start
        comp_end = component.char_end

        # Binary search: find exclusive upper bound
        # First token where char_start >= comp_end (nothing from here can overlap)
        end_idx = bisect_right(char_starts, comp_end - 1)

        # Binary search: find lower bound
        # First token where char_start >= comp_start
        start_idx = bisect_left(char_starts, comp_start)

        # Check one token before start_idx — it may extend into the component
        search_start = max(0, start_idx - 1)

        result: list[str] = []
        for idx in range(search_start, end_idx):
            meta = sorted_meta[idx]
            # Overlap: token range intersects component range
            if meta.char_end > comp_start and meta.char_start < comp_end:
                result.append(meta.token_id)

        return result

    def _resolve_token_span(
        self,
        token_span: tuple[int, int],
        tokens: dict[str, Token],
    ) -> list[str]:
        """Resolve a pre-computed token_span to token IDs.

        Args:
            token_span: (start_index, end_index) tuple.
            tokens: Dict of token_id -> Token.

        Returns:
            List of token IDs in the span.
        """
        t_start, t_end = token_span
        token_ids: list[str] = []
        for t_id in range(t_start, t_end + 1):
            token_key = f"T{t_id}"
            if token_key in tokens:
                token_ids.append(token_key)
        return token_ids

    # ------------------------------------------------------------------
    # Validation: primary signatures (type-safe)
    # ------------------------------------------------------------------

    def validate_input(
        self,
        input_data: TokenSpanInput,
    ) -> tuple[bool, str]:
        """Verify inputs are valid."""
        if not input_data.components:
            return False, "No components to map"
        if not input_data.stage1_output.tokens:
            return False, "Stage1Output has no tokens"
        return True, ""

    def validate_output(
        self,
        output_data: TokenSpanOutput,
    ) -> tuple[bool, str]:
        """Verify mapping covers all components."""
        if not output_data.component_to_tokens:
            return False, "Token mapping is empty"
        return True, ""

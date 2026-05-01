"""Metadata indexer for Stage 1 — validates and guarantees token metadata integrity.

Wraps SpacyTokenStreamBuilder internally to provide a single ProcessingUnit that:
1. Tokenizes the source text
2. Validates metadata integrity (no gaps, no overlaps, correct positions)
3. Returns Stage1Output with config-aware full coverage guarantee
"""

from pydantic import BaseModel

from prism.core.processing_unit import ProcessingUnit
from prism.schemas import Stage1Input, Stage1Output, TokenizationConfig
from prism.stage1.tokenizer import SpacyTokenStreamBuilder


class MetadataIndexer(ProcessingUnit[Stage1Input, Stage1Output, TokenizationConfig]):
    """Tokenizes text and validates metadata integrity.

    This is the P1.3 ProcessingUnit that combines tokenization with
    metadata validation. It wraps SpacyTokenStreamBuilder internally
    and adds validation for:

    - Metadata key/token key match (every token has metadata, every metadata has a token)
    - No overlapping character ranges
    - No gaps between consecutive tokens (when include_whitespace=True)
    - Config-aware full coverage (gaps from filtered whitespace are expected)
    - Sequential token IDs (T0, T1, ... TN)
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        self._builder = SpacyTokenStreamBuilder(model_name=model_name)

    def process(self, input_data: Stage1Input, config: TokenizationConfig) -> Stage1Output:
        valid, error = self.validate_input(input_data)
        if not valid:
            raise ValueError(f"Invalid input: {error}")

        output = self._builder.process(input_data, config)
        valid, error = self.validate_output(output)
        if not valid:
            raise ValueError(f"Metadata integrity violation: {error}")

        return output

    def validate_input(self, input_data: Stage1Input) -> tuple[bool, str]:
        return self._builder.validate_input(input_data)

    def validate_output(self, output_data: Stage1Output) -> tuple[bool, str]:
        if output_data is None:
            return False, "Output is None"

        if not isinstance(output_data, BaseModel):
            return False, f"Expected Stage1Output, got {type(output_data)}"

        if not isinstance(output_data, Stage1Output):
            return False, f"Expected Stage1Output, got {type(output_data)}"

        # Empty output is valid for empty source
        if not output_data.tokens and not output_data.source_text:
            return True, ""

        # 1. Metadata key/token key match
        token_keys = set(output_data.tokens.keys())
        metadata_keys = set(output_data.metadata.keys())

        missing_metadata = token_keys - metadata_keys
        if missing_metadata:
            return False, f"Missing metadata for tokens: {sorted(missing_metadata)}"

        extra_metadata = metadata_keys - token_keys
        if extra_metadata:
            return False, f"Metadata keys without matching tokens: {sorted(extra_metadata)}"

        # 2. Per-token metadata integrity
        for token_id, token in output_data.tokens.items():
            if token_id != token.id:
                return False, f"Token ID mismatch: key={token_id}, token.id={token.id}"

            meta = output_data.metadata[token_id]
            if meta.token_id != token_id:
                return False, f"Metadata token_id mismatch: key={token_id}, meta.token_id={meta.token_id}"

            # Token text must match source at recorded position
            if meta.char_start < 0:
                return False, f"Invalid char_start for {token_id}: {meta.char_start}"

            if meta.char_end < meta.char_start:
                return False, f"Invalid char range for {token_id}: end ({meta.char_end}) < start ({meta.char_start})"

            if meta.char_end > len(output_data.source_text):
                return False, f"Char range out of bounds for {token_id}: end ({meta.char_end}) > source length ({len(output_data.source_text)})"

            expected_text = output_data.source_text[meta.char_start:meta.char_end]
            if token.text != expected_text:
                return False, (
                    f"Token text mismatch for {token_id}: "
                    f"token.text={token.text!r} != source[{meta.char_start}:{meta.char_end}]={expected_text!r}"
                )

        # 3. No overlapping character ranges
        sorted_ids = output_data.token_ids
        for i in range(len(sorted_ids) - 1):
            current_meta = output_data.metadata[sorted_ids[i]]
            next_meta = output_data.metadata[sorted_ids[i + 1]]
            if current_meta.char_end > next_meta.char_start:
                return False, (
                    f"Overlapping char ranges: {sorted_ids[i]} "
                    f"(end={current_meta.char_end}) overlaps {sorted_ids[i + 1]} "
                    f"(start={next_meta.char_start})"
                )

        # 4. Sequential token IDs
        for i, token_id in enumerate(sorted_ids):
            expected_id = f"T{i}"
            if token_id != expected_id:
                return False, f"Non-sequential token ID: expected {expected_id}, got {token_id}"

        # 5. Position gap detection
        if not sorted_ids:
            return True, ""

        include_ws = output_data.config.include_whitespace if output_data.config else True

        # Check gap from start of source to first token
        first_meta = output_data.metadata[sorted_ids[0]]
        if first_meta.char_start > 0:
            leading_gap = output_data.source_text[:first_meta.char_start]
            if leading_gap and not (leading_gap.isspace() and not include_ws):
                return False, f"Gap at start of source: {leading_gap!r} not covered by any token"

        # Check gaps between consecutive tokens
        for i in range(len(sorted_ids) - 1):
            current_meta = output_data.metadata[sorted_ids[i]]
            next_meta = output_data.metadata[sorted_ids[i + 1]]
            if next_meta.char_start > current_meta.char_end:
                gap = output_data.source_text[current_meta.char_end:next_meta.char_start]
                if gap:
                    if include_ws:
                        return False, f"Gap between {sorted_ids[i]} and {sorted_ids[i + 1]}: {gap!r} not covered"
                    if not gap.isspace():
                        return False, (
                            f"Non-whitespace gap between {sorted_ids[i]} and {sorted_ids[i + 1]}: {gap!r} — "
                            f"include_whitespace=False but non-whitespace content is missing"
                        )

        # Check trailing gap
        last_meta = output_data.metadata[sorted_ids[-1]]
        if last_meta.char_end < len(output_data.source_text):
            trailing_gap = output_data.source_text[last_meta.char_end:]
            if trailing_gap:
                if include_ws:
                    return False, f"Trailing gap after {sorted_ids[-1]}: {trailing_gap!r} not covered"
                if not trailing_gap.isspace():
                    return False, f"Non-whitespace trailing gap: {trailing_gap!r}"

        # 6. Config-aware full coverage
        if not output_data.is_config_full_coverage:
            if output_data.config and not output_data.config.include_whitespace:
                return False, (
                    f"Token data integrity violated: token text does not match source at recorded positions, "
                    f"or non-whitespace content was lost during filtering."
                )
            return False, (
                f"Full Coverage Invariant violated: "
                f"reconstructed_text ({len(output_data.reconstructed_text)} chars) != "
                f"source_text ({len(output_data.source_text)} chars)."
            )

        return True, ""

    def name(self) -> str:
        return "MetadataIndexer"

    @property
    def tier(self) -> str:
        return "python_nlp"

"""spaCy-based token stream builder for Stage 1.

Architecture: Full Text Coverage Invariant
───────────────────────────────────────────
Every character in the source text MUST be accounted for in the token stream.
This is achieved through a three-phase pipeline:

  Phase 1 — Semantic Tokenization: spaCy extracts linguistic tokens
  Phase 2 — Structural Coverage: gaps between semantic tokens become structural tokens (whitespace/newlines)
  Phase 3 — Config Filtering: include_whitespace decides final stream composition

This design ensures:
  - P1.4 ValidationV1 can verify no gaps/overlaps in character ranges
  - P2 Physical Topology receives structural info (paragraph breaks, indentation)
  - Round-trip reconstruction: joining all tokens (with config) reproduces source_text
  - Traceability: every character maps to exactly one token
"""

from dataclasses import field
from pathlib import Path

import spacy
from pydantic import BaseModel

from prism.core.processing_unit import ProcessingUnit
from prism.schemas import Stage1Input, Stage1Output, Token, TokenMetadata, TokenizationConfig
from prism.schemas.enums import TokenType
from prism.stage1.gap_filler import _StructuralGapFiller, _TokenSpan


class SpacyTokenStreamBuilder(ProcessingUnit[Stage1Input, Stage1Output, TokenizationConfig]):
    """Tokenizes text using spaCy with Full Text Coverage guarantee.

    Three-phase pipeline:
    1. Extract semantic tokens from spaCy (words, punctuation)
    2. Detect gaps between semantic tokens and create structural tokens
    3. Apply config filter (include_whitespace) for final output

    Assigns global sequential IDs (T0, T1, ...) across the entire document.
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        self._model_name = model_name
        self._nlp = spacy.load(model_name)

    def process(self, input_data: Stage1Input, config: TokenizationConfig) -> Stage1Output:
        source_text = self._get_source_text(input_data)
        doc = self._nlp(source_text)

        spans = self._extract_semantic_spans(doc, source_text)
        spans = self._fill_structural_gaps(spans, source_text)
        spans = self._apply_config_filter(spans, config)

        return self._assign_ids_and_build_output(spans, source_text, config)

    def _extract_semantic_spans(self, doc, source_text: str) -> list[_TokenSpan]:
        """Phase 1: Extract linguistic tokens from spaCy."""
        spans: list[_TokenSpan] = []
        for spacy_token in doc:
            if spacy_token.is_space:
                continue
            line = source_text[:spacy_token.idx].count("\n") + 1
            spans.append(_TokenSpan(
                text=spacy_token.text,
                char_start=spacy_token.idx,
                char_end=spacy_token.idx + len(spacy_token.text),
                source_line=line,
                lemma=spacy_token.lemma_ or None,
                pos=spacy_token.pos_ or None,
                is_structural=False,
            ))
        return spans

    def _fill_structural_gaps(self, spans: list[_TokenSpan], source_text: str) -> list[_TokenSpan]:
        """Phase 2: Delegate to _StructuralGapFiller for full Unicode-aware coverage.

        This is the core of the Full Coverage Invariant: every character in
        the source text must belong to exactly one token. Gaps between
        semantic tokens represent whitespace/newlines that carry structural
        information for downstream stages (P2 Physical Topology).

        Delegates to _StructuralGapFiller which handles:
        - Leading gaps (before first semantic token)
        - Inter-token gaps (between semantic tokens)
        - Trailing gaps (after last semantic token)
        - Unicode whitespace (Zs, Zl, Zp categories + BOM + ASCII structural)
        """
        return _StructuralGapFiller.fill(spans, source_text)

    def _apply_config_filter(self, spans: list[_TokenSpan], config: TokenizationConfig) -> list[_TokenSpan]:
        """Phase 3: Apply include_whitespace config to structural tokens."""
        if config.include_whitespace:
            return spans
        return [s for s in spans if not s.is_structural]

    def _assign_ids_and_build_output(self, spans: list[_TokenSpan], source_text: str, config: TokenizationConfig) -> Stage1Output:
        """Convert spans to Token/TokenMetadata with global sequential IDs."""
        tokens: dict[str, Token] = {}
        metadata: dict[str, TokenMetadata] = {}

        for i, span in enumerate(spans):
            token_id = f"T{i}"
            token_type = TokenType.STRUCTURAL if span.is_structural else TokenType.SEMANTIC
            tokens[token_id] = Token(
                id=token_id,
                text=span.text,
                token_type=token_type,
                lemma=span.lemma,
                pos=span.pos,
            )
            metadata[token_id] = TokenMetadata(
                token_id=token_id,
                char_start=span.char_start,
                char_end=span.char_end,
                source_line=span.source_line,
            )

        return Stage1Output(
            tokens=tokens,
            metadata=metadata,
            source_text=source_text,
            config=config,
        )

    def _get_source_text(self, input_data: Stage1Input) -> str:
        if input_data.source_type == "file":
            source_path = Path(input_data.source)
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            if source_path.is_dir():
                raise IsADirectoryError(f"Path is a directory, not a file: {source_path}")
            return source_path.read_text(encoding="utf-8")
        return input_data.source

    def validate_input(self, input_data: Stage1Input) -> tuple[bool, str]:
        if input_data.source_type == "file":
            source_path = Path(input_data.source)
            if not source_path.exists():
                return False, f"Source file does not exist: {source_path}"
            if source_path.is_dir():
                return False, f"Path is a directory, not a file: {source_path}"
            return True, ""

        if input_data.source_type == "raw_text":
            if not input_data.source or not input_data.source.strip():
                return False, "Source text is empty or whitespace-only"
            return True, ""

        return False, f"Unknown source_type: {input_data.source_type}"

    def validate_output(self, output_data: Stage1Output) -> tuple[bool, str]:
        if output_data is None:
            return False, "Output is None"

        if not isinstance(output_data, BaseModel):
            return False, f"Expected Stage1Output, got {type(output_data)}"

        if not isinstance(output_data, Stage1Output):
            return False, f"Expected Stage1Output, got {type(output_data)}"

        for token_id, token in output_data.tokens.items():
            if token_id != token.id:
                return False, f"Token ID mismatch: key={token_id}, token.id={token.id}"

            if token_id not in output_data.metadata:
                return False, f"Missing metadata for token {token_id}"

            meta = output_data.metadata[token_id]
            if meta.token_id != token_id:
                return False, f"Metadata token_id mismatch: key={token_id}, meta.token_id={meta.token_id}"

            if meta.char_end < meta.char_start:
                return False, f"Invalid char range for {token_id}: end < start"

        if not output_data.is_config_full_coverage:
            if output_data.config and not output_data.config.include_whitespace:
                return False, (
                    f"Token data integrity violated: token text does not match source at recorded positions, "
                    f"or non-whitespace content was lost during filtering."
                )
            reconstructed_len = len(output_data.reconstructed_text)
            source_len = len(output_data.source_text)
            return False, (
                f"Full Coverage Invariant violated: "
                f"reconstructed_text ({reconstructed_len} chars) != source_text ({source_len} chars). "
                f"{'Tokens are missing.' if reconstructed_len < source_len else 'Unexpected extra content.'}"
            )

        return True, ""

    def name(self) -> str:
        return "SpacyTokenStreamBuilder"

    @property
    def tier(self) -> str:
        return "python_nlp"

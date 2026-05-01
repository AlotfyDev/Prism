"""Token and TokenMetadata schema models for Stage 1."""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from prism.schemas.enums import TokenType

_TOKEN_ID_PATTERN = re.compile(r"^T\d+$")


class Token(BaseModel):
    """A single token with linguistic annotations.

    Token IDs are globally sequential across the entire document (T0, T1, ...).
    The token_type field distinguishes semantic tokens (words, punctuation)
    from structural tokens (whitespace, newlines, indentation), enabling
    P2 Physical Topology to route tokens correctly.
    """

    id: str = Field(..., description="Global sequential token ID (T0, T1, ...)")
    text: str = Field(..., min_length=1, description="Surface text of the token")
    token_type: TokenType = Field(
        default=TokenType.SEMANTIC,
        description="Token origin: semantic (linguistic) or structural (layout/spacing)",
    )
    lemma: Optional[str] = Field(default=None, description="Lemmatized form")
    pos: Optional[str] = Field(default=None, description="Part-of-speech tag")
    ner_label: Optional[str] = Field(default=None, description="Named entity label")

    @field_validator("id")
    @classmethod
    def validate_token_id(cls, v: str) -> str:
        if not _TOKEN_ID_PATTERN.match(v):
            raise ValueError(f"Token ID must match T{{n}} pattern (e.g., T0, T1), got: {v!r}")
        return v


class TokenMetadata(BaseModel):
    """Positional and source metadata for a single token."""

    token_id: str = Field(..., description="Reference to Token.id")
    char_start: int = Field(..., ge=0, description="Start character offset in source text")
    char_end: int = Field(..., ge=0, description="End character offset in source text (exclusive)")
    source_line: int = Field(..., ge=1, description="Line number in source document (1-indexed)")
    bounding_box: Optional[tuple[float, float, float, float]] = Field(
        default=None,
        description="Bounding box (x0, y0, x1, y1) for PDF/layout-aware sources",
    )

    @field_validator("token_id")
    @classmethod
    def validate_token_id(cls, v: str) -> str:
        if not _TOKEN_ID_PATTERN.match(v):
            raise ValueError(f"Token ID must match T{{n}} pattern, got: {v!r}")
        return v

    @field_validator("char_end")
    @classmethod
    def validate_char_range(cls, v: int, info) -> int:
        if "char_start" in info.data and v < info.data["char_start"]:
            raise ValueError("char_end must be >= char_start")
        return v


class TokenizationConfig(BaseModel):
    """Configuration for the Stage 1 tokenization process."""

    tokenizer: str = Field(
        default="spacy",
        description="Tokenization engine (spacy, nltk, custom)",
    )
    include_whitespace: bool = Field(
        default=False,
        description="Whether to include whitespace tokens",
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 language code",
    )


class Stage1Input(BaseModel):
    """Input schema for the tokenization stage."""

    source: str = Field(..., description="File path or raw text content")
    source_type: str = Field(
        default="file",
        description="Source type: 'file' or 'raw_text'",
    )
    config: TokenizationConfig = Field(default_factory=TokenizationConfig)


class Stage1Output(BaseModel):
    """Output schema for the tokenization stage."""

    tokens: dict[str, Token] = Field(
        default_factory=dict,
        description="Map of token_id -> Token",
    )
    metadata: dict[str, TokenMetadata] = Field(
        default_factory=dict,
        description="Map of token_id -> TokenMetadata",
    )
    source_text: str = Field(default="", description="Original source text")
    config: Optional["TokenizationConfig"] = Field(
        default=None,
        description="Tokenization config used to produce this output — needed for validate_output",
    )

    @property
    def token_count(self) -> int:
        return len(self.tokens)

    @property
    def token_ids(self) -> list[str]:
        return sorted(self.tokens.keys(), key=lambda x: int(x[1:]))

    @property
    def reconstructed_text(self) -> str:
        """Reconstruct text by concatenating all tokens in order."""
        ordered = sorted(self.tokens.keys(), key=lambda x: int(x[1:]))
        return "".join(self.tokens[tid].text for tid in ordered)

    @property
    def is_full_coverage(self) -> bool:
        """Verify Full Coverage Invariant: reconstructed text matches source."""
        return self.reconstructed_text == self.source_text

    @property
    def is_config_full_coverage(self) -> bool:
        """Check full coverage accounting for config filtering.

        If include_whitespace=False, gaps from removed whitespace are expected.
        This verifies that gaps ONLY occur at structural token positions —
        no semantic token data was lost.
        """
        if self.config is None:
            return self.is_full_coverage
        if self.config.include_whitespace:
            return self.is_full_coverage

        # Whitespace excluded — verify gaps are only from filtered whitespace
        ordered_ids = self.token_ids
        if not ordered_ids:
            return len(self.source_text) == 0

        # Check: reconstructed text should equal source with all whitespace gaps removed
        cursor = 0
        for token_id in ordered_ids:
            token = self.tokens[token_id]
            meta = self.metadata[token_id]
            # The token text should match the source at its recorded position
            expected = self.source_text[meta.char_start:meta.char_end]
            if token.text != expected:
                return False
            cursor = meta.char_end

        # Check for gaps between consecutive tokens — they should be whitespace only
        cursor = 0
        for token_id in ordered_ids:
            meta = self.metadata[token_id]
            if meta.char_start > cursor:
                gap = self.source_text[cursor:meta.char_start]
                if gap and not gap.isspace():
                    return False
            cursor = meta.char_end

        # Check trailing gap
        if cursor < len(self.source_text):
            trailing = self.source_text[cursor:]
            if trailing and not trailing.isspace():
                return False

        return True


# Forward reference resolution
Stage1Output.model_rebuild()

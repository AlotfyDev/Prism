"""Unicode-aware structural gap filler for the tokenizer pipeline.

This module provides a dedicated mechanism for filling structural gaps
(whitespace, newlines, Unicode spaces) in the token stream, ensuring
the Full Text Coverage Invariant holds for ALL Unicode content.

Architecture:
    _StructuralGapFiller is invoked during Phase 2 of the tokenizer pipeline.
    It walks the source text from start to end, inserting structural tokens
    for any character regions not covered by semantic spans.

    Handles:
    - Leading gaps (before first semantic token)
    - Inter-token gaps (between semantic tokens)
    - Trailing gaps (after last semantic token)
    - Unicode whitespace (Zs, Zl, Zp categories + ASCII structural chars)

Unicode coverage:
    - Zs (Space Separator): U+0020, U+00A0, U+1680, U+2000-U+200A, U+202F, U+205F, U+3000
    - Zl (Line Separator): U+2028
    - Zp (Paragraph Separator): U+2029
    - BOM: U+FEFF
    - ASCII control: \t, \n, \r, \f, \v
"""

import unicodedata
from dataclasses import dataclass


@dataclass
class _TokenSpan:
    """Intermediate representation of a token before ID assignment."""

    text: str
    char_start: int
    char_end: int
    source_line: int
    lemma: str | None = None
    pos: str | None = None
    is_structural: bool = False


class _StructuralGapFiller:
    """Dedicated mechanism for filling structural gaps in the token stream.

    Ensures the Full Text Coverage Invariant: every character in the source
    text maps to exactly one token, regardless of Unicode complexity.
    """

    # Unicode whitespace characters that spaCy may not classify as is_space
    # but are structurally meaningful for downstream topology analysis.
    _UNICODE_WHITESPACE_CODEPOINTS = frozenset({
        # ASCII control whitespace
        0x0009,  # TAB
        0x000A,  # LINE FEED
        0x000D,  # CARRIAGE RETURN
        0x000C,  # FORM FEED
        0x000B,  # VERTICAL TAB
        # Zs - Space Separators
        0x0020,  # SPACE
        0x00A0,  # NO-BREAK SPACE
        0x1680,  # OGHAM SPACE MARK
        0x2000,  # EN QUAD
        0x2001,  # EM QUAD
        0x2002,  # EN SPACE
        0x2003,  # EM SPACE
        0x2004,  # THREE-PER-EM SPACE
        0x2005,  # FOUR-PER-EM SPACE
        0x2006,  # SIX-PER-EM SPACE
        0x2007,  # FIGURE SPACE
        0x2008,  # PUNCTUATION SPACE
        0x2009,  # THIN SPACE
        0x200A,  # HAIR SPACE
        0x202F,  # NARROW NO-BREAK SPACE
        0x205F,  # MEDIUM MATHEMATICAL SPACE
        0x3000,  # IDEOGRAPHIC SPACE
        # Zl - Line Separator
        0x2028,  # LINE SEPARATOR
        # Zp - Paragraph Separator
        0x2029,  # PARAGRAPH SEPARATOR
        # BOM
        0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM
    })

    @classmethod
    def is_structural_whitespace(cls, char: str) -> bool:
        """Check if a single character is structural whitespace.

        Covers ASCII control whitespace + Unicode Zs/Zl/Zp categories + BOM.
        Uses both codepoint lookup and unicodedata category for full coverage.
        """
        if len(char) != 1:
            return False
        cp = ord(char)
        if cp in cls._UNICODE_WHITESPACE_CODEPOINTS:
            return True
        # Catch-all via Unicode category (handles future additions)
        category = unicodedata.category(char)
        return category in ("Zs", "Zl", "Zp")

    @classmethod
    def fill(
        cls,
        spans: list[_TokenSpan],
        source_text: str,
    ) -> list[_TokenSpan]:
        """Fill ALL structural gaps in the token stream.

        Walks the source text from start to end, inserting structural tokens
        for any character regions not covered by semantic spans.

        Args:
            spans: Semantic token spans sorted by position
            source_text: Complete source text

        Returns:
            Complete span list with all gaps filled as structural tokens
        """
        if not spans:
            return cls._handle_empty(source_text)

        filled: list[_TokenSpan] = []
        cursor = 0

        for span in spans:
            cursor = cls._fill_gap_before(filled, cursor, span.char_start, source_text)
            filled.append(span)
            cursor = span.char_end

        # Trailing gap after last semantic token
        cursor = cls._fill_gap_before(filled, cursor, len(source_text), source_text)

        return filled

    @classmethod
    def _handle_empty(cls, source_text: str) -> list[_TokenSpan]:
        """Handle case where no semantic tokens exist (all-whitespace text)."""
        if not source_text:
            return []
        return [_TokenSpan(
            text=source_text,
            char_start=0,
            char_end=len(source_text),
            source_line=1,
            is_structural=True,
        )]

    @classmethod
    def _fill_gap_before(
        cls,
        filled: list[_TokenSpan],
        cursor: int,
        target: int,
        source_text: str,
    ) -> int:
        """Fill any gap between cursor and target position.

        Returns the updated cursor position (always equals target after this).
        """
        if cursor >= target:
            return target

        gap_text = source_text[cursor:target]
        if not gap_text:
            return target

        line = source_text[:cursor].count("\n") + 1
        filled.append(_TokenSpan(
            text=gap_text,
            char_start=cursor,
            char_end=target,
            source_line=line,
            is_structural=True,
        ))
        return target

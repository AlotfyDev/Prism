"""Unit tests for _StructuralGapFiller (P1.5 architectural fix).

Tests the dedicated Unicode-aware gap filler that ensures the
Full Text Coverage Invariant holds for ALL Unicode content.

Scenarios:
- Leading gaps (before first semantic token)
- Inter-token gaps (between semantic tokens)
- Trailing gaps (after last semantic token)
- Unicode whitespace (Zs, Zl, Zp categories)
- Empty input
- All-whitespace input
- Mixed ASCII + Unicode whitespace
- BOM handling
"""

import pytest

from prism.stage1.gap_filler import _StructuralGapFiller
from prism.stage1.tokenizer import _TokenSpan


class TestStructuralGapFillerLeading:
    """Leading gap scenarios (before first semantic token)."""

    def test_leading_space_single(self):
        """Single leading space before first token."""
        spans = [_TokenSpan(text="hello", char_start=1, char_end=6, source_line=1)]
        result = _StructuralGapFiller.fill(spans, " hello")
        assert len(result) == 2
        assert result[0].text == " "
        assert result[0].is_structural is True
        assert result[1].text == "hello"

    def test_leading_tabs_and_spaces(self):
        """Leading mix of tabs and spaces."""
        spans = [_TokenSpan(text="hello", char_start=4, char_end=9, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "\t\t  hello")
        assert result[0].text == "\t\t  "
        assert result[0].char_start == 0
        assert result[0].char_end == 4

    def test_leading_newlines(self):
        """Leading newlines shift line number."""
        spans = [_TokenSpan(text="hello", char_start=3, char_end=8, source_line=4)]
        result = _StructuralGapFiller.fill(spans, "\n\n\nhello")
        assert result[0].text == "\n\n\n"
        assert result[0].source_line == 1

    def test_no_leading_gap(self):
        """No gap when token starts at position 0."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello")
        assert len(result) == 1
        assert result[0].text == "hello"


class TestStructuralGapFillerInterToken:
    """Inter-token gap scenarios (between semantic tokens)."""

    def test_single_space_between_tokens(self):
        """Single space gap between two tokens."""
        spans = [
            _TokenSpan(text="hello", char_start=0, char_end=5, source_line=1),
            _TokenSpan(text="world", char_start=6, char_end=11, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "hello world")
        assert len(result) == 3
        assert result[1].text == " "
        assert result[1].is_structural is True

    def test_multiple_spaces_between_tokens(self):
        """Multiple space gap between tokens."""
        spans = [
            _TokenSpan(text="hello", char_start=0, char_end=5, source_line=1),
            _TokenSpan(text="world", char_start=10, char_end=15, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "hello     world")
        assert result[1].text == "     "
        assert result[1].char_start == 5
        assert result[1].char_end == 10

    def test_newline_between_tokens(self):
        """Newline gap between tokens (paragraph break)."""
        spans = [
            _TokenSpan(text="first", char_start=0, char_end=5, source_line=1),
            _TokenSpan(text="second", char_start=7, char_end=13, source_line=3),
        ]
        result = _StructuralGapFiller.fill(spans, "first\n\nsecond")
        assert result[1].text == "\n\n"
        assert result[1].source_line == 1

    def test_adjacent_tokens_no_gap(self):
        """Adjacent tokens with no gap between them."""
        spans = [
            _TokenSpan(text="he", char_start=0, char_end=2, source_line=1),
            _TokenSpan(text="llo", char_start=2, char_end=5, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "hello")
        assert len(result) == 2
        assert result[0].text == "he"
        assert result[1].text == "llo"


class TestStructuralGapFillerTrailing:
    """Trailing gap scenarios (after last semantic token)."""

    def test_trailing_space_single(self):
        """Single trailing space after last token."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello ")
        assert len(result) == 2
        assert result[1].text == " "
        assert result[1].is_structural is True

    def test_trailing_newline(self):
        """Trailing newline after last token."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello\n")
        assert result[1].text == "\n"
        assert result[1].char_start == 5
        assert result[1].char_end == 6

    def test_trailing_multiple_spaces(self):
        """Multiple trailing spaces after last token."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello   ")
        assert result[1].text == "   "

    def test_no_trailing_gap(self):
        """No gap when last token ends at source end."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello")
        assert len(result) == 1


class TestStructuralGapFillerUnicode:
    """Unicode whitespace scenarios."""

    def test_unicode_nbsp(self):
        """Unicode NO-BREAK SPACE (U+00A0) as gap."""
        spans = [
            _TokenSpan(text="hello", char_start=0, char_end=5, source_line=1),
            _TokenSpan(text="world", char_start=6, char_end=11, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "hello\u00a0world")
        assert result[1].text == "\u00a0"
        assert result[1].is_structural is True

    def test_unicode_em_space(self):
        """Unicode EM SPACE (U+2003) as gap."""
        spans = [
            _TokenSpan(text="hello", char_start=0, char_end=5, source_line=1),
            _TokenSpan(text="world", char_start=6, char_end=11, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "hello\u2003world")
        assert result[1].text == "\u2003"

    def test_unicode_six_per_em_space(self):
        """Unicode SIX-PER-EM SPACE (U+2006) — the Hypothesis failure case."""
        spans = [
            _TokenSpan(text="a", char_start=0, char_end=1, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "a\u2006")
        assert len(result) == 2
        assert result[1].text == "\u2006"
        assert result[1].is_structural is True
        assert result[1].char_end == len("a\u2006")

    def test_unicode_thin_space_trailing(self):
        """Unicode THIN SPACE (U+2009) as trailing gap."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello\u2009")
        assert result[1].text == "\u2009"

    def test_unicode_mixed_whitespace_gap(self):
        """Mixed ASCII + Unicode whitespace in a single gap."""
        spans = [
            _TokenSpan(text="a", char_start=0, char_end=1, source_line=1),
            _TokenSpan(text="b", char_start=3, char_end=4, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "a \u2000b")
        assert result[1].text == " \u2000"

    def test_unicode_line_separator(self):
        """Unicode LINE SEPARATOR (U+2028) as gap."""
        spans = [
            _TokenSpan(text="a", char_start=0, char_end=1, source_line=1),
            _TokenSpan(text="b", char_start=2, char_end=3, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "a\u2028b")
        assert result[1].text == "\u2028"

    def test_unicode_paragraph_separator(self):
        """Unicode PARAGRAPH SEPARATOR (U+2029) as gap."""
        spans = [
            _TokenSpan(text="a", char_start=0, char_end=1, source_line=1),
            _TokenSpan(text="b", char_start=2, char_end=3, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "a\u2029b")
        assert result[1].text == "\u2029"

    def test_unicode_bom_trailing(self):
        """Unicode BOM (U+FEFF) as trailing gap."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello\uFEFF")
        assert result[1].text == "\uFEFF"

    def test_unicode_ideographic_space(self):
        """Unicode IDEOGRAPHIC SPACE (U+3000) as gap."""
        spans = [
            _TokenSpan(text="a", char_start=0, char_end=1, source_line=1),
            _TokenSpan(text="b", char_start=2, char_end=3, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "a\u3000b")
        assert result[1].text == "\u3000"


class TestStructuralGapFillerEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_source(self):
        """Empty source text returns empty list."""
        result = _StructuralGapFiller.fill([], "")
        assert result == []

    def test_all_whitespace_source(self):
        """All-whitespace source becomes single structural token."""
        result = _StructuralGapFiller.fill([], "   \n\t  ")
        assert len(result) == 1
        assert result[0].is_structural is True
        assert result[0].text == "   \n\t  "
        assert result[0].char_start == 0
        assert result[0].char_end == len("   \n\t  ")

    def test_single_token_no_gaps(self):
        """Single token covering entire source."""
        spans = [_TokenSpan(text="hello", char_start=0, char_end=5, source_line=1)]
        result = _StructuralGapFiller.fill(spans, "hello")
        assert len(result) == 1
        assert result[0].text == "hello"

    def test_multiple_leading_inter_trailing(self):
        """All three gap types in one document."""
        spans = [
            _TokenSpan(text="first", char_start=2, char_end=7, source_line=1),
            _TokenSpan(text="last", char_start=9, char_end=13, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, "  first  last  ")
        assert len(result) == 5
        assert result[0].text == "  "  # leading
        assert result[1].text == "first"
        assert result[2].text == "  "  # inter
        assert result[3].text == "last"
        assert result[4].text == "  "  # trailing

    def test_full_coverage_invariant(self):
        """Every character in source is covered by exactly one token."""
        source = "  hello   world  \n"
        spans = [
            _TokenSpan(text="hello", char_start=2, char_end=7, source_line=1),
            _TokenSpan(text="world", char_start=10, char_end=15, source_line=1),
        ]
        result = _StructuralGapFiller.fill(spans, source)

        covered = 0
        for token in result:
            assert token.char_start < token.char_end
            assert source[token.char_start:token.char_end] == token.text
            covered += token.char_end - token.char_start

        assert covered == len(source)


class TestIsStructuralWhitespace:
    """Test _StructuralGapFiller.is_structural_whitespace classification."""

    @pytest.mark.parametrize("char", [
        " ", "\t", "\n", "\r", "\f", "\v",  # ASCII
        "\u00a0",  # NBSP
        "\u2000", "\u2001", "\u2002", "\u2003",  # Quad/Space variants
        "\u2004", "\u2005", "\u2006", "\u2007",  # More space variants
        "\u2008", "\u2009", "\u200a",  # Thin/Hair space
        "\u202f", "\u205f", "\u3000",  # Narrow/Medium/Ideographic
        "\u2028", "\u2029",  # Line/Paragraph separator
        "\ufeff",  # BOM
    ])
    def test_unicode_whitespace_detected(self, char):
        """All Unicode whitespace characters are detected."""
        assert _StructuralGapFiller.is_structural_whitespace(char) is True

    @pytest.mark.parametrize("char", [
        "a", "Z", "0", "9", ".", ",", "!", "?", "-", "_",
    ])
    def test_non_whitespace_rejected(self, char):
        """Non-whitespace characters are rejected."""
        assert _StructuralGapFiller.is_structural_whitespace(char) is False

    def test_empty_string_rejected(self):
        """Empty string is not whitespace."""
        assert _StructuralGapFiller.is_structural_whitespace("") is False

    def test_multi_char_string_rejected(self):
        """Multi-character strings are rejected (single char expected)."""
        assert _StructuralGapFiller.is_structural_whitespace("  ") is False

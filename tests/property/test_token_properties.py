"""Property-based tests for Stage 1 token invariants (P1.5).

Uses Hypothesis to verify that token invariants hold for ANY valid input,
not just hand-crafted examples. These are mathematical properties that
MUST be true for any tokenizer implementation.

Properties tested:
1. Sequential IDs: Any non-empty text → T0, T1, ... TN
2. No overlapping char ranges
3. Token text matches source at recorded positions
4. Full coverage when include_whitespace=True
5. Deterministic output (same input → same output)
6. Metadata completeness (every token has metadata)
7. Config-aware gap detection
"""

import pytest
from hypothesis import given, settings, HealthCheck, example
import hypothesis.strategies as st

from prism.schemas import Stage1Input, Stage1Output, TokenizationConfig
from prism.stage1.metadata import MetadataIndexer
from prism.stage1.validation_v1 import ValidationV1

SETTINGS = settings(
    max_examples=20,
    deadline=10000,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.large_base_example],
)


# --- Hypothesis Strategies ---

def non_empty_text():
    """Generate non-empty text with various characteristics."""
    return st.text(
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"),
            blacklist_characters=("\x00",),
        ),
        min_size=1,
        max_size=200,
    ).filter(lambda s: s.strip())


def realistic_text():
    """Generate text that looks like real Markdown content.

    Includes Unicode whitespace (Zs category) to verify _StructuralGapFiller
    handles all Unicode space separators correctly.
    """
    words = st.text(
        alphabet=st.characters(
            whitelist_categories=("Ll", "Lu", "Nd", "Po", "Ps", "Pe"),
            whitelist_characters=(" ", "\t", "\n"),
            blacklist_characters=("\x00",),
        ),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s.strip())

    single_para = st.lists(words, min_size=1, max_size=15).map(" ".join)
    multi_para = st.lists(single_para, min_size=2, max_size=3).map("\n\n".join)

    # Add Unicode whitespace variants to stress-test gap filler
    unicode_space_text = st.text(
        alphabet=st.characters(
            whitelist_categories=("Ll", "Lu", "Nd"),
            whitelist_characters=("\u00a0", "\u2000", "\u2001", "\u2002", "\u2003", "\u2004", "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u202f", "\u205f", "\u3000"),
        ),
        min_size=1,
        max_size=50,
    ).filter(lambda s: any(c.strip() for c in s))

    return st.one_of(single_para, multi_para, unicode_space_text)


# --- Property Tests ---

class TestTokenSequentialIDs:
    """Property: Tokenizer always produces sequential IDs with no gaps."""

    @given(non_empty_text())
    @SETTINGS
    def test_sequential_ids_for_any_text(self, text):
        """For any non-empty text, token IDs are T0, T1, ... TN."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        sorted_ids = sorted(output.tokens.keys(), key=lambda x: int(x[1:]))
        expected = [f"T{i}" for i in range(len(sorted_ids))]
        assert sorted_ids == expected, (
            f"Non-sequential IDs for text: {text[:50]!r}"
        )

    @example("hello")
    @example("a b c")
    @given(non_empty_text())
    @SETTINGS
    def test_no_duplicate_ids(self, text):
        """No duplicate token IDs for any input."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        ids = list(output.tokens.keys())
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

    @example("single")
    @given(non_empty_text())
    @SETTINGS
    def test_starts_at_t0(self, text):
        """First token is always T0."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        assert "T0" in output.tokens, "First token should be T0"


class TestTokenCharRanges:
    """Property: Token char ranges never overlap and are within bounds."""

    @given(realistic_text())
    @SETTINGS
    def test_no_overlapping_ranges(self, text):
        """For any text, no two tokens have overlapping char ranges."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        sorted_ids = sorted(output.metadata.keys(), key=lambda x: int(x[1:]))
        for i in range(len(sorted_ids) - 1):
            current = output.metadata[sorted_ids[i]]
            next_token = output.metadata[sorted_ids[i + 1]]
            assert current.char_end <= next_token.char_start, (
                f"Overlap at {sorted_ids[i]} (end={current.char_end}) and "
                f"{sorted_ids[i + 1]} (start={next_token.char_start})"
            )

    @given(realistic_text())
    @SETTINGS
    def test_ranges_within_bounds(self, text):
        """All char ranges are within source text bounds."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        source_len = len(output.source_text)
        for token_id, meta in output.metadata.items():
            assert meta.char_start >= 0, f"{token_id}: negative char_start"
            assert meta.char_end <= source_len, (
                f"{token_id}: char_end ({meta.char_end}) > source length ({source_len})"
            )
            assert meta.char_end >= meta.char_start, (
                f"{token_id}: char_end < char_start"
            )

    @given(realistic_text())
    @SETTINGS
    def test_token_text_matches_source(self, text):
        """Token text always matches source at recorded position."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        for token_id, token in output.tokens.items():
            meta = output.metadata[token_id]
            expected = output.source_text[meta.char_start:meta.char_end]
            assert token.text == expected, (
                f"{token_id}: token.text={token.text!r} != source[{meta.char_start}:{meta.char_end}]={expected!r}"
            )


class TestTokenCoverage:
    """Property: Token char ranges cover all source characters."""

    @given(realistic_text())
    @SETTINGS
    def test_full_coverage_with_whitespace(self, text):
        """When include_whitespace=True, all chars are covered."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        assert output.is_full_coverage, (
            f"Full coverage violated for text: {text[:100]!r}\n"
            f"reconstructed: {output.reconstructed_text[:100]!r}"
        )

    @given(realistic_text())
    @SETTINGS
    def test_config_full_coverage_semantic_only(self, text):
        """When include_whitespace=False, config-aware coverage holds."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=False)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        assert output.is_config_full_coverage, (
            f"Config full coverage violated for text: {text[:100]!r}"
        )


class TestTokenDeterminism:
    """Property: Tokenizer produces deterministic output."""

    @given(non_empty_text())
    @SETTINGS
    def test_same_input_same_output(self, text):
        """Same input always produces same token stream."""
        indexer1 = MetadataIndexer()
        indexer2 = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)

        inp1 = Stage1Input(source=text, source_type="raw_text", config=config)
        inp2 = Stage1Input(source=text, source_type="raw_text", config=config)

        output1 = indexer1.process(inp1, config)
        output2 = indexer2.process(inp2, config)

        assert output1.token_count == output2.token_count
        assert list(output1.tokens.keys()) == list(output2.tokens.keys())
        for tid in output1.tokens:
            assert output1.tokens[tid].text == output2.tokens[tid].text


class TestTokenMetadata:
    """Property: Metadata is always complete and consistent."""

    @given(realistic_text())
    @SETTINGS
    def test_metadata_count_matches_tokens(self, text):
        """Every token has exactly one metadata entry."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        assert len(output.metadata) == len(output.tokens)
        assert set(output.metadata.keys()) == set(output.tokens.keys())

    @given(realistic_text())
    @SETTINGS
    def test_metadata_token_id_matches_key(self, text):
        """Metadata token_id always matches its key."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        for key, meta in output.metadata.items():
            assert meta.token_id == key

    @given(realistic_text())
    @SETTINGS
    def test_source_line_is_positive(self, text):
        """All source_line values are >= 1."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        for meta in output.metadata.values():
            assert meta.source_line >= 1, f"source_line < 1 for token {meta.token_id}"


class TestValidationV1Properties:
    """Property: ValidationV1 behavior is consistent and correct."""

    @given(realistic_text())
    @SETTINGS
    def test_valid_output_always_passes(self, text):
        """Output from MetadataIndexer always passes ValidationV1."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        report = ValidationV1().validate(output)
        assert report.passed, f"Valid output failed V1: {report.critical_failures}"

    @given(realistic_text())
    @SETTINGS
    def test_report_always_has_five_checks(self, text):
        """ValidationV1 always returns exactly 5 checks."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        report = ValidationV1().validate(output)
        assert len(report.checks) == 5, f"Expected 5 checks, got {len(report.checks)}"

    @given(realistic_text())
    @SETTINGS
    def test_report_stage_is_stage1(self, text):
        """Validation report always has stage='stage1'."""
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)

        report = ValidationV1().validate(output)
        assert report.stage == "stage1"

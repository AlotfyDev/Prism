"""Unit tests for SpacyTokenStreamBuilder (P1.2)."""

import pytest
from pathlib import Path

from prism.schemas.enums import TokenType
from prism.stage1.tokenizer import SpacyTokenStreamBuilder
from prism.schemas import Stage1Input, Stage1Output, TokenizationConfig


class TestSpacyTokenStreamBuilderInstantiation:
    """Tests for SpacyTokenStreamBuilder construction."""

    def test_can_instantiate(self):
        """SpacyTokenStreamBuilder can be instantiated."""
        builder = SpacyTokenStreamBuilder()
        assert isinstance(builder.name(), str)

    def test_name_is_descriptive(self):
        """name() returns a descriptive string."""
        builder = SpacyTokenStreamBuilder()
        assert "spacy" in builder.name().lower()

    def test_tier_is_python_nlp(self):
        """tier returns python_nlp since it uses spaCy."""
        builder = SpacyTokenStreamBuilder()
        assert builder.tier == "python_nlp"


class TestSpacyTokenStreamBuilderValidateInput:
    """Tests for input validation."""

    def test_valid_raw_text_input(self):
        """validate_input returns True for non-empty raw text."""
        builder = SpacyTokenStreamBuilder()
        input_data = Stage1Input(
            source="Hello world.",
            source_type="raw_text",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = builder.validate_input(input_data)
        assert is_valid is True
        assert error_msg == ""

    def test_empty_raw_text_input(self):
        """validate_input returns False for empty raw text."""
        builder = SpacyTokenStreamBuilder()
        input_data = Stage1Input(
            source="",
            source_type="raw_text",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = builder.validate_input(input_data)
        assert is_valid is False
        assert error_msg != ""

    def test_whitespace_only_input(self):
        """validate_input returns False for whitespace-only input."""
        builder = SpacyTokenStreamBuilder()
        input_data = Stage1Input(
            source="   \n\t  ",
            source_type="raw_text",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = builder.validate_input(input_data)
        assert is_valid is False

    def test_valid_file_input(self, tmp_path: Path):
        """validate_input returns True for existing file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Hello world", encoding="utf-8")
        builder = SpacyTokenStreamBuilder()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="file",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = builder.validate_input(input_data)
        assert is_valid is True
        assert error_msg == ""

    def test_missing_file_input(self, tmp_path: Path):
        """validate_input returns False for non-existent file."""
        missing_file = tmp_path / "nonexistent.md"
        builder = SpacyTokenStreamBuilder()
        input_data = Stage1Input(
            source=str(missing_file),
            source_type="file",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = builder.validate_input(input_data)
        assert is_valid is False
        assert error_msg != ""


class TestSpacyTokenStreamBuilderValidateOutput:
    """Tests for output validation."""

    def test_valid_output(self):
        """validate_output returns True for valid Stage1Output."""
        builder = SpacyTokenStreamBuilder()
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "Hello"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="Hello",
        )
        is_valid, error_msg = builder.validate_output(output)
        assert is_valid is True
        assert error_msg == ""

    def test_none_output(self):
        """validate_output returns False for None output."""
        builder = SpacyTokenStreamBuilder()
        is_valid, error_msg = builder.validate_output(None)
        assert is_valid is False
        assert error_msg != ""

    def test_mismatched_type_output(self):
        """validate_output returns False for wrong type."""
        builder = SpacyTokenStreamBuilder()
        is_valid, error_msg = builder.validate_output("not a model")
        assert is_valid is False
        assert error_msg != ""


class TestSpacyTokenStreamBuilderBasic:
    """Basic tokenization tests."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()
        self.config = TokenizationConfig()

    def test_single_word(self):
        """Single word produces one token."""
        input_data = Stage1Input(source="hello", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.token_count == 1
        assert "T0" in output.tokens
        assert output.tokens["T0"].text == "hello"

    def test_two_words(self):
        """Two words produce two tokens."""
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.token_count == 2
        assert "T0" in output.tokens
        assert "T1" in output.tokens
        assert output.tokens["T0"].text == "hello"
        assert output.tokens["T1"].text == "world"

    def test_sentence_with_punctuation(self):
        """Punctuation becomes separate tokens."""
        input_data = Stage1Input(source="Hello world.", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        token_texts = [t.text for t in output.tokens.values()]
        assert "Hello" in token_texts
        assert "world" in token_texts
        assert "." in token_texts

    def test_global_sequential_ids(self):
        """Token IDs are globally sequential T0, T1, T2..."""
        input_data = Stage1Input(source="hello world today", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        ids = sorted(output.tokens.keys(), key=lambda x: int(x[1:]))
        expected = [f"T{i}" for i in range(len(ids))]
        assert ids == expected

    def test_output_is_stage1_output(self):
        """process returns Stage1Output instance."""
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert isinstance(output, Stage1Output)

    def test_source_text_preserved(self):
        """source_text in output matches input."""
        original = "hello world"
        input_data = Stage1Input(source=original, source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.source_text == original


class TestSpacyTokenStreamBuilderMultiParagraph:
    """Multi-paragraph tokenization tests."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()
        self.config = TokenizationConfig()

    def test_multi_paragraph(self):
        """Multi-paragraph text is tokenized correctly."""
        text = "First paragraph.\n\nSecond paragraph."
        input_data = Stage1Input(source=text, source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.token_count > 0
        token_texts = [t.text for t in output.tokens.values()]
        assert "First" in token_texts
        assert "paragraph" in token_texts
        assert "Second" in token_texts

    def test_token_count_matches(self):
        """token_count property matches actual token dict length."""
        text = "One two three four five."
        input_data = Stage1Input(source=text, source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.token_count == len(output.tokens)


class TestSpacyTokenStreamBuilderWhitespace:
    """Whitespace handling tests."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()

    def test_exclude_whitespace_by_default(self):
        """Whitespace tokens are excluded by default."""
        config = TokenizationConfig(include_whitespace=False)
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        token_texts = [t.text for t in output.tokens.values()]
        assert " " not in token_texts

    def test_include_whitespace(self):
        """Whitespace tokens are included when config says so."""
        config = TokenizationConfig(include_whitespace=True)
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        token_texts = [t.text for t in output.tokens.values()]
        assert " " in token_texts
        assert "hello" in token_texts
        assert "world" in token_texts


class TestSpacyTokenStreamBuilderMarkdown:
    """Markdown-specific tokenization tests."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()
        self.config = TokenizationConfig()

    def test_heading_tokens(self):
        """Markdown heading text is tokenized."""
        text = "# Introduction"
        input_data = Stage1Input(source=text, source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        token_texts = [t.text for t in output.tokens.values()]
        assert "#" in token_texts
        assert "Introduction" in token_texts

    def test_inline_code(self):
        """Inline code is tokenized."""
        text = "Use `print()` function"
        input_data = Stage1Input(source=text, source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.token_count > 0

    def test_list_items(self):
        """List items are tokenized."""
        text = "- item one\n- item two"
        input_data = Stage1Input(source=text, source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, config=self.config)
        assert output.token_count > 0
        token_texts = [t.text for t in output.tokens.values()]
        assert "-" in token_texts


class TestSpacyTokenStreamBuilderFile:
    """File-based tokenization tests."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()
        self.config = TokenizationConfig()

    def test_tokenizes_from_file(self, tmp_path: Path):
        """process reads and tokenizes from file path."""
        test_file = tmp_path / "test.md"
        test_file.write_text("hello world", encoding="utf-8")
        input_data = Stage1Input(source=str(test_file), source_type="file", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.token_count == 2

    def test_file_not_found_raises(self, tmp_path: Path):
        """process raises FileNotFoundError for missing file."""
        missing_file = tmp_path / "nonexistent.md"
        input_data = Stage1Input(source=str(missing_file), source_type="file", config=self.config)
        with pytest.raises(FileNotFoundError):
            self.builder.process(input_data, self.config)

    def test_file_unicode_content(self, tmp_path: Path):
        """process handles unicode content from file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Hello café naïve", encoding="utf-8")
        input_data = Stage1Input(source=str(test_file), source_type="file", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.token_count > 0


class TestSpacyTokenStreamBuilderMetadata:
    """Token metadata tests."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()
        self.config = TokenizationConfig()

    def test_metadata_created_for_each_token(self):
        """Each token has corresponding metadata."""
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert len(output.metadata) == len(output.tokens)
        assert set(output.metadata.keys()) == set(output.tokens.keys())

    def test_metadata_token_id_matches(self):
        """Metadata token_id matches the key."""
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        for token_id, meta in output.metadata.items():
            assert meta.token_id == token_id

    def test_first_token_char_start_zero(self):
        """First token starts at character 0."""
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.metadata["T0"].char_start == 0

    def test_char_positions_consistent(self):
        """char_end of one token should be near char_start of next (accounting for whitespace)."""
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        # T0 = "hello" (0-5), T1 = "world"
        t0_meta = output.metadata["T0"]
        assert t0_meta.char_start == 0
        assert t0_meta.char_end == 5

    def test_source_line_first_token(self):
        """First token is on line 1."""
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        assert output.metadata["T0"].source_line == 1

    def test_source_line_second_paragraph(self):
        """Tokens after newline have higher source_line."""
        text = "first line\nsecond line"
        input_data = Stage1Input(source=text, source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        lines = [m.source_line for m in output.metadata.values()]
        assert 1 in lines
        assert 2 in lines


class TestSpacyTokenStreamBuilderEdgeCases:
    """Edge case tests."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()
        self.config = TokenizationConfig()

    def test_lemma_populated(self):
        """Token lemma is populated from spaCy."""
        input_data = Stage1Input(source="running", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        token = output.tokens["T0"]
        assert token.lemma is not None

    def test_pos_populated(self):
        """Token pos is populated from spaCy."""
        input_data = Stage1Input(source="hello", source_type="raw_text", config=self.config)
        output = self.builder.process(input_data, self.config)
        token = output.tokens["T0"]
        assert token.pos is not None

    def test_empty_string_validation(self):
        """Empty string fails validation before processing."""
        input_data = Stage1Input(source="", source_type="raw_text", config=self.config)
        is_valid, _ = self.builder.validate_input(input_data)
        assert is_valid is False

    def test_newlines_only_validation(self):
        """Newlines-only input fails validation."""
        input_data = Stage1Input(source="\n\n\n", source_type="raw_text", config=self.config)
        is_valid, _ = self.builder.validate_input(input_data)
        assert is_valid is False


class TestSpacyTokenStreamBuilderTokenType:
    """Tests for token_type classification (semantic vs structural)."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()

    def test_semantic_tokens_have_semantic_type(self):
        """Word tokens are classified as SEMANTIC."""
        config = TokenizationConfig(include_whitespace=False)
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        for token in output.tokens.values():
            assert token.token_type == TokenType.SEMANTIC

    def test_structural_tokens_have_structural_type(self):
        """Whitespace tokens are classified as STRUCTURAL."""
        config = TokenizationConfig(include_whitespace=True)
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        structural_tokens = [t for t in output.tokens.values() if t.text == " "]
        assert len(structural_tokens) > 0
        for token in structural_tokens:
            assert token.token_type == TokenType.STRUCTURAL

    def test_punctuation_is_semantic(self):
        """Punctuation tokens are SEMANTIC, not structural."""
        config = TokenizationConfig(include_whitespace=False)
        input_data = Stage1Input(source="hello.", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        period_token = [t for t in output.tokens.values() if t.text == "."][0]
        assert period_token.token_type == TokenType.SEMANTIC


class TestSpacyTokenStreamBuilderFullCoverage:
    """Tests for Full Coverage Invariant validation."""

    def setup_method(self):
        self.builder = SpacyTokenStreamBuilder()

    def test_output_passes_full_coverage_with_whitespace(self):
        """include_whitespace=True produces full coverage."""
        config = TokenizationConfig(include_whitespace=True)
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        assert output.is_full_coverage is True
        is_valid, _ = self.builder.validate_output(output)
        assert is_valid is True

    def test_output_passes_full_coverage_without_whitespace(self):
        """include_whitespace=False still passes because token data integrity is preserved."""
        config = TokenizationConfig(include_whitespace=False)
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        assert output.is_full_coverage is False  # reconstructed != source (whitespace missing)
        assert output.is_config_full_coverage is True  # but token data matches source positions
        is_valid, msg = self.builder.validate_output(output)
        assert is_valid is True

    def test_reconstructed_text_with_whitespace(self):
        """reconstructed_text matches source when whitespace is included."""
        config = TokenizationConfig(include_whitespace=True)
        input_data = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.builder.process(input_data, config)
        assert output.reconstructed_text == "hello world"


class TestSpacyTokenStreamBuilderVersion:
    """Tests for version property."""

    def test_version_is_string(self):
        builder = SpacyTokenStreamBuilder()
        assert isinstance(builder.version, str)

    def test_version_format(self):
        builder = SpacyTokenStreamBuilder()
        assert builder.version.startswith("v")

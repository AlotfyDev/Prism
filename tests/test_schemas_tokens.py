"""Unit tests for Stage 1 schema models (Token, TokenMetadata, etc.)."""

import pytest
from pydantic import ValidationError

from prism.schemas.enums import TokenType
from prism.schemas.token import (
    Stage1Input,
    Stage1Output,
    Token,
    TokenMetadata,
    TokenizationConfig,
)


class TestToken:
    def test_valid_minimal(self):
        token = Token(id="T0", text="Hello")
        assert token.id == "T0"
        assert token.text == "Hello"
        assert token.lemma is None
        assert token.pos is None
        assert token.ner_label is None

    def test_valid_full(self):
        token = Token(
            id="T42",
            text="running",
            lemma="run",
            pos="VERB",
            ner_label="O",
        )
        assert token.id == "T42"
        assert token.lemma == "run"
        assert token.pos == "VERB"

    def test_invalid_id_no_t_prefix(self):
        with pytest.raises(ValidationError, match="T"):
            Token(id="42", text="Hello")

    def test_invalid_id_empty(self):
        with pytest.raises(ValidationError, match="T"):
            Token(id="", text="Hello")

    def test_invalid_id_bad_pattern(self):
        with pytest.raises(ValidationError, match="T"):
            Token(id="Token_0", text="Hello")

    def test_invalid_empty_text(self):
        with pytest.raises(ValidationError, match="at least 1 character"):
            Token(id="T0", text="")

    def test_large_token_id(self):
        token = Token(id="T999999", text="x")
        assert token.id == "T999999"

    def test_token_type_defaults_to_semantic(self):
        token = Token(id="T0", text="Hello")
        assert token.token_type == TokenType.SEMANTIC

    def test_token_type_can_be_structural(self):
        token = Token(id="T0", text="  ", token_type=TokenType.STRUCTURAL)
        assert token.token_type == TokenType.STRUCTURAL

    def test_token_type_enum_values(self):
        assert TokenType.SEMANTIC.value == "semantic"
        assert TokenType.STRUCTURAL.value == "structural"

    def test_token_type_two_values(self):
        assert len(TokenType) == 2


class TestTokenMetadata:
    def test_valid_minimal(self):
        meta = TokenMetadata(token_id="T0", char_start=0, char_end=5, source_line=1)
        assert meta.token_id == "T0"
        assert meta.char_start == 0
        assert meta.char_end == 5
        assert meta.source_line == 1
        assert meta.bounding_box is None

    def test_valid_with_bbox(self):
        meta = TokenMetadata(
            token_id="T1",
            char_start=6,
            char_end=11,
            source_line=1,
            bounding_box=(10.0, 20.0, 50.0, 35.0),
        )
        assert meta.bounding_box == (10.0, 20.0, 50.0, 35.0)

    def test_invalid_token_id(self):
        with pytest.raises(ValidationError, match="T"):
            TokenMetadata(token_id="bad", char_start=0, char_end=5, source_line=1)

    def test_invalid_char_end_before_start(self):
        with pytest.raises(ValidationError, match="char_end"):
            TokenMetadata(token_id="T0", char_start=10, char_end=5, source_line=1)

    def test_invalid_negative_char_start(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            TokenMetadata(token_id="T0", char_start=-1, char_end=5, source_line=1)

    def test_invalid_negative_source_line(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            TokenMetadata(token_id="T0", char_start=0, char_end=5, source_line=0)

    def test_equal_char_start_end(self):
        meta = TokenMetadata(token_id="T0", char_start=5, char_end=5, source_line=1)
        assert meta.char_start == 5
        assert meta.char_end == 5


class TestTokenizationConfig:
    def test_defaults(self):
        config = TokenizationConfig()
        assert config.tokenizer == "spacy"
        assert config.include_whitespace is False
        assert config.language == "en"

    def test_custom_values(self):
        config = TokenizationConfig(
            tokenizer="nltk",
            include_whitespace=True,
            language="ar",
        )
        assert config.tokenizer == "nltk"
        assert config.include_whitespace is True
        assert config.language == "ar"


class TestStage1Input:
    def test_valid_file_source(self):
        inp = Stage1Input(source="path/to/doc.md", source_type="file")
        assert inp.source == "path/to/doc.md"
        assert inp.source_type == "file"
        assert inp.config.tokenizer == "spacy"

    def test_valid_raw_text(self):
        inp = Stage1Input(source="Hello world", source_type="raw_text")
        assert inp.source == "Hello world"

    def test_default_source_type(self):
        inp = Stage1Input(source="doc.md")
        assert inp.source_type == "file"

    def test_custom_config(self):
        config = TokenizationConfig(tokenizer="custom", language="fr")
        inp = Stage1Input(source="doc.md", config=config)
        assert inp.config.language == "fr"

    def test_missing_source(self):
        with pytest.raises(ValidationError):
            Stage1Input()


class TestStage1Output:
    def test_empty_output(self):
        output = Stage1Output()
        assert output.tokens == {}
        assert output.metadata == {}
        assert output.token_count == 0
        assert output.token_ids == []

    def test_with_tokens(self):
        tokens = {
            "T0": Token(id="T0", text="Hello"),
            "T1": Token(id="T1", text="world"),
        }
        metadata = {
            "T0": TokenMetadata(token_id="T0", char_start=0, char_end=5, source_line=1),
            "T1": TokenMetadata(token_id="T1", char_start=6, char_end=11, source_line=1),
        }
        output = Stage1Output(
            tokens=tokens,
            metadata=metadata,
            source_text="Hello world",
        )
        assert output.token_count == 2
        assert output.token_ids == ["T0", "T1"]
        assert output.source_text == "Hello world"

    def test_token_ids_sorted(self):
        tokens = {
            "T10": Token(id="T10", text="c"),
            "T0": Token(id="T0", text="a"),
            "T2": Token(id="T2", text="b"),
        }
        output = Stage1Output(tokens=tokens)
        assert output.token_ids == ["T0", "T2", "T10"]

    def test_reconstructed_text_matches_source(self):
        tokens = {
            "T0": Token(id="T0", text="Hello"),
            "T1": Token(id="T1", text=" "),
            "T2": Token(id="T2", text="world"),
        }
        output = Stage1Output(
            tokens=tokens,
            source_text="Hello world",
        )
        assert output.reconstructed_text == "Hello world"
        assert output.is_full_coverage is True

    def test_reconstructed_text_with_missing_tokens(self):
        tokens = {
            "T0": Token(id="T0", text="Hello"),
        }
        output = Stage1Output(
            tokens=tokens,
            source_text="Hello world",
        )
        assert output.reconstructed_text == "Hello"
        assert output.is_full_coverage is False

    def test_reconstructed_text_empty_output(self):
        output = Stage1Output(source_text="")
        assert output.reconstructed_text == ""
        assert output.is_full_coverage is True

    def test_is_full_coverage_with_structural_tokens(self):
        tokens = {
            "T0": Token(id="T0", text="Hello", token_type=TokenType.SEMANTIC),
            "T1": Token(id="T1", text="  \n", token_type=TokenType.STRUCTURAL),
            "T2": Token(id="T2", text="Next", token_type=TokenType.SEMANTIC),
        }
        output = Stage1Output(
            tokens=tokens,
            source_text="Hello  \nNext",
        )
        assert output.reconstructed_text == "Hello  \nNext"
        assert output.is_full_coverage is True
